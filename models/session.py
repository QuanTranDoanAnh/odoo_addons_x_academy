from odoo import fields, models


class XAcademySession(models.Model):
    _name = "x.academy.session"
    _description = "Academy Session"
    _order = "date_start, name"

    name = fields.Char(required=True)
    course_id = fields.Many2one(
        comodel_name="x.academy.course",
        string="Course",
        required=True,
        ondelete="cascade",
    )
    date_start = fields.Datetime(required=True)
    date_end = fields.Datetime(required=True)
    instructor_id = fields.Many2one(
        comodel_name="res.partner",
        string="Instructor",
    )
    attendee_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="x_academy_session_partner_rel",
        column1="session_id",
        column2="partner_id",
        string="Attendees",
    )