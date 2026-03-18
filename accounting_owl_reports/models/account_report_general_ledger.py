from odoo import _, api, models
from odoo.exceptions import UserError


class AccountReportGeneralLedger(models.TransientModel):
    _inherit = "account.report.general.ledger"

    @api.model
    def _check_owl_report_access(self):
        # Enforce the wizard ACL on remote OWL calls as well, not only via menus.
        self.check_access_rights("read")

    @api.model
    def get_owl_initial_data(self):
        self._check_owl_report_access()
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
        self._check_owl_report_access()
        options = self._sanitize_and_validate_owl_options(options or {})
        company = self.env.company
        analytic_accounts = self._get_existing_records(
            "account.analytic.account", options["analytic_account_ids"]
        )
        partners = self._get_existing_records("res.partner", options["partner_ids"])
        accounts = self._get_owl_accounts(options)
        payload_accounts = self._get_owl_account_summaries(
            accounts, options, analytic_accounts, partners
        )
        total_lines = sum(account["line_count"] for account in payload_accounts)
        total_debit = sum(account["debit"] for account in payload_accounts)
        total_credit = sum(account["credit"] for account in payload_accounts)
        total_balance = sum(account["balance"] for account in payload_accounts)

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
    def get_owl_account_lines(self, account_id, options=None):
        self._check_owl_report_access()
        options = self._sanitize_and_validate_owl_options(options or {})
        try:
            account_id = int(account_id)
        except (TypeError, ValueError):
            return {"account_id": False, "lines": [], "line_count": 0}
        analytic_accounts = self._get_existing_records(
            "account.analytic.account", options["analytic_account_ids"]
        )
        partners = self._get_existing_records("res.partner", options["partner_ids"])
        account = self._get_owl_accounts(options).filtered(lambda rec: rec.id == account_id)
        if not account:
            return {"account_id": account_id, "lines": [], "line_count": 0}

        report_model = self.env["report.accounting_pdf_reports.report_general_ledger"]
        query_context = self._build_owl_query_context(
            options, analytic_accounts, partners
        )
        account_result = report_model.with_context(query_context)._get_account_move_entry(
            account,
            analytic_accounts,
            partners,
            options["initial_balance"],
            options["sortby"],
            "all",
        )
        account_data = account_result[0] if account_result else {"move_lines": []}
        move_lines = account_data.get("move_lines", [])
        move_by_line_id = self._get_owl_move_by_line_id(move_lines)
        payload_lines = self._serialize_owl_move_lines(
            account.id, move_lines, move_by_line_id
        )
        return {
            "account_id": account.id,
            "lines": payload_lines,
            "line_count": len(payload_lines),
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
    def _sanitize_and_validate_owl_options(self, options):
        options = self._sanitize_owl_options(options)
        if options["initial_balance"] and not options["date_from"]:
            raise UserError(_("You must define a Start Date"))
        return options

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
    def _build_owl_query_context(
        self, options, analytic_accounts=False, partners=False, initial_balance=False
    ):
        context = dict(self._build_owl_context(options))
        if analytic_accounts:
            context["analytic_account_ids"] = analytic_accounts
        if partners:
            context["partner_ids"] = partners
        if initial_balance:
            context["date_to"] = False
            context["initial_bal"] = True
        return context

    @api.model
    def _get_owl_accounts(self, options):
        company = self.env.company
        account_domain = [("company_ids", "in", [company.id])]
        if options["account_ids"]:
            account_domain.append(("id", "in", options["account_ids"]))
        return self.env["account.account"].search(account_domain, order="code, id")

    @api.model
    def _get_owl_account_summaries(
        self, accounts, options, analytic_accounts=False, partners=False
    ):
        empty_totals = {"debit": 0.0, "credit": 0.0, "balance": 0.0, "line_count": 0}
        current_totals = self._get_owl_grouped_account_totals(
            accounts.ids,
            self._build_owl_query_context(options, analytic_accounts, partners),
        )
        initial_totals = {}
        if options["initial_balance"]:
            initial_totals = self._get_owl_grouped_account_totals(
                accounts.ids,
                self._build_owl_query_context(
                    options, analytic_accounts, partners, initial_balance=True
                ),
            )

        payload_accounts = []
        for account in accounts:
            current = current_totals.get(account.id, empty_totals)
            initial = initial_totals.get(account.id, empty_totals)
            debit = initial["debit"] + current["debit"]
            credit = initial["credit"] + current["credit"]
            balance = initial["balance"] + current["balance"]
            has_initial_balance = bool(initial["line_count"])
            line_count = current["line_count"] + (1 if has_initial_balance else 0)
            currency = account.currency_id or self.env.company.currency_id

            should_include = options["display_account"] == "all"
            if options["display_account"] == "movement":
                should_include = bool(line_count)
            elif options["display_account"] == "not_zero":
                should_include = not currency.is_zero(balance)

            if not should_include:
                continue

            payload_accounts.append(
                {
                    "id": account.id,
                    "code": account.code,
                    "name": account.name,
                    "debit": debit,
                    "credit": credit,
                    "balance": balance,
                    "line_count": line_count,
                    "move_line_count": current["line_count"],
                    "has_initial_balance": has_initial_balance,
                }
            )
        return payload_accounts

    @api.model
    def _get_owl_grouped_account_totals(self, account_ids, context):
        if not account_ids:
            return {}

        move_line_model = self.env["account.move.line"]
        _, where_clause, where_params = move_line_model.with_context(context)._query_get()
        filters = ["l.account_id IN %s"]
        if where_clause.strip():
            filters.append(
                where_clause.strip()
                .replace("account_move_line__move_id", "m")
                .replace("account_move_line", "l")
            )

        sql = """
            SELECT
                l.account_id AS account_id,
                COALESCE(SUM(l.debit), 0.0) AS debit,
                COALESCE(SUM(l.credit), 0.0) AS credit,
                COALESCE(SUM(l.debit), 0.0) - COALESCE(SUM(l.credit), 0.0) AS balance,
                COUNT(l.id) AS line_count
            FROM account_move_line l
            JOIN account_move m ON (l.move_id = m.id)
            LEFT JOIN res_partner p ON (l.partner_id = p.id)
            JOIN account_journal j ON (l.journal_id = j.id)
            JOIN account_account acc ON (l.account_id = acc.id)
            WHERE
        """ + " AND ".join(filters) + """
            GROUP BY l.account_id
        """
        params = (tuple(account_ids),) + tuple(where_params)
        self.env.cr.execute(sql, params)
        return {
            row["account_id"]: {
                "debit": row["debit"] or 0.0,
                "credit": row["credit"] or 0.0,
                "balance": row["balance"] or 0.0,
                "line_count": int(row["line_count"] or 0),
            }
            for row in self.env.cr.dictfetchall()
        }

    @api.model
    def _get_owl_move_by_line_id(self, move_lines):
        move_line_ids = [
            line["lid"] for line in move_lines if line.get("lid")
        ]
        if not move_line_ids:
            return {}
        return {
            move_line.id: move_line.move_id.id
            for move_line in self.env["account.move.line"].browse(move_line_ids).exists()
        }

    @api.model
    def _serialize_owl_move_lines(self, account_id, move_lines, move_by_line_id):
        payload_lines = []
        for line_index, line in enumerate(move_lines, start=1):
            payload_lines.append(
                {
                    "id": line.get("lid") or f"{account_id}-initial-{line_index}",
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
        return payload_lines

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
