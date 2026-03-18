/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { deserializeDate, formatDate } from "@web/core/l10n/dates";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";
import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { useSetupAction } from "@web/search/action_hook";
import { formatMonetary } from "@web/views/fields/formatters";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

export class GeneralLedgerReport extends Component {
    static template = "accounting_owl_reports.GeneralLedgerReport";
    static components = { Layout, MultiRecordSelector, Dropdown, DropdownItem };
    static props = { ...standardActionServiceProps };

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.display = { controlPanel: {} };

        const savedState = this.props.state || {};
        const savedAmountDisplay =
            savedState.amountDisplay && savedState.amountDisplay !== "full"
                ? savedState.amountDisplay
                : "full_decimal";
        this.state = useState({
            loading: true,
            loadingReport: false,
            meta: savedState.meta || null,
            options: savedState.options || null,
            report: savedState.report || null,
            unfoldedAccountIds: savedState.unfoldedAccountIds || [],
            searchTerm: savedState.searchTerm || "",
            amountDisplay: savedAmountDisplay,
        });

        onWillStart(async () => {
            if (!this.state.meta || !this.state.options) {
                const meta = await this.orm.call(
                    "account.report.general.ledger",
                    "get_owl_initial_data",
                    []
                );
                this.state.meta = meta;
                this.state.options = { ...meta.defaults };
            }
            this.ensureDateRangeDefaults();
            if (!this.state.report) {
                await this.loadReport();
            } else if (!this.state.unfoldedAccountIds.length) {
                this.collapseAll();
            }
            this.state.loading = false;
        });

