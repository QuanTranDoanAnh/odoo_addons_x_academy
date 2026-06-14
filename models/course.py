from odoo import api, fields, models
from odoo.exceptions import ValidationError


class XAcademyCourse(models.Model):
    _name = "x.academy.course"
    _description = "Academy Course"
    _order = "sequence, name"

    _sql_constraints = [
        (
            "course_name_unique",
            "unique(name)",
            "Course name must be unique.",
        ),
        (
            "course_seats_positive",
            "CHECK(seats >= 0)",
            "Seats must be greater than or equal to zero.",
        ),
    ]

    name = fields.Char(string="Course Name", required=True)
    code = fields.Char(string="Course Code")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    description = fields.Text()
    start_date = fields.Date()
    end_date = fields.Date()
    seats = fields.Integer(default=0)

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
    )

    duration_days = fields.Integer(
        string="Duration (Days)",
        compute="_compute_duration_days",
        store=True,
    )

    session_ids = fields.One2many(
        comodel_name="x.academy.session",
        inverse_name="course_id",
        string="Sessions",
    )

    enrollment_ids = fields.One2many(
        comodel_name="x.academy.enrollment",
        inverse_name="course_id",
        string="Enrollments",
    )

    session_count = fields.Integer(
        string="Session Count",
        compute="_compute_session_count",
    )

    confirmed_enrollment_count = fields.Integer(
        string="Confirmed Enrollments",
        compute="_compute_confirmed_enrollment_count",
    )

    @api.depends("start_date", "end_date")
    def _compute_duration_days(self):
        for record in self:
            if record.start_date and record.end_date:
                record.duration_days = (record.end_date - record.start_date).days + 1
            else:
                record.duration_days = 0

    @api.depends("session_ids")
    def _compute_session_count(self):
        for record in self:
            record.session_count = len(record.session_ids)

    @api.depends("enrollment_ids.state")
    def _compute_confirmed_enrollment_count(self):
        for record in self:
            record.confirmed_enrollment_count = len(
                record.enrollment_ids.filtered(lambda enrollment: enrollment.state == "confirmed")
            )

    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date and record.end_date < record.start_date:
                raise ValidationError("End date cannot be earlier than start date.")

    def action_confirm(self):
        for record in self:
            if record.seats <= 0:
                raise ValidationError("You must set seats before confirming the course.")
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

    def action_view_sessions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Sessions",
            "res_model": "x.academy.session",
            "view_mode": "list,form,calendar",
            "domain": [("course_id", "=", self.id)],
            "context": {"default_course_id": self.id},
        }

    def action_view_enrollments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Enrollments",
            "res_model": "x.academy.enrollment",
            "view_mode": "list,form",
            "domain": [("course_id", "=", self.id)],
            "context": {"default_course_id": self.id},
        }