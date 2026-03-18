from odoo import _, api, models
from odoo.exceptions import UserError


class AccountReportGeneralLedger(models.TransientModel):
    _inherit = "account.report.general.ledger"

    @api.model
    def get_owl_initial_data(self):
        company = self.env.company
        journals = self.env["account.journal"].search([("company_id", "=", company.id)])
        return {
            "company": {
                "id": company.id,
                "name": company.display_name,
            },
            "currency": {
                "id": company.currency_id.id,
                "name": company.currency_id.name,
                "symbol": company.currency_id.symbol,
            },
            "domains": {
                "journals": [("company_id", "=", company.id)],
                "accounts": [("company_ids", "in", [company.id])],
                "analytic_accounts": [
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "=", company.id),
                ],
                "partners": [],
            },
            "defaults": {
                "target_move": "posted",
                "date_from": False,
                "date_to": False,
                "display_account": "movement",
                "initial_balance": False,
                "sortby": "sort_date",
                "journal_ids": journals.ids,
                "account_ids": [],
                "analytic_account_ids": [],
                "partner_ids": [],
            },
            "selections": {
                "target_move": [
                    {"value": "posted", "label": _("All Posted Entries")},
                    {"value": "all", "label": _("All Entries")},
                ],
                "display_account": [
                    {"value": "all", "label": _("All")},
                    {"value": "movement", "label": _("With movements")},
                    {
                        "value": "not_zero",
                        "label": _("With balance is not equal to 0"),
                    },
                ],
                "sortby": [
                    {"value": "sort_date", "label": _("Date")},
                    {
                        "value": "sort_journal_partner",
                        "label": _("Journal & Partner"),
                    },
                ],
            },
            "features": {
                "analytic_filter": self.env.user.has_group(
                    "analytic.group_analytic_accounting"
                ),
            },
            "journals": [
                {
                    "id": journal.id,
                    "name": journal.display_name,
                    "code": journal.code,
                }
                for journal in journals
            ],
        }

    @api.model
    def get_owl_report_data(self, options=None):
        options = self._sanitize_owl_options(options or {})
        if options["initial_balance"] and not options["date_from"]:
            raise UserError(_("You must define a Start Date"))

        company = self.env.company
        analytic_accounts = self._get_existing_records(
            "account.analytic.account", options["analytic_account_ids"]
        )
        partners = self._get_existing_records("res.partner", options["partner_ids"])
        account_domain = [("company_ids", "in", [company.id])]
        if options["account_ids"]:
            account_domain.append(("id", "in", options["account_ids"]))
        accounts = self.env["account.account"].search(account_domain)

        used_context = self._build_owl_context(options)
        report_model = self.env["report.accounting_pdf_reports.report_general_ledger"]
        accounts_res = report_model.with_context(used_context)._get_account_move_entry(
            accounts,
            analytic_accounts,
            partners,
            options["initial_balance"],
            options["sortby"],
            options["display_account"],
        )
        move_line_ids = []
        for account in accounts_res:
            for line in account.get("move_lines", []):
                if line.get("lid"):
                    move_line_ids.append(line["lid"])
        move_by_line_id = {}
        if move_line_ids:
            move_by_line_id = {
                move_line.id: move_line.move_id.id
                for move_line in self.env["account.move.line"].browse(move_line_ids).exists()
            }

        payload_accounts = []
        total_lines = 0
        total_debit = 0.0
        total_credit = 0.0
        total_balance = 0.0

        for sequence, account in enumerate(accounts_res, start=1):
            move_lines = []
            for line_index, line in enumerate(account.get("move_lines", []), start=1):
                move_lines.append(
                    {
                        "id": line.get("lid") or f"{sequence}-initial-{line_index}",
                        "move_line_id": line.get("lid") or False,
                        "move_id": move_by_line_id.get(line.get("lid")) or False,
                        "date": line.get("ldate") or False,
                        "journal_code": line.get("lcode") or "",
                        "reference": line.get("lref") or "",
                        "label": line.get("lname") or "",
                        "partner_name": line.get("partner_name") or "",
                        "move_name": line.get("move_name") or "",
                        "currency_id": line.get("currency_id") or False,
                        "currency_code": line.get("currency_code") or "",
                        "amount_currency": line.get("amount_currency") or 0.0,
                        "debit": line.get("debit") or 0.0,
                        "credit": line.get("credit") or 0.0,
                        "balance": line.get("balance") or 0.0,
                        "is_initial_balance": not bool(line.get("lid")),
                    }
                )

            total_lines += len(move_lines)
            total_debit += account.get("debit", 0.0)
            total_credit += account.get("credit", 0.0)
            total_balance += account.get("balance", 0.0)
            payload_accounts.append(
                {
                    "id": sequence,
                    "code": account.get("code"),
                    "name": account.get("name"),
                    "debit": account.get("debit", 0.0),
                    "credit": account.get("credit", 0.0),
                    "balance": account.get("balance", 0.0),
                    "line_count": len(move_lines),
                    "move_lines": move_lines,
                }
            )

        return {
            "options": options,
            "summary": {
                "account_count": len(payload_accounts),
                "line_count": total_lines,
                "debit": total_debit,
                "credit": total_credit,
                "balance": total_balance,
            },
            "accounts": payload_accounts,
            "meta": {
                "company_name": company.display_name,
                "currency_id": company.currency_id.id,
            },
        }

    @api.model
    def _sanitize_owl_options(self, options):
        journal_ids = options.get("journal_ids")
        if journal_ids is None:
            journal_ids = self.env["account.journal"].search(
                [("company_id", "=", self.env.company.id)]
            ).ids

        return {
            "target_move": self._sanitize_selection(
                options.get("target_move"),
                {"posted", "all"},
                "posted",
            ),
            "date_from": options.get("date_from") or False,
            "date_to": options.get("date_to") or False,
            "display_account": self._sanitize_selection(
                options.get("display_account"),
                {"all", "movement", "not_zero"},
                "movement",
            ),
            "initial_balance": bool(options.get("initial_balance")),
            "sortby": self._sanitize_selection(
                options.get("sortby"),
                {"sort_date", "sort_journal_partner"},
                "sort_date",
            ),
            "journal_ids": self._sanitize_ids(journal_ids),
            "account_ids": self._sanitize_ids(options.get("account_ids", [])),
            "analytic_account_ids": self._sanitize_ids(
                options.get("analytic_account_ids", [])
            ),
            "partner_ids": self._sanitize_ids(options.get("partner_ids", [])),
        }

    @api.model
    def _build_owl_context(self, options):
        company = self.env.company
        return {
            "journal_ids": options["journal_ids"] or False,
            "state": options["target_move"],
            "date_from": options["date_from"] or False,
            "date_to": options["date_to"] or False,
            "strict_range": bool(options["date_from"]),
            "company_id": company.id,
            "allowed_company_ids": [company.id],
            "lang": self.env.lang,
        }

    @api.model
    def _sanitize_ids(self, values):
        if isinstance(values, (int, str)):
            values = [values]
        sanitized = []
        for value in values or []:
            try:
                sanitized.append(int(value))
            except (TypeError, ValueError):
                continue
        return sanitized

    @api.model
    def _sanitize_selection(self, value, allowed_values, default):
        return value if value in allowed_values else default

    @api.model
    def _get_existing_records(self, model_name, ids):
        records = self.env[model_name].browse(ids).exists()
        return records or False
