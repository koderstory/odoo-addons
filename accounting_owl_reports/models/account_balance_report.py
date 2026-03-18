from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountBalanceReport(models.TransientModel):
    _name = "accounting.owl.trial.balance.report"
    _description = "Accounting OWL Trial Balance Report"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    journal_ids = fields.Many2many(
        "account.journal",
        "accounting_owl_trial_balance_journal_rel",
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
    account_ids = fields.Many2many("account.account", string="Accounts")
    analytic_account_ids = fields.Many2many(
        "account.analytic.account",
        "accounting_owl_trial_balance_analytic_rel",
        "wizard_id",
        "analytic_account_id",
        string="Analytic Accounts",
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
            },
            "defaults": {
                "target_move": "posted",
                "date_from": False,
                "date_to": False,
                "display_account": "movement",
                "journal_ids": journals.ids,
                "account_ids": [],
                "analytic_account_ids": [],
                "comparison_mode": "no_comparison",
                "comparison_period_count": 10,
                "comparison_date_from": False,
                "comparison_date_to": False,
                "comparison_order": "asc",
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
                "comparison_mode": [
                    {"value": "no_comparison", "label": _("No Comparison")},
                    {"value": "previous_period", "label": _("Previous Period")},
                    {
                        "value": "same_period_last_year",
                        "label": _("Same Period Last Year"),
                    },
                    {"value": "custom_date", "label": _("Custom Dates")},
                ],
                "comparison_order": [
                    {"value": "asc", "label": _("Ascending")},
                    {"value": "desc", "label": _("Descending")},
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
        accounts = self._get_owl_accounts(options)
        period_config = self._build_period_config(options)

        initial_anchor_start = period_config["initial_anchor_start"]
        initial_totals = {}
        if initial_anchor_start:
            initial_totals = self._get_owl_grouped_account_totals(
                accounts.ids,
                options,
                analytic_accounts=analytic_accounts,
                date_from=initial_anchor_start,
                date_to=False,
                initial_balance=True,
            )

        period_totals = {}
        for period in period_config["periods"]:
            period_totals[period["key"]] = self._get_owl_grouped_account_totals(
                accounts.ids,
                options,
                analytic_accounts=analytic_accounts,
                date_from=period["date_from"],
                date_to=period["date_to"],
            )

        payload_accounts = []
        summary_initial_debit = 0.0
        summary_initial_credit = 0.0
        summary_ending_debit = 0.0
        summary_ending_credit = 0.0
        summary_periods = {
            period["key"]: {"debit": 0.0, "credit": 0.0, "balance": 0.0}
            for period in period_config["periods"]
        }
        empty_totals = {"debit": 0.0, "credit": 0.0, "balance": 0.0}
        current_key = period_config["current_period_key"]
        ending_uses_all_periods = options["comparison_mode"] == "previous_period"

        for account in accounts:
            currency = account.currency_id or company.currency_id
            initial_balance = initial_totals.get(account.id, empty_totals)["balance"]
            current_period_totals = period_totals.get(current_key, {}).get(
                account.id, empty_totals
            )
            ending_balance = initial_balance + current_period_totals["balance"]
            if ending_uses_all_periods:
                ending_balance = initial_balance + sum(
                    period_totals[period["key"]].get(account.id, empty_totals)["balance"]
                    for period in period_config["periods"]
                )

            initial_debit, initial_credit = self._split_balance(initial_balance)
            ending_debit, ending_credit = self._split_balance(ending_balance)
            period_values = {}
            has_visible_movement = False

            for period in period_config["periods"]:
                totals = period_totals[period["key"]].get(account.id, empty_totals)
                period_values[period["key"]] = {
                    "debit": totals["debit"],
                    "credit": totals["credit"],
                    "balance": totals["balance"],
                }
                summary_periods[period["key"]]["debit"] += totals["debit"]
                summary_periods[period["key"]]["credit"] += totals["credit"]
                summary_periods[period["key"]]["balance"] += totals["balance"]

                if ending_uses_all_periods or period["key"] == current_key:
                    has_visible_movement = has_visible_movement or not (
                        currency.is_zero(totals["debit"])
                        and currency.is_zero(totals["credit"])
                    )

            should_include = options["display_account"] == "all"
            if options["display_account"] == "movement":
                should_include = has_visible_movement or not (
                    currency.is_zero(initial_balance) and currency.is_zero(ending_balance)
                )
            elif options["display_account"] == "not_zero":
                should_include = not currency.is_zero(ending_balance)

            if not should_include:
                # Roll back period aggregates for skipped rows.
                for period in period_config["periods"]:
                    totals = period_totals[period["key"]].get(account.id, empty_totals)
                    summary_periods[period["key"]]["debit"] -= totals["debit"]
                    summary_periods[period["key"]]["credit"] -= totals["credit"]
                    summary_periods[period["key"]]["balance"] -= totals["balance"]
                continue

            payload_accounts.append(
                {
                    "id": account.id,
                    "code": account.code,
                    "name": account.name,
                    "initial_balance": {
                        "debit": initial_debit,
                        "credit": initial_credit,
                        "balance": initial_balance,
                    },
                    "period_values": period_values,
                    "ending_balance": {
                        "debit": ending_debit,
                        "credit": ending_credit,
                        "balance": ending_balance,
                    },
                }
            )
            summary_initial_debit += initial_debit
            summary_initial_credit += initial_credit
            summary_ending_debit += ending_debit
            summary_ending_credit += ending_credit

        return {
            "options": options,
            "periods": [
                {
                    "key": period["key"],
                    "label": period["label"],
                    "is_current": period["key"] == current_key,
                }
                for period in period_config["periods"]
            ],
            "summary": {
                "account_count": len(payload_accounts),
                "initial_balance": {
                    "debit": summary_initial_debit,
                    "credit": summary_initial_credit,
                },
                "period_totals": summary_periods,
                "ending_balance": {
                    "debit": summary_ending_debit,
                    "credit": summary_ending_credit,
                },
            },
            "accounts": payload_accounts,
            "meta": {
                "company_name": company.display_name,
                "currency_id": company.currency_id.id,
                "comparison_mode": options["comparison_mode"],
            },
        }

    @api.model
    def _sanitize_owl_options(self, options):
        journal_ids = options.get("journal_ids")
        if journal_ids is None:
            journal_ids = self.env["account.journal"].search(
                [("company_id", "=", self.env.company.id)]
            ).ids

        comparison_count = options.get("comparison_period_count", 10)
        try:
            comparison_count = int(comparison_count)
        except (TypeError, ValueError):
            comparison_count = 10

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
            "journal_ids": self._sanitize_ids(journal_ids),
            "account_ids": self._sanitize_ids(options.get("account_ids", [])),
            "analytic_account_ids": self._sanitize_ids(
                options.get("analytic_account_ids", [])
            ),
            "comparison_mode": self._sanitize_selection(
                options.get("comparison_mode"),
                {
                    "no_comparison",
                    "previous_period",
                    "same_period_last_year",
                    "custom_date",
                },
                "no_comparison",
            ),
            "comparison_period_count": max(1, min(comparison_count, 12)),
            "comparison_date_from": options.get("comparison_date_from") or False,
            "comparison_date_to": options.get("comparison_date_to") or False,
            "comparison_order": self._sanitize_selection(
                options.get("comparison_order"),
                {"asc", "desc"},
                "asc",
            ),
        }

    @api.model
    def _sanitize_and_validate_owl_options(self, options):
        options = self._sanitize_owl_options(options)
        if not options["date_from"] or not options["date_to"]:
            raise UserError(_("You must define a Start Date and End Date."))
        if options["date_from"] > options["date_to"]:
            raise UserError(_("The Start Date must be before the End Date."))
        if options["comparison_mode"] == "custom_date":
            if not options["comparison_date_from"] or not options["comparison_date_to"]:
                raise UserError(_("You must define Comparison Start Date and End Date."))
            if options["comparison_date_from"] > options["comparison_date_to"]:
                raise UserError(
                    _("The Comparison Start Date must be before the End Date.")
                )
        return options

    @api.model
    def _build_owl_move_line_domain(
        self,
        options,
        account_ids,
        analytic_accounts=False,
        date_from=False,
        date_to=False,
        initial_balance=False,
    ):
        domain = [
            ("display_type", "not in", ("line_section", "line_note")),
            ("parent_state", "!=", "cancel"),
            ("company_id", "=", self.env.company.id),
            ("account_id", "in", account_ids),
        ]
        if date_to and not initial_balance:
            domain.append(("date", "<=", date_to))
        if date_from:
            operator = "<" if initial_balance else ">="
            domain.append(("date", operator, date_from))
        if options["journal_ids"]:
            domain.append(("journal_id", "in", options["journal_ids"]))
        if options["target_move"] != "all":
            domain.append(("parent_state", "=", options["target_move"]))
        if analytic_accounts:
            domain.append(("analytic_distribution", "in", analytic_accounts.ids))
        return domain

    @api.model
    def _get_owl_accounts(self, options):
        company = self.env.company
        account_domain = [("company_ids", "in", [company.id])]
        if options["account_ids"]:
            account_domain.append(("id", "in", options["account_ids"]))
        return self.env["account.account"].search(account_domain, order="code, id")

    @api.model
    def _build_period_config(self, options):
        current_start = fields.Date.from_string(options["date_from"])
        current_end = fields.Date.from_string(options["date_to"])
        current_period = {
            "key": "current_period",
            "label": self._format_period_label(current_start, current_end),
            "date_from": options["date_from"],
            "date_to": options["date_to"],
        }
        comparison_periods = []
        comparison_mode = options["comparison_mode"]

        if comparison_mode == "previous_period":
            comparison_periods = self._build_previous_periods(
                current_start,
                current_end,
                options["comparison_period_count"],
                options["comparison_order"],
            )
        elif comparison_mode == "same_period_last_year":
            comparison_start = current_start + relativedelta(years=-1)
            comparison_end = current_end + relativedelta(years=-1)
            comparison_periods = [
                {
                    "key": "comparison_same_period_last_year",
                    "label": self._format_period_label(comparison_start, comparison_end),
                    "date_from": fields.Date.to_string(comparison_start),
                    "date_to": fields.Date.to_string(comparison_end),
                }
            ]
        elif comparison_mode == "custom_date":
            comparison_start = fields.Date.from_string(options["comparison_date_from"])
            comparison_end = fields.Date.from_string(options["comparison_date_to"])
            comparison_periods = [
                {
                    "key": "comparison_custom_date",
                    "label": self._format_period_label(comparison_start, comparison_end),
                    "date_from": options["comparison_date_from"],
                    "date_to": options["comparison_date_to"],
                }
            ]

        initial_anchor_start = options["date_from"]
        if comparison_mode == "previous_period" and comparison_periods:
            initial_anchor_start = min(
                period["date_from"] for period in comparison_periods
            )

        return {
            "comparison_mode": comparison_mode,
            "current_period_key": current_period["key"],
            "initial_anchor_start": initial_anchor_start,
            "periods": [*comparison_periods, current_period],
        }

    @api.model
    def _build_previous_periods(self, current_start, current_end, count, order):
        period_type = self._detect_period_type(current_start, current_end)
        periods = []

        if period_type == "month":
            for offset in range(count, 0, -1):
                period_start = current_start + relativedelta(months=-offset)
                period_end = period_start + relativedelta(months=1, days=-1)
                periods.append(
                    {
                        "key": f"comparison_previous_{offset}",
                        "label": self._format_period_label(period_start, period_end),
                        "date_from": fields.Date.to_string(period_start),
                        "date_to": fields.Date.to_string(period_end),
                    }
                )
        elif period_type == "quarter":
            for offset in range(count, 0, -1):
                period_start = current_start + relativedelta(months=-(offset * 3))
                period_end = period_start + relativedelta(months=3, days=-1)
                periods.append(
                    {
                        "key": f"comparison_previous_{offset}",
                        "label": self._format_period_label(period_start, period_end),
                        "date_from": fields.Date.to_string(period_start),
                        "date_to": fields.Date.to_string(period_end),
                    }
                )
        elif period_type == "year":
            for offset in range(count, 0, -1):
                period_start = current_start + relativedelta(years=-offset)
                period_end = period_start + relativedelta(years=1, days=-1)
                periods.append(
                    {
                        "key": f"comparison_previous_{offset}",
                        "label": self._format_period_label(period_start, period_end),
                        "date_from": fields.Date.to_string(period_start),
                        "date_to": fields.Date.to_string(period_end),
                    }
                )
        else:
            period_span = (current_end - current_start).days
            next_period_end = current_start - timedelta(days=1)
            for offset in range(count, 0, -1):
                period_start = next_period_end - timedelta(days=period_span)
                periods.append(
                    {
                        "key": f"comparison_previous_{offset}",
                        "label": self._format_period_label(period_start, next_period_end),
                        "date_from": fields.Date.to_string(period_start),
                        "date_to": fields.Date.to_string(next_period_end),
                    }
                )
                next_period_end = period_start - timedelta(days=1)
            periods.reverse()

        if order == "desc":
            periods.reverse()
        return periods

    @api.model
    def _detect_period_type(self, start, end):
        if not (start and end):
            return "custom"
        if (
            start.day == 1
            and start.month == end.month
            and start.year == end.year
            and end == (start + relativedelta(months=1, days=-1))
        ):
            return "month"

        quarter_start_month = ((start.month - 1) // 3) * 3 + 1
        quarter_end = fields.Date.from_string(
            fields.Date.to_string(start + relativedelta(month=quarter_start_month, months=3, day=1, days=-1))
        )
        if (
            start.day == 1
            and start.month == quarter_start_month
            and end == quarter_end
        ):
            return "quarter"

        if (
            start.day == 1
            and start.month == 1
            and end.day == 31
            and end.month == 12
            and start.year == end.year
        ):
            return "year"
        return "custom"

    @api.model
    def _format_period_label(self, start, end):
        period_type = self._detect_period_type(start, end)
        if period_type == "month":
            return start.strftime("%b %Y")
        if period_type == "quarter":
            return f"Q{((start.month - 1) // 3) + 1} {start.year}"
        if period_type == "year":
            return str(start.year)
        return f"{start.strftime('%m/%d/%Y')} - {end.strftime('%m/%d/%Y')}"

    @api.model
    def _split_balance(self, balance):
        return (balance, 0.0) if balance >= 0 else (0.0, abs(balance))

    @api.model
    def _get_owl_grouped_account_totals(
        self,
        account_ids,
        options,
        analytic_accounts=False,
        date_from=False,
        date_to=False,
        initial_balance=False,
    ):
        if not account_ids:
            return {}
        rows = self.env["account.move.line"]._read_group(
            domain=self._build_owl_move_line_domain(
                options,
                account_ids,
                analytic_accounts=analytic_accounts,
                date_from=date_from,
                date_to=date_to,
                initial_balance=initial_balance,
            ),
            groupby=["account_id"],
            aggregates=["debit:sum", "credit:sum"],
        )
        return {
            account.id: {
                "debit": debit or 0.0,
                "credit": credit or 0.0,
                "balance": (debit or 0.0) - (credit or 0.0),
            }
            for account, debit, credit in rows
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
