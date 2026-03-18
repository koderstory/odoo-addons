from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountReportGeneralLedger(models.TransientModel):
    _name = "accounting.owl.general.ledger.report"
    _description = "Accounting OWL General Ledger Report"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    journal_ids = fields.Many2many(
        "account.journal",
        "accounting_owl_general_ledger_journal_rel",
        "wizard_id",
        "journal_id",
        string="Journals",
        required=True,
        default=lambda self: self.env["account.journal"].search(
            [("company_id", "=", self.env.company.id)]
        ),
        domain="[('company_id', '=', company_id)]",
    )
    date_from = fields.Date(string="Start Date")
    date_to = fields.Date(string="End Date")
    target_move = fields.Selection(
        [("posted", "All Posted Entries"), ("all", "All Entries")],
        string="Target Moves",
        required=True,
        default="posted",
    )
    display_account = fields.Selection(
        [
            ("all", "All"),
            ("movement", "With movements"),
            ("not_zero", "With balance is not equal to 0"),
        ],
        string="Display Accounts",
        required=True,
        default="movement",
    )
    analytic_account_ids = fields.Many2many(
        "account.analytic.account",
        "accounting_owl_general_ledger_analytic_rel",
        "wizard_id",
        "analytic_account_id",
        string="Analytic Accounts",
    )
    account_ids = fields.Many2many("account.account", string="Accounts")
    partner_ids = fields.Many2many("res.partner", string="Partners")
    initial_balance = fields.Boolean(
        string="Include Initial Balances",
        help=(
            "If you selected a date range, this option adds a row showing "
            "the debit, credit, and balance that precede the selected period."
        ),
    )
    sortby = fields.Selection(
        [("sort_date", "Date"), ("sort_journal_partner", "Journal & Partner")],
        string="Sort by",
        required=True,
        default="sort_date",
    )

    @api.onchange("company_id")
    def _onchange_company_id(self):
        if self.company_id:
            self.journal_ids = self.env["account.journal"].search(
                [("company_id", "=", self.company_id.id)]
            )
        else:
            self.journal_ids = self.env["account.journal"].search([])

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
        payload_lines = self._get_owl_account_lines_payload(
            account[0], options, analytic_accounts, partners
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
            options,
            analytic_accounts=analytic_accounts,
            partners=partners,
        )
        initial_totals = {}
        if options["initial_balance"]:
            initial_totals = self._get_owl_grouped_account_totals(
                accounts.ids,
                options,
                analytic_accounts=analytic_accounts,
                partners=partners,
                initial_balance=True,
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
    def _build_owl_move_line_domain(
        self,
        options,
        account_ids,
        analytic_accounts=False,
        partners=False,
        initial_balance=False,
    ):
        domain = [
            ("display_type", "not in", ("line_section", "line_note")),
            ("parent_state", "!=", "cancel"),
            ("company_id", "=", self.env.company.id),
            ("account_id", "in", account_ids),
        ]
        if options["date_to"] and not initial_balance:
            domain.append(("date", "<=", options["date_to"]))
        if options["date_from"]:
            operator = "<" if initial_balance else ">="
            domain.append(("date", operator, options["date_from"]))
        if options["journal_ids"]:
            domain.append(("journal_id", "in", options["journal_ids"]))
        if options["target_move"] != "all":
            domain.append(("parent_state", "=", options["target_move"]))
        if analytic_accounts:
            domain.append(("analytic_distribution", "in", analytic_accounts.ids))
        if partners:
            domain.append(("partner_id", "in", partners.ids))
        return domain

    @api.model
    def _get_owl_grouped_account_totals(
        self, account_ids, options, analytic_accounts=False, partners=False, initial_balance=False
    ):
        if not account_ids:
            return {}
        rows = self.env["account.move.line"]._read_group(
            domain=self._build_owl_move_line_domain(
                options,
                account_ids,
                analytic_accounts=analytic_accounts,
                partners=partners,
                initial_balance=initial_balance,
            ),
            groupby=["account_id"],
            aggregates=["debit:sum", "credit:sum", "id:count"],
        )
        return {
            account.id: {
                "debit": debit or 0.0,
                "credit": credit or 0.0,
                "balance": (debit or 0.0) - (credit or 0.0),
                "line_count": int(line_count or 0),
            }
            for account, debit, credit, line_count in rows
        }

    @api.model
    def _get_owl_account_lines_payload(
        self, account, options, analytic_accounts=False, partners=False
    ):
        payload_lines = []
        running_balance = 0.0

        if options["initial_balance"] and options["date_from"]:
            initial_totals = self._get_owl_grouped_account_totals(
                [account.id],
                options,
                analytic_accounts=analytic_accounts,
                partners=partners,
                initial_balance=True,
            )
            initial = initial_totals.get(account.id, {})
            if initial.get("line_count"):
                running_balance = initial.get("balance", 0.0)
                payload_lines.append(
                    {
                        "id": f"{account.id}-initial-1",
                        "move_line_id": False,
                        "move_id": False,
                        "date": False,
                        "journal_code": "",
                        "reference": "",
                        "label": "Initial Balance",
                        "partner_name": "",
                        "move_name": "",
                        "currency_id": False,
                        "currency_code": "",
                        "amount_currency": 0.0,
                        "debit": initial.get("debit", 0.0),
                        "credit": initial.get("credit", 0.0),
                        "balance": running_balance,
                        "is_initial_balance": True,
                    }
                )

        order = "date, move_id, id"
        if options["sortby"] == "sort_journal_partner":
            order = "journal_id, partner_id, move_id, date, id"
        move_lines = self.env["account.move.line"].search(
            self._build_owl_move_line_domain(
                options, [account.id], analytic_accounts=analytic_accounts, partners=partners
            ),
            order=order,
        )
        for line in move_lines:
            running_balance += (line.debit or 0.0) - (line.credit or 0.0)
            payload_lines.append(
                {
                    "id": line.id,
                    "move_line_id": line.id,
                    "move_id": line.move_id.id,
                    "date": line.date or False,
                    "journal_code": line.journal_id.code or "",
                    "reference": line.ref or "",
                    "label": line.name or "",
                    "partner_name": line.partner_id.display_name or "",
                    "move_name": line.move_name or "",
                    "currency_id": line.currency_id.id or False,
                    "currency_code": line.currency_id.symbol or "",
                    "amount_currency": line.amount_currency or 0.0,
                    "debit": line.debit or 0.0,
                    "credit": line.credit or 0.0,
                    "balance": running_balance,
                    "is_initial_balance": False,
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
