# -*- coding: utf-8 -*-

from odoo import models, fields, _


class BackupManualNameWizard(models.TransientModel):
    _name = "backup.manual.name.wizard"
    _description = "Manual Backup Name Wizard"

    backup_id = fields.Many2one(
        "backup.record",
        string="Backup Record",
        required=True,
        readonly=True,
    )
    manual_name = fields.Char(
        string="Backup File Name",
        help="Leave empty to use default naming (Backup_<db>_<date>).",
    )

    def action_confirm(self):
        """User clicked 'Run Backup' in the popup."""
        self.ensure_one()
        manual_name = (self.manual_name or "").strip()

        # Pass manual file name to the manual_execution via context
        ctx = dict(self.env.context or {})
        ctx["manual_file_name"] = manual_name
        ctx["from_wizard"] = True

        return self.backup_id.with_context(ctx).manual_execution()
