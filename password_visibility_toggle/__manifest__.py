{
    'name': 'Password Visibility Toggle',
    'author': 'Hiten Makasana',
    'category': 'Tools',
    'summary': 'This Odoo module adds a password visibility toggle button to the login page, allowing users to easily show or hide password. show password, password visible, hidden password, login form, visible password, password show',
    'description': """
        The Password Visibility Toggle module enhances the login page by adding a simple and intuitive toggle button to show or hide the password input. This feature improves the user experience, allowing users to verify their password before submission, ensuring better accuracy during login.
        By clicking the eye icon next to the password field, users can easily toggle between viewing the password in plain text or hiding it for privacy. This not only helps reduce login errors but also increases security by giving users more control over their login credentials.
        Ideal for improving accessibility and user-friendliness in login forms, this module is especially beneficial for users on devices with small screens or for those who struggle with remembering passwords. It ensures a smooth and secure login process, improving both user satisfaction and overall security.
        Features:
        - Password visibility toggle button on the login form
        - Show/Hide password functionality
        - User-friendly, easy to use for better login accuracy
        - Secure and privacy-conscious
    """,
    'maintainer': 'Hiten Makasana',
    'version': '1.0',
    'depends': ['base', 'web'],
    'data': [
        'view/web_login_template.xml',
    ],
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
