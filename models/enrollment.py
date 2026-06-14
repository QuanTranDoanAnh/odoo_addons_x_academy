from odoo import api, fields, models
from odoo.exceptions import ValidationError


class XAcademyEnrollment(models.Model):
    _name = "x.academy.enrollment"
    _description = "Academy Enrollment"
    _order = "enrollment_date desc, id desc"

    _sql_constraints = [
        (
            "unique_student_course",
            "unique(student_id, course_id)",
            "This student is already enrolled in this course.",
        ),
    ]

    name = fields.Char(
        string="Enrollment Reference",
        compute="_compute_name",
        store=True,
    )

    course_id = fields.Many2one(
        comodel_name="x.academy.course",
        string="Course",
        required=True,
        ondelete="cascade",
    )

    student_id = fields.Many2one(
        comodel_name="res.partner",
        string="Student",
        required=True,
        domain=[("is_academy_student", "=", True)],
        ondelete="restrict",
    )

    session_id = fields.Many2one(
        comodel_name="x.academy.session",
        string="Preferred Session",
        ondelete="set null",
    )

    enrollment_date = fields.Date(
        default=fields.Date.context_today,
        required=True,
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

    @api.depends("student_id", "course_id")
    def _compute_name(self):
        for record in self:
            student_name = record.student_id.name or "No Student"
            course_name = record.course_id.name or "No Course"
            record.name = f"{student_name} - {course_name}"

    @api.onchange("course_id")
    def _onchange_course_id(self):
        for record in self:
            if record.session_id and record.session_id.course_id != record.course_id:
                record.session_id = False

    @api.constrains("course_id", "session_id")
    def _check_session_belongs_to_course(self):
        for record in self:
            if record.session_id and record.session_id.course_id != record.course_id:
                raise ValidationError("The selected session must belong to the selected course.")

    def action_confirm(self):
        for record in self:
            if record.course_id.state not in ["confirmed", "done"]:
                raise ValidationError("You can only confirm enrollment for a confirmed course.")

            if (
                record.course_id.seats
                and record.course_id.confirmed_enrollment_count >= record.course_id.seats
            ):
                raise ValidationError("No seats available for this course.")

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