# -*- coding: utf-8 -*-

import os
import glob
from datetime import datetime

from odoo import models, fields, _
from odoo.exceptions import ValidationError


class BackupRecordFile(models.Model):
    _name = "backup.record.file"
    _description = "Backup Files for Record"
    _order = "backup_date desc, name"

    backup_id = fields.Many2one(
        "backup.record",
        string="Backup Record",
        ondelete="cascade",
        required=True,
        index=True,
    )
    name = fields.Char(string="File Name", required=True)
    full_path = fields.Char(string="Full Path", readonly=True)
    size_bytes = fields.Integer(string="Size (bytes)", readonly=True)
    size_human = fields.Char(string="Size", readonly=True)
    backup_date = fields.Datetime(string="Modified Time", readonly=True)

    def open_folder_help(self):
        # optional placeholder for future actions (e.g. download)
        return True
