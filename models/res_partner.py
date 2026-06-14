from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_academy_student = fields.Boolean(string="Academy Student")
    is_academy_instructor = fields.Boolean(string="Academy Instructor")

    academy_enrollment_ids = fields.One2many(
        comodel_name="x.academy.enrollment",
        inverse_name="student_id",
        string="Academy Enrollments",
    )

    academy_instructor_session_ids = fields.One2many(
        comodel_name="x.academy.session",
        inverse_name="instructor_id",
        string="Instructor Sessions",
    )