{
    "name": "Accounting OWL Reports",
    "version": "18.0.1.0.0",
    "summary": "OWL-based accounting reports for Invoicing",
    "category": "Accounting/Accounting",
    "depends": ["account", "web"],
    "data": [
        "security/ir.model.access.csv",
        "views/accounting_owl_report_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "accounting_owl_reports/static/src/actions/*.js",
            "accounting_owl_reports/static/src/xml/*.xml",
            "accounting_owl_reports/static/src/scss/*.scss",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}
