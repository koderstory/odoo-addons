# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # field ini sudah kamu punya; kalau sudah ada di module lain, hapus deklarasi ini.
    purchase_request = fields.Boolean(
        help="Check this box to generate Purchase Request instead of generating RFQ from procurement.",
        company_dependent=True,
    )

    def _ks_has_buy_route(self, company):
        """Cek apakah produk punya Buy route (dari product routes + category routes)."""
        self.ensure_one()

        # ambil semua route yang action-nya buy (route bisa global atau per company)
        buy_routes = self.env["stock.route"].with_context(active_test=False).search([
            ("rule_ids.action", "=", "buy"),
            ("company_id", "in", [False, company.id]),
        ])

        effective_routes = (self.route_ids | self.categ_id.route_ids).filtered(
            lambda r: (not r.company_id) or (r.company_id == company)
        )
        return bool(effective_routes & buy_routes)

    @api.model_create_multi
    def create(self, vals_list):
        templates = super().create(vals_list)
        templates._ks_auto_enable_purchase_request_on_buy_route()
        return templates

    def write(self, vals):
        res = super().write(vals)
        # hanya re-check kalau perubahan bisa berdampak ke routes/category
        if any(k in vals for k in ("route_ids", "categ_id")):
            self._ks_auto_enable_purchase_request_on_buy_route()
        return res

    def _ks_auto_enable_purchase_request_on_buy_route(self):
        """Auto-check purchase_request jika Buy route aktif. (Tidak auto-uncheck)"""
        if self.env.context.get("ks_skip_pr_autoset"):
            return

        for company in self.env.companies:
            for tmpl in self.with_company(company):
                if tmpl.purchase_request:
                    continue  # sudah True, skip
                if tmpl._ks_has_buy_route(company):
                    tmpl.with_context(ks_skip_pr_autoset=True).with_company(company).write(
                        {"purchase_request": True}
                    )
