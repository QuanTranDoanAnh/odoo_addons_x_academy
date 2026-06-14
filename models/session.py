from odoo import api, fields, models
from odoo.exceptions import ValidationError


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
        domain=[("is_academy_instructor", "=", True)],
    )

    attendee_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="x_academy_session_partner_rel",
        column1="session_id",
        column2="partner_id",
        string="Attendees",
        domain=[("is_academy_student", "=", True)],
    )

    attendee_count = fields.Integer(
        string="Attendee Count",
        compute="_compute_attendee_count",
    )

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
    )

    @api.depends("attendee_ids")
    def _compute_attendee_count(self):
        for record in self:
            record.attendee_count = len(record.attendee_ids)

    @api.constrains("date_start", "date_end")
    def _check_session_dates(self):
        for record in self:
            if record.date_start and record.date_end and record.date_end < record.date_start:
                raise ValidationError("Session end time cannot be earlier than start time.")

    @api.onchange("course_id")
    def _onchange_course_id(self):
        for record in self:
            if record.course_id and not record.name:
                record.name = record.course_id.name

    def action_confirm(self):
        for record in self:
            record.state = "confirmed"

    def action_done(self):
        for record in self:
            record.state = "done"

    def action_cancel(self):
        for record in self:
            record.state = "cancelled"

    def action_reset_to_draft(self):
        for record in self:
            record.state = "draft"