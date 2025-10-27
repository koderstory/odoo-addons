{
    "name": " Easy to hide/show the vendor's list of products to user.",

    'version': "18.0",

    'category': "Products",

   "summary": " Easy to hide/show the vendor's list of products to user.Control visibility of vendor details for specific users by managing access through user settings.",
    'description': """
        The "Hide Vendors" module enables vendor managers to control the visibility of vendor information for specific users. By using this module, managers can assign or revoke access to view vendor details through a simple checkbox in the user's settings.
    """,
    'author': "INKERP",
    'website': 'https://www.inkerp.com/',
    "depends": ["purchase"],

    "data": ["security/security.xml",
             "views/product_template.xml"],

    'images': ['static/description/banner.png'],
    'license': "OPL-1",
    'installable': True,
    'application': True,
    'auto_install': True,
}
