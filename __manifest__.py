
{
    "name": "X Academy",
    "summary": "Academy management module for Odoo 19 learning",
    "version": "19.0.1.0.0",
    "category": "Training",
    "author": "Your Company",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/course_views.xml",
        "views/session_views.xml",
        "views/enrollment_views.xml",
        "views/res_partner_views.xml",
        "views/menus.xml",
    ],
    "application": True,
    "installable": True,
}