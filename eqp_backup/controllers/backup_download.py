# -*- coding: utf-8 -*-

import os

from odoo import http, _
from odoo.exceptions import AccessError
from odoo.http import request, content_disposition


class BackupDownloadController(http.Controller):

    @http.route(
        "/eqp_backup/download_backup_file/<int:file_id>",
        type="http",
        auth="user",       # only logged-in users
        methods=["GET"],
    )
    def download_backup_file(self, file_id, **kwargs):
        """Stream the backup file to the browser."""

        # Get record with normal access rules
        BackupFile = request.env["backup.record.file"]
        record = BackupFile.browse(file_id)
        if not record.exists():
            return request.not_found()

        # Check access rights & rules on parent backup record
        try:
            record.check_access_rights("read")
            record.check_access_rule("read")
        except AccessError:
            return request.not_found()

        path = record.full_path
        if not path or not os.path.exists(path):
            return request.not_found()

        # Read file
        with open(path, "rb") as f:
            file_data = f.read()

        filename = record.name or os.path.basename(path)

        headers = [
            ("Content-Type", "application/octet-stream"),
            ("Content-Disposition", content_disposition(filename)),
        ]

        return request.make_response(file_data, headers)