        useSetupAction({
            getLocalState: () => ({
                meta: this.state.meta,
                options: { ...this.state.options },
                report: this.state.report,
                unfoldedAccountIds: [...this.state.unfoldedAccountIds],
                searchTerm: this.state.searchTerm,
                amountDisplay: this.state.amountDisplay,
            }),
        });
    }

    get hasAccounts() {
        return Boolean(this.filteredAccounts.length);
    }

    get companyCurrencyId() {
        return this.state.meta?.currency?.id || this.state.report?.meta?.currency_id || false;
    }

    get advancedFilterCount() {
        const defaults = this.state.meta?.defaults || {};
        let count = 0;
        const comparedFields = ["display_account", "sortby", "initial_balance"];
        for (const fieldName of comparedFields) {
            if (this.state.options?.[fieldName] !== defaults[fieldName]) {
                count += 1;
            }
        }
        const recordFields = [
            ["journal_ids", defaults.journal_ids || []],
            ["account_ids", defaults.account_ids || []],
            ["partner_ids", defaults.partner_ids || []],
            ["analytic_account_ids", defaults.analytic_account_ids || []],
        ];
        for (const [fieldName, defaultValue] of recordFields) {
            const current = this.state.options?.[fieldName] || [];
            if (JSON.stringify(current) !== JSON.stringify(defaultValue)) {
                count += 1;
            }
        }
        return count;
    }

    get dateRangeSummary() {
        const { date_from: dateFrom, date_to: dateTo } = this.state.options || {};
        const start = this.parseDate(dateFrom);
        const end = this.parseDate(dateTo);
        const preset = this.detectDatePreset(start, end);
        if (start && end) {
            if (preset === "month") {
                return this.formatMonthYear(start);
            }
            if (preset === "quarter") {
                return `Q${Math.floor(start.getMonth() / 3) + 1} ${start.getFullYear()}`;
            }
            if (preset === "year") {
                return `${start.getFullYear()}`;
            }
            return `${this.formatLineDate(dateFrom)} - ${this.formatLineDate(dateTo)}`;
        }
        if (dateFrom) {
            return `From ${this.formatLineDate(dateFrom)}`;
        }
        if (dateTo) {
            return `Up to ${this.formatLineDate(dateTo)}`;
        }
        return "All Dates";
    }

    get currentDatePreset() {
        return this.detectDatePreset(
            this.parseDate(this.state.options?.date_from),
            this.parseDate(this.state.options?.date_to)
        );
    }

    get monthPresetLabel() {
        return new Intl.DateTimeFormat(undefined, { month: "long", year: "numeric" }).format(
            this.getDatePresetRange("month").start
        );
    }

    get quarterPresetLabel() {
        const { start, end } = this.getDatePresetRange("quarter");
        const formatter = new Intl.DateTimeFormat(undefined, { month: "short" });
        return `${formatter.format(start)} - ${formatter.format(end)} ${end.getFullYear()}`;
    }

    get yearPresetLabel() {
        return `${this.getDatePresetRange("year").start.getFullYear()}`;
    }

    get availableYears() {
        const selectedYear = this.selectedDateYear;
        const years = [];
        for (let year = selectedYear + 2; year >= selectedYear - 7; year--) {
            years.push(year);
        }
        return years;
    }

    get monthOptions() {
        return Array.from({ length: 12 }, (_, monthIndex) => ({
            value: monthIndex + 1,
            label: new Intl.DateTimeFormat(undefined, { month: "long" }).format(
                new Date(2026, monthIndex, 1)
            ),
        }));
    }

    get selectedDateYear() {
        return (
            this.parseDate(this.state.options?.date_from)
            || this.parseDate(this.state.options?.date_to)
            || new Date()
        ).getFullYear();
    }

    get selectedDateMonth() {
        return (
            this.parseDate(this.state.options?.date_from)
            || this.parseDate(this.state.options?.date_to)
            || new Date()
        ).getMonth() + 1;
    }

    get journalSummary() {
        const current = this.state.options?.journal_ids || [];
        const defaults = this.state.meta?.defaults?.journal_ids || [];
        if (!current.length || JSON.stringify(current) === JSON.stringify(defaults)) {
            return "All Journals";
        }
        if (current.length === 1) {
            const journal = this.state.meta?.journals?.find((item) => item.id === current[0]);
            return journal?.code || journal?.name || "1 Journal";
        }
        return `${current.length} Journals`;
    }

    get analyticSummary() {
        const total =
            (this.state.options?.account_ids?.length || 0)
            + (this.state.options?.analytic_account_ids?.length || 0);
        return total ? `Analytic (${total})` : "Analytic";
    }

    get targetMoveSummary() {
        const parts = [this.getSelectionLabel("target_move", this.state.options?.target_move)];
        if (this.state.options?.initial_balance) {
            parts.push("Initial Balance");
        }
        return parts.filter(Boolean).join(", ");
    }

    get amountDisplaySummary() {
        return this.getAmountDisplayLabel(this.state.amountDisplay);
    }

    get amountDisplayFullLabel() {
        return this.getAmountDisplayLabel("full");
    }

    get amountDisplayFullDecimalLabel() {
        return this.getAmountDisplayLabel("full_decimal");
    }

    get amountDisplayKLabel() {
        return this.getAmountDisplayLabel("k");
    }

    get amountDisplayMLabel() {
        return this.getAmountDisplayLabel("m");
    }

    get filteredAccounts() {
        const accounts = this.state.report?.accounts || [];
        const searchTerm = (this.state.searchTerm || "").trim().toLowerCase();
        if (!searchTerm) {
            return accounts;
        }
        return accounts.reduce((result, account) => {
            const accountText = `${account.code || ""} ${account.name || ""}`.toLowerCase();
            if (accountText.includes(searchTerm)) {
                result.push(account);
                return result;
            }
            const filteredLines = (account.move_lines || []).filter((line) => {
                const lineText = [
                    line.move_name,
                    line.reference,
                    line.label,
                    line.partner_name,
                    line.journal_code,
                ]
                    .filter(Boolean)
                    .join(" ")
                    .toLowerCase();
                return lineText.includes(searchTerm);
            });
            if (filteredLines.length) {
                result.push({
                    ...account,
                    move_lines: filteredLines,
                    line_count: filteredLines.length,
                });
            }
            return result;
        }, []);
    }

    getSelectorProps(resModel, fieldName, domain, fieldString, placeholder) {
        return {
            resModel,
            resIds: this.state.options?.[fieldName] || [],
            domain,
            update: (resIds) => this.updateRecordSelection(fieldName, resIds),
            fieldString,
            placeholder,
        };
    }

    getSelection(selectionName) {
        return this.state.meta?.selections?.[selectionName] || [];
    }

    getSelectionLabel(selectionName, value) {
        const option = this.getSelection(selectionName).find((item) => item.value === value);
        return option?.label || value || "";
    }

    updateOption(fieldName, value) {
        this.state.options[fieldName] = value;
    }

    updateBooleanOption(fieldName, ev) {
        this.state.options[fieldName] = ev.target.checked;
    }

    updateDateOption(fieldName, ev) {
        this.state.options[fieldName] = ev.target.value || false;
    }

    updateRecordSelection(fieldName, resIds) {
        this.state.options[fieldName] = [...resIds];
    }

    updateSearchTerm(ev) {
        this.state.searchTerm = ev.target.value;
    }

    selectTargetMove(value) {
        this.state.options.target_move = value;
    }

    toggleInitialBalanceQuick() {
        this.state.options.initial_balance = !this.state.options.initial_balance;
    }

    toggleJournalId(journalId) {
        const current = [...(this.state.options.journal_ids || [])];
        const index = current.indexOf(journalId);
        if (index >= 0) {
            current.splice(index, 1);
        } else {
            current.push(journalId);
        }
        this.state.options.journal_ids = current;
    }

    applyDatePreset(preset) {
        const { start, end } = this.getDatePresetRange(preset);
        this.state.options.date_from = this.toServerDate(start);
        this.state.options.date_to = this.toServerDate(end);
    }

    selectDateYear(ev) {
        this.applyYearSelection(Number(ev.target.value));
    }

    selectDateMonth(ev) {
        this.applyMonthSelection(this.selectedDateYear, Number(ev.target.value));
    }

    setAmountDisplay(mode) {
        this.state.amountDisplay = mode;
    }

    getAmountDisplayLabel(mode) {
        const currency = this.state.meta?.currency;
        if (!currency) {
            return "";
        }
        const symbol = currency.symbol || currency.name;
        if (mode === "full_decimal") {
            return `In .${symbol}`;
        }
        if (mode === "full") {
            return `In ${symbol}`;
        }
        if (mode === "k") {
            return `In K${symbol}`;
        }
        if (mode === "m") {
            return `In M${symbol}`;
        }
        return `In .${symbol}`;
    }

    isJournalSelected(journalId) {
        return (this.state.options?.journal_ids || []).includes(journalId);
    }

    parseDate(value) {
        return value ? new Date(`${value}T00:00:00`) : null;
    }

    ensureDateRangeDefaults() {
        if (!this.state.options?.date_from || !this.state.options?.date_to) {
            const today = new Date();
            const start = new Date(today.getFullYear(), today.getMonth(), 1);
            const end = this.getLastDayOfMonth(today);
            this.state.options.date_from = this.toServerDate(start);
            this.state.options.date_to = this.toServerDate(end);
        }
    }

    detectDatePreset(start, end) {
        if (!(start && end)) {
            return "custom";
        }
        if (
            start.getDate() === 1
            && start.getMonth() === end.getMonth()
            && start.getFullYear() === end.getFullYear()
            && end.getDate() === this.getLastDayOfMonth(end).getDate()
        ) {
            return "month";
        }
        const quarterStartMonth = Math.floor(start.getMonth() / 3) * 3;
        const quarterEnd = new Date(start.getFullYear(), quarterStartMonth + 3, 0);
        if (
            start.getDate() === 1
            && start.getMonth() === quarterStartMonth
            && end.getTime() === quarterEnd.getTime()
        ) {
            return "quarter";
        }
        if (
            start.getDate() === 1
            && start.getMonth() === 0
            && end.getMonth() === 11
            && start.getFullYear() === end.getFullYear()
            && end.getDate() === 31
        ) {
            return "year";
        }
        return "custom";
    }

    getBaseDate() {
        return this.parseDate(this.state.options?.date_to)
            || this.parseDate(this.state.options?.date_from)
            || new Date();
    }

    applyMonthSelection(year, month) {
        const monthIndex = month - 1;
        const start = new Date(year, monthIndex, 1);
        const end = new Date(year, monthIndex + 1, 0);
        this.state.options.date_from = this.toServerDate(start);
        this.state.options.date_to = this.toServerDate(end);
    }

    applyYearSelection(year) {
        const start = new Date(year, 0, 1);
        const end = new Date(year, 11, 31);
        this.state.options.date_from = this.toServerDate(start);
        this.state.options.date_to = this.toServerDate(end);
    }

    getDatePresetRange(preset) {
        const baseDate = this.getBaseDate();
        if (preset === "month") {
            return {
                start: new Date(baseDate.getFullYear(), baseDate.getMonth(), 1),
                end: this.getLastDayOfMonth(baseDate),
            };
        }
        if (preset === "quarter") {
            const quarterStartMonth = Math.floor(baseDate.getMonth() / 3) * 3;
            return {
                start: new Date(baseDate.getFullYear(), quarterStartMonth, 1),
                end: new Date(baseDate.getFullYear(), quarterStartMonth + 3, 0),
            };
        }
        return {
            start: new Date(baseDate.getFullYear(), 0, 1),
            end: new Date(baseDate.getFullYear(), 11, 31),
        };
    }

    getLastDayOfMonth(date) {
        return new Date(date.getFullYear(), date.getMonth() + 1, 0);
    }

    toServerDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, "0");
        const day = String(date.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    }

    formatMonthYear(date) {
        return new Intl.DateTimeFormat(undefined, { month: "short", year: "numeric" }).format(date);
    }

    async onApplyFilters(ev) {
        if (ev) {
            ev.preventDefault();
        }
        await this.loadReport();
    }

    async onResetFilters() {
        this.state.options = { ...this.state.meta.defaults };
        this.ensureDateRangeDefaults();
        this.state.amountDisplay = "full_decimal";
        this.state.searchTerm = "";
        await this.loadReport();
    }

    async loadReport() {
        this.state.loadingReport = true;
        try {
            this.state.report = await this.orm.call(
                "account.report.general.ledger",
                "get_owl_report_data",
                [],
                { options: this.state.options }
            );
            this.collapseAll();
        } finally {
            this.state.loadingReport = false;
        }
    }

    isUnfolded(accountId) {
        return this.state.unfoldedAccountIds.includes(accountId);
    }

    toggleAccount(accountId) {
        if (this.isUnfolded(accountId)) {
            this.state.unfoldedAccountIds = this.state.unfoldedAccountIds.filter(
                (id) => id !== accountId
            );
        } else {
            this.state.unfoldedAccountIds = [...this.state.unfoldedAccountIds, accountId];
        }
    }

    expandAll() {
        this.state.unfoldedAccountIds = (this.state.report?.accounts || []).map(
            (account) => account.id
        );
    }

    collapseAll() {
        this.state.unfoldedAccountIds = [];
    }

    openMoveLine(line) {
        if (!line.move_id) {
            return;
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            res_id: line.move_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    formatMoney(value, currencyId = this.companyCurrencyId) {
        if (this.state.amountDisplay === "full_decimal") {
            return formatMonetary(value || 0, { currencyId });
        }
        if (this.state.amountDisplay !== "full") {
            return this.formatCompactMoney(value, currencyId);
        }
        return this.formatRoundedMoney(value, currencyId);
    }

    formatRoundedMoney(value, currencyId = this.companyCurrencyId) {
        const amount = value || 0;
        const currency = this.state.meta?.currency;
        if (!currency || currencyId !== currency.id) {
            return new Intl.NumberFormat(undefined, {
                minimumFractionDigits: 0,
                maximumFractionDigits: 0,
            }).format(amount);
        }
        const formatted = new Intl.NumberFormat(undefined, {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(amount);
        return `${currency.symbol || currency.name} ${formatted}`;
    }

    formatCompactMoney(value, currencyId = this.companyCurrencyId) {
        const amount = value || 0;
        const currency = this.state.meta?.currency;
        if (!currency || currencyId !== currency.id) {
            return formatMonetary(amount, { currencyId });
        }
        const divisorByMode = { k: 1000, m: 1000000 };
        const suffixByMode = { k: "K", m: "M" };
        const divisor = divisorByMode[this.state.amountDisplay] || 1;
        const suffix = suffixByMode[this.state.amountDisplay] || "";
        const scaled = amount / divisor;
        const formatted = new Intl.NumberFormat(undefined, {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(scaled);
        return `${currency.symbol || currency.name} ${formatted}${suffix}`;
    }

    formatLineAmountCurrency(line) {
        if (!line.amount_currency) {
            return "";
        }
        return this.formatMoney(line.amount_currency, line.currency_id || this.companyCurrencyId);
    }

    formatLineDate(value) {
        if (!value) {
            return "";
        }
        return formatDate(deserializeDate(value));
    }
}

registry.category("actions").add("accounting_owl_reports.general_ledger", GeneralLedgerReport);
