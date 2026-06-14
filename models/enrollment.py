from odoo import Command, api, fields, models, _
from odoo.exceptions import UserError, ValidationError


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
        default="New",
        readonly=True,
        copy=False,
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

    student_email = fields.Char(
        string="Student Email",
        related="student_id.email",
        readonly=True,
    )

    course_state = fields.Selection(
        related="course_id.state",
        string="Course Status",
        readonly=True,
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
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("x.academy.enrollment")
                    or "New"
                )
        return super().create(vals_list)

    def write(self, vals):
        protected_fields = {
            "course_id",
            "student_id",
        }

        changing_protected_fields = bool(protected_fields.intersection(vals.keys()))

        for record in self:
            if changing_protected_fields and record.state in ["confirmed", "done", "cancelled"]:
                raise UserError(
                    _(
                        "You cannot change course or student after the enrollment "
                        "has been confirmed, done, or cancelled."
                    )
                )

            if "session_id" in vals and record.state in ["done", "cancelled"]:
                raise UserError(
                    _("You cannot change session after the enrollment is done or cancelled.")
                )

        if vals.get("state") == "confirmed":
            for record in self:
                record._validate_before_confirm()

        result = super().write(vals)

        if vals.get("state") == "confirmed":
            self._sync_student_to_session_attendees()

        return result

    def unlink(self):
        for record in self:
            if record.state not in ["draft", "cancelled"]:
                raise UserError(
                    _("You can only delete an enrollment in Draft or Cancelled status.")
                )
        return super().unlink()

    @api.onchange("course_id")
    def _onchange_course_id(self):
        for record in self:
            if record.session_id and record.session_id.course_id != record.course_id:
                record.session_id = False

    @api.constrains("course_id", "session_id")
    def _check_session_belongs_to_course(self):
        for record in self:
            if record.session_id and record.session_id.course_id != record.course_id:
                raise ValidationError(
                    _("The selected session must belong to the selected course.")
                )

    def _validate_before_confirm(self):
        for record in self:
            if record.course_id.state != "confirmed":
                raise ValidationError(
                    _("You can only confirm enrollment for a confirmed course.")
                )

            record._validate_course_capacity()
            record._validate_session_capacity()

    def _validate_course_capacity(self):
        for record in self:
            course = record.course_id

            if not course.seats:
                return

            confirmed_count = self.search_count(
                [
                    ("course_id", "=", course.id),
                    ("state", "=", "confirmed"),
                    ("id", "!=", record.id),
                ]
            )

            if confirmed_count >= course.seats:
                raise ValidationError(
                    _(
                        "No seats available for this course. "
                        "Course: %(course)s. Seats: %(seats)s."
                    )
                    % {
                        "course": course.display_name,
                        "seats": course.seats,
                    }
                )

    def _validate_session_capacity(self):
        for record in self:
            session = record.session_id

            if not session:
                return

            capacity = session._get_effective_capacity()

            if not capacity:
                return

            confirmed_count = self.search_count(
                [
                    ("session_id", "=", session.id),
                    ("state", "=", "confirmed"),
                    ("id", "!=", record.id),
                ]
            )

            if confirmed_count >= capacity:
                raise ValidationError(
                    _(
                        "No seats available for this session. "
                        "Session: %(session)s. Capacity: %(capacity)s."
                    )
                    % {
                        "session": session.display_name,
                        "capacity": capacity,
                    }
                )

    def _sync_student_to_session_attendees(self):
        for record in self:
            if record.state == "confirmed" and record.session_id and record.student_id:
                record.session_id.write(
                    {"attendee_ids": [Command.link(record.student_id.id)]}
                )

    def _remove_student_from_session_attendees(self):
        for record in self:
            if record.session_id and record.student_id:
                record.session_id.write(
                    {"attendee_ids": [Command.unlink(record.student_id.id)]}
                )

    def action_confirm(self):
        self.write({"state": "confirmed"})

    def action_done(self):
        for record in self:
            if record.state != "confirmed":
                raise UserError(_("Only confirmed enrollments can be marked as done."))
        self.write({"state": "done"})

    def action_cancel(self):
        for record in self:
            if record.state == "done":
                raise UserError(_("You cannot cancel an enrollment that is already done."))

        self._remove_student_from_session_attendees()
        self.write({"state": "cancelled"})

    def action_reset_to_draft(self):
        for record in self:
            if record.state == "done":
                raise UserError(_("You cannot reset a done enrollment to draft."))
        self.write({"state": "draft"})