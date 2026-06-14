from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


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
    code = fields.Char(
        string="Course Code",
        default="New",
        readonly=True,
        copy=False,
    )
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
        copy=False,
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

    available_seats = fields.Integer(
        string="Available Seats",
        compute="_compute_available_seats",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code", "New") == "New":
                vals["code"] = (
                    self.env["ir.sequence"].next_by_code("x.academy.course")
                    or "New"
                )
        return super().create(vals_list)

    def write(self, vals):
        protected_fields = {
            "name",
            "code",
            "start_date",
            "end_date",
        }

        changing_protected_fields = bool(protected_fields.intersection(vals.keys()))

        for record in self:
            if changing_protected_fields and record.state in ["confirmed", "done", "cancelled"]:
                raise UserError(
                    _(
                        "You cannot change course identity or dates after the course "
                        "has been confirmed, done, or cancelled."
                    )
                )

            if "seats" in vals and record.state == "done":
                raise UserError(_("You cannot change seats after the course is done."))

        result = super().write(vals)

        if "seats" in vals:
            self._validate_capacity_not_below_confirmed_enrollments()

        return result

    def unlink(self):
        for record in self:
            if record.state not in ["draft", "cancelled"]:
                raise UserError(
                    _("You can only delete a course in Draft or Cancelled status.")
                )
        return super().unlink()

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
                record.enrollment_ids.filtered(
                    lambda enrollment: enrollment.state == "confirmed"
                )
            )

    @api.depends("seats", "enrollment_ids.state")
    def _compute_available_seats(self):
        for record in self:
            if record.seats:
                record.available_seats = max(
                    record.seats - record.confirmed_enrollment_count,
                    0,
                )
            else:
                record.available_seats = 0

    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date and record.end_date < record.start_date:
                raise ValidationError(_("End date cannot be earlier than start date."))

    def _validate_capacity_not_below_confirmed_enrollments(self):
        for record in self:
            if record.seats and record.confirmed_enrollment_count > record.seats:
                raise ValidationError(
                    _(
                        "Course capacity cannot be lower than confirmed enrollments. "
                        "Confirmed enrollments: %(confirmed)s. Seats: %(seats)s."
                    )
                    % {
                        "confirmed": record.confirmed_enrollment_count,
                        "seats": record.seats,
                    }
                )

    def action_confirm(self):
        for record in self:
            if record.seats <= 0:
                raise ValidationError(_("You must set seats before confirming the course."))

            if not record.start_date or not record.end_date:
                raise ValidationError(_("You must set start date and end date before confirming."))

            record._validate_capacity_not_below_confirmed_enrollments()
            record.state = "confirmed"

    def action_done(self):
        for record in self:
            if record.state != "confirmed":
                raise UserError(_("Only confirmed courses can be marked as done."))
            record.state = "done"

    def action_cancel(self):
        for record in self:
            if record.state == "done":
                raise UserError(_("You cannot cancel a course that is already done."))
            record.state = "cancelled"

    def action_reset_to_draft(self):
        for record in self:
            if record.state == "done":
                raise UserError(_("You cannot reset a done course to draft."))
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