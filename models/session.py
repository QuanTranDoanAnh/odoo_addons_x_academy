from odoo import Command, api, fields, models, _
from odoo.exceptions import UserError, ValidationError


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

    max_attendees = fields.Integer(
        string="Max Attendees",
        default=0,
        help="If zero, the session uses the course capacity.",
    )

    attendee_count = fields.Integer(
        string="Attendee Count",
        compute="_compute_attendee_count",
    )

    available_seats = fields.Integer(
        string="Available Seats",
        compute="_compute_available_seats",
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

    def write(self, vals):
        protected_fields = {
            "course_id",
            "date_start",
            "date_end",
            "instructor_id",
        }

        changing_protected_fields = bool(protected_fields.intersection(vals.keys()))

        for record in self:
            if changing_protected_fields and record.state in ["confirmed", "done", "cancelled"]:
                raise UserError(
                    _(
                        "You cannot change course, dates, or instructor after the "
                        "session has been confirmed, done, or cancelled."
                    )
                )

            if "max_attendees" in vals and record.state == "done":
                raise UserError(_("You cannot change capacity after the session is done."))

        result = super().write(vals)

        if "max_attendees" in vals or "attendee_ids" in vals:
            self._validate_session_capacity()

        return result

    def unlink(self):
        for record in self:
            if record.state not in ["draft", "cancelled"]:
                raise UserError(
                    _("You can only delete a session in Draft or Cancelled status.")
                )
        return super().unlink()

    @api.depends("attendee_ids")
    def _compute_attendee_count(self):
        for record in self:
            record.attendee_count = len(record.attendee_ids)

    @api.depends("attendee_ids", "max_attendees", "course_id.seats")
    def _compute_available_seats(self):
        for record in self:
            capacity = record._get_effective_capacity()
            if capacity:
                record.available_seats = max(capacity - record.attendee_count, 0)
            else:
                record.available_seats = 0

    def _get_effective_capacity(self):
        self.ensure_one()
        return self.max_attendees or self.course_id.seats or 0

    @api.constrains("date_start", "date_end")
    def _check_session_dates(self):
        for record in self:
            if record.date_start and record.date_end and record.date_end < record.date_start:
                raise ValidationError(_("Session end time cannot be earlier than start time."))

    @api.constrains("course_id", "date_start", "date_end")
    def _check_session_inside_course_period(self):
        for record in self:
            if not record.course_id or not record.date_start or not record.date_end:
                continue

            if not record.course_id.start_date or not record.course_id.end_date:
                continue

            session_start_date = fields.Date.to_date(record.date_start)
            session_end_date = fields.Date.to_date(record.date_end)

            if session_start_date < record.course_id.start_date:
                raise ValidationError(
                    _("Session start date cannot be earlier than course start date.")
                )

            if session_end_date > record.course_id.end_date:
                raise ValidationError(
                    _("Session end date cannot be later than course end date.")
                )

    @api.constrains("max_attendees")
    def _check_max_attendees(self):
        for record in self:
            if record.max_attendees < 0:
                raise ValidationError(_("Max attendees cannot be negative."))

    @api.onchange("course_id")
    def _onchange_course_id(self):
        for record in self:
            if record.course_id and not record.name:
                record.name = record.course_id.name

            if record.course_id and not record.max_attendees:
                record.max_attendees = record.course_id.seats

    def _validate_session_capacity(self):
        for record in self:
            capacity = record._get_effective_capacity()
            if capacity and record.attendee_count > capacity:
                raise ValidationError(
                    _(
                        "Session capacity exceeded. Attendees: %(attendees)s. "
                        "Capacity: %(capacity)s."
                    )
                    % {
                        "attendees": record.attendee_count,
                        "capacity": capacity,
                    }
                )

    def _validate_instructor_no_overlap(self):
        for record in self:
            if not record.instructor_id or not record.date_start or not record.date_end:
                continue

            overlapping_session = self.search(
                [
                    ("id", "!=", record.id),
                    ("instructor_id", "=", record.instructor_id.id),
                    ("state", "=", "confirmed"),
                    ("date_start", "<", record.date_end),
                    ("date_end", ">", record.date_start),
                ],
                limit=1,
            )

            if overlapping_session:
                raise ValidationError(
                    _(
                        "Instructor %(instructor)s already has another confirmed "
                        "session during this time: %(session)s."
                    )
                    % {
                        "instructor": record.instructor_id.name,
                        "session": overlapping_session.display_name,
                    }
                )

    def action_confirm(self):
        for record in self:
            if record.course_id.state != "confirmed":
                raise UserError(_("You can only confirm a session for a confirmed course."))

            record._validate_session_capacity()
            record._validate_instructor_no_overlap()
            record.state = "confirmed"

    def action_done(self):
        for record in self:
            if record.state != "confirmed":
                raise UserError(_("Only confirmed sessions can be marked as done."))
            record.state = "done"

    def action_cancel(self):
        for record in self:
            if record.state == "done":
                raise UserError(_("You cannot cancel a session that is already done."))
            record.state = "cancelled"

    def action_reset_to_draft(self):
        for record in self:
            if record.state == "done":
                raise UserError(_("You cannot reset a done session to draft."))
            record.state = "draft"

    def action_fill_attendees_from_enrollments(self):
        for record in self:
            confirmed_enrollments = self.env["x.academy.enrollment"].search(
                [
                    ("course_id", "=", record.course_id.id),
                    ("state", "=", "confirmed"),
                    "|",
                    ("session_id", "=", False),
                    ("session_id", "=", record.id),
                ]
            )

            student_ids = confirmed_enrollments.mapped("student_id").ids
            record.write({"attendee_ids": [Command.set(student_ids)]})