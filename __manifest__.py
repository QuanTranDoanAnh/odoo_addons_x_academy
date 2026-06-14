# custom_addons/x_academy/__manifest__.py

{
    "name": "X Academy",
    "summary": "Simple academy management module for Odoo 19 learning",
    "version": "19.0.1.0.0",
    "category": "Training",
    "author": "Your Company",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/course_views.xml",
    ],
    "application": True,
    "installable": True,
}