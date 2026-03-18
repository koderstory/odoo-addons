/** @odoo-module **/

import { registry } from "@web/core/registry";

import { GeneralLedgerReport } from "./general_ledger_report";

export class TrialBalanceReport extends GeneralLedgerReport {
    static template = "accounting_owl_reports.TrialBalanceReport";
    static components = GeneralLedgerReport.components;
    static props = GeneralLedgerReport.props;

    get reportModel() {
        return "accounting.owl.trial.balance.report";
    }

    get hasAccounts() {
        return Boolean(this.filteredAccounts.length);
    }

    get targetMoveSummary() {
        return this.getSelectionLabel("target_move", this.state.options?.target_move);
    }

    get displayAccountSummary() {
        const value = this.state.options?.display_account || "all";
        if (value === "movement") {
            return "Movement";
        }
        if (value === "not_zero") {
            return "Not Zero";
        }
        return "All";
    }

    get comparisonSummary() {
        const mode = this.state.options?.comparison_mode || "no_comparison";
        if (mode === "previous_period") {
            const count = this.state.options?.comparison_period_count || 10;
            return `% Comparison: ${count} Previous Period${count === 1 ? "" : "s"}`;
        }
        if (mode === "same_period_last_year") {
            return "% Comparison: Same Period Last Year";
        }
        if (mode === "custom_date") {
            return "% Comparison: Custom Dates";
        }
        return "% Comparison";
    }

    get comparisonOrderLabel() {
        return this.getSelectionLabel(
            "comparison_order",
            this.state.options?.comparison_order
        );
    }

    get filteredAccounts() {
        const accounts = this.state.report?.accounts || [];
        const searchTerm = (this.state.searchTerm || "").trim().toLowerCase();
        if (!searchTerm) {
            return accounts;
        }
        return accounts.filter((account) => {
            const accountText = `${account.code || ""} ${account.name || ""}`.toLowerCase();
            return accountText.includes(searchTerm);
        });
    }

    selectComparisonMode(mode) {
        this.state.options.comparison_mode = mode;
    }

    selectDisplayAccount(value) {
        this.state.options.display_account = value;
    }

    updateComparisonPeriodCount(ev) {
        const value = Number(ev.target.value);
        this.state.options.comparison_period_count = Number.isFinite(value)
            ? Math.max(1, Math.min(value, 12))
            : 10;
    }

    updateComparisonOrder(ev) {
        this.state.options.comparison_order = ev.target.value;
    }

    updateComparisonDateOption(fieldName, ev) {
        this.state.options[fieldName] = ev.target.value || false;
    }

    getPeriodValue(account, periodKey) {
        return account.period_values?.[periodKey] || {
            debit: 0,
            credit: 0,
            balance: 0,
        };
    }

    getPeriodTotal(periodKey) {
        return this.state.report?.summary?.period_totals?.[periodKey] || {
            debit: 0,
            credit: 0,
            balance: 0,
        };
    }
}

registry.category("actions").add("accounting_owl_reports.trial_balance", TrialBalanceReport);
