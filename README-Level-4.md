Dưới đây là **Level 4 — Business Logic chuyên sâu** cho module `x_academy`.

Mục tiêu của Level 4 là đưa module từ mức “có quan hệ dữ liệu” lên mức **có luật nghiệp vụ thật**: sequence tự động, kiểm soát capacity, kiểm soát trạng thái, chặn sửa/xóa sai quy trình, validate ngày giờ, validate trùng lịch instructor, và tự đồng bộ student vào session attendees.

Odoo ORM là lớp trung tâm để khai báo business objects bằng Python class kế thừa `Model`, tránh phải viết SQL thủ công trong đa số trường hợp và cung cấp persistence/security services cho model. ([Odoo][1]) Với constraints, Odoo khuyến nghị dùng SQL constraints khi phù hợp vì thường hiệu quả hơn Python constraints; còn Python constraints dùng cho logic nghiệp vụ phức tạp hơn. ([Odoo][2])

---

# 1. Business logic sẽ thêm ở Level 4

Sau bài này, module sẽ có thêm:

| Nhóm logic          | Nội dung                                                                           |
| ------------------- | ---------------------------------------------------------------------------------- |
| Auto sequence       | Course code: `CRS/2026/00001`, Enrollment reference: `ENR/2026/00001`              |
| Create override     | Tự sinh mã khi tạo Course/Enrollment                                               |
| Write protection    | Không cho sửa field quan trọng sau khi Course/Session/Enrollment đã confirmed/done |
| Delete protection   | Không cho xóa record đã confirmed/done                                             |
| Course capacity     | Không cho confirmed enrollment vượt quá số seats của Course                        |
| Session capacity    | Không cho confirmed enrollment vượt quá sức chứa của Session                       |
| Date validation     | Session phải nằm trong khoảng ngày của Course                                      |
| Instructor conflict | Instructor không được dạy 2 session confirmed bị overlap thời gian                 |
| Enrollment workflow | Confirm enrollment sẽ tự thêm student vào `session.attendee_ids`                   |
| Cancel enrollment   | Cancel enrollment sẽ remove student khỏi session attendees                         |
| Robustness          | Logic nằm ở Python model, không chỉ nằm ở UI button                                |

---

# 2. Cấu trúc module sau Level 4

Thêm thư mục `data`:

```text id="14q0ob"
x_academy/
├── data/
│   └── sequence.xml
├── models/
│   ├── course.py
│   ├── session.py
│   ├── enrollment.py
│   └── res_partner.py
├── security/
│   ├── security.xml
│   └── ir.model.access.csv
└── views/
    ├── course_views.xml
    ├── session_views.xml
    ├── enrollment_views.xml
    ├── res_partner_views.xml
    └── menus.xml
```

---

# 3. Cập nhật `__manifest__.py`

Thêm `data/sequence.xml` trước views:

```python id="zoz2sf"
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
        "data/sequence.xml",
        "views/course_views.xml",
        "views/session_views.xml",
        "views/enrollment_views.xml",
        "views/res_partner_views.xml",
        "views/menus.xml",
    ],
    "application": True,
    "installable": True,
}
```

---

# 4. Thêm sequence

Tạo file:

```text id="efmqb7"
custom_addons/x_academy/data/sequence.xml
```

Nội dung:

```xml id="5z4eza"
<odoo>
    <record id="seq_x_academy_course" model="ir.sequence">
        <field name="name">Academy Course Sequence</field>
        <field name="code">x.academy.course</field>
        <field name="prefix">CRS/%(year)s/</field>
        <field name="padding">5</field>
        <field name="company_id" eval="False"/>
    </record>

    <record id="seq_x_academy_enrollment" model="ir.sequence">
        <field name="name">Academy Enrollment Sequence</field>
        <field name="code">x.academy.enrollment</field>
        <field name="prefix">ENR/%(year)s/</field>
        <field name="padding">5</field>
        <field name="company_id" eval="False"/>
    </record>
</odoo>
```

Sau khi cài/update module, Course mới sẽ có code dạng:

```text id="wz2ivx"
CRS/2026/00001
```

Enrollment mới sẽ có reference dạng:

```text id="1fh2p5"
ENR/2026/00001
```

---

# 5. Cập nhật `course.py`

Thay toàn bộ file:

```text id="x6pcpo"
custom_addons/x_academy/models/course.py
```

bằng code sau:

```python id="118c5s"
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
```

## Logic quan trọng trong `course.py`

Có 3 điểm đáng chú ý.

Thứ nhất, sequence được sinh ở `create()`:

```python id="2p54w0"
@api.model_create_multi
def create(self, vals_list):
    for vals in vals_list:
        if vals.get("code", "New") == "New":
            vals["code"] = (
                self.env["ir.sequence"].next_by_code("x.academy.course")
                or "New"
            )
    return super().create(vals_list)
```

Thứ hai, không cho sửa `name`, `code`, `start_date`, `end_date` sau khi course đã confirmed/done/cancelled.

Thứ ba, không cho giảm `seats` xuống thấp hơn số enrollment đã confirmed.

---

# 6. Cập nhật `session.py`

Thay toàn bộ file:

```text id="9b5awf"
custom_addons/x_academy/models/session.py
```

bằng code sau:

```python id="8nxz4i"
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
```

## Logic quan trọng trong `session.py`

Có 3 logic đáng chú ý.

Một là session phải nằm trong thời gian của course:

```python id="eomna5"
session_start_date = fields.Date.to_date(record.date_start)
session_end_date = fields.Date.to_date(record.date_end)
```

Hai là instructor không được bị trùng lịch confirmed session:

```python id="esxa9d"
("date_start", "<", record.date_end),
("date_end", ">", record.date_start),
```

Đây là công thức overlap thời gian chuẩn:

```text id="dwly8z"
A.start < B.end AND A.end > B.start
```

Ba là action `action_fill_attendees_from_enrollments()` giúp lấy confirmed enrollments và đẩy student vào session attendees.

---

# 7. Cập nhật `enrollment.py`

Thay toàn bộ file:

```text id="47gp0x"
custom_addons/x_academy/models/enrollment.py
```

bằng code sau:

```python id="xvhi4e"
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
```

## Logic quan trọng trong `enrollment.py`

Ở Level 3, `name` là computed field. Sang Level 4, ta chuyển thành sequence field:

```python id="cmykga"
name = fields.Char(
    string="Enrollment Reference",
    default="New",
    readonly=True,
    copy=False,
)
```

Khi confirm enrollment, hệ thống sẽ:

1. Kiểm tra course đã confirmed chưa.
2. Kiểm tra Course còn seats không.
3. Kiểm tra Session còn capacity không.
4. Nếu pass, chuyển state sang confirmed.
5. Nếu có session, tự thêm student vào session attendees.

---

# 8. Cập nhật view Course

Trong `course_views.xml`, nên sửa các field trong form để phản ánh logic mới.

Thay phần group chính trong form bằng đoạn sau:

```xml id="awz85g"
<group>
    <group>
        <field name="name" readonly="state != 'draft'"/>
        <field name="code" readonly="1"/>
        <field name="active"/>
        <field name="seats" readonly="state == 'done'"/>
        <field name="confirmed_enrollment_count" readonly="1"/>
        <field name="available_seats" readonly="1"/>
    </group>
    <group>
        <field name="start_date" readonly="state != 'draft'"/>
        <field name="end_date" readonly="state != 'draft'"/>
        <field name="duration_days" readonly="1"/>
    </group>
</group>
```

Trong list view, thêm `available_seats`:

```xml id="0c3eki"
<field name="available_seats"/>
```

Ví dụ list view nên là:

```xml id="6ly7ca"
<list string="Courses">
    <field name="sequence" widget="handle"/>
    <field name="name"/>
    <field name="code"/>
    <field name="start_date"/>
    <field name="end_date"/>
    <field name="seats"/>
    <field name="confirmed_enrollment_count"/>
    <field name="available_seats"/>
    <field name="state"/>
</list>
```

---

# 9. Cập nhật view Session

Trong `session_views.xml`, thêm `max_attendees` và `available_seats`.

List view:

```xml id="36lc88"
<list string="Sessions">
    <field name="name"/>
    <field name="course_id"/>
    <field name="date_start"/>
    <field name="date_end"/>
    <field name="instructor_id"/>
    <field name="max_attendees"/>
    <field name="attendee_count"/>
    <field name="available_seats"/>
    <field name="state"/>
</list>
```

Form view, thay phần group chính bằng:

```xml id="pbq63n"
<group>
    <group>
        <field name="name" readonly="state != 'draft'"/>
        <field name="course_id" readonly="state != 'draft'"/>
        <field name="instructor_id" readonly="state != 'draft'"/>
    </group>
    <group>
        <field name="date_start" readonly="state != 'draft'"/>
        <field name="date_end" readonly="state != 'draft'"/>
        <field name="max_attendees" readonly="state == 'done'"/>
        <field name="attendee_count" readonly="1"/>
        <field name="available_seats" readonly="1"/>
    </group>
</group>
```

Trong header của session form, thêm button:

```xml id="r5wyl5"
<button name="action_fill_attendees_from_enrollments"
        string="Fill Attendees"
        type="object"
        invisible="state == 'done'"/>
```

Header session đầy đủ nên là:

```xml id="24ar93"
<header>
    <button name="action_confirm"
            string="Confirm"
            type="object"
            class="btn-primary"
            invisible="state != 'draft'"/>

    <button name="action_done"
            string="Mark as Done"
            type="object"
            class="btn-primary"
            invisible="state != 'confirmed'"/>

    <button name="action_cancel"
            string="Cancel"
            type="object"
            invisible="state in ['done', 'cancelled']"/>

    <button name="action_reset_to_draft"
            string="Reset to Draft"
            type="object"
            invisible="state == 'draft'"/>

    <button name="action_fill_attendees_from_enrollments"
            string="Fill Attendees"
            type="object"
            invisible="state == 'done'"/>

    <field name="state"
           widget="statusbar"
           statusbar_visible="draft,confirmed,done"/>
</header>
```

---

# 10. Cập nhật view Enrollment

Trong `enrollment_views.xml`, list view nên là:

```xml id="j7r1ba"
<list string="Enrollments">
    <field name="name"/>
    <field name="course_id"/>
    <field name="course_state"/>
    <field name="student_id"/>
    <field name="student_email"/>
    <field name="session_id"/>
    <field name="enrollment_date"/>
    <field name="state"/>
</list>
```

Form view, thay group chính bằng:

```xml id="1kn5kd"
<group>
    <group>
        <field name="name" readonly="1"/>
        <field name="course_id" readonly="state != 'draft'"/>
        <field name="course_state" readonly="1"/>
        <field name="student_id" readonly="state != 'draft'"/>
        <field name="student_email" readonly="1"/>
    </group>
    <group>
        <field name="session_id"
               domain="[('course_id', '=', course_id)]"
               readonly="state in ['done', 'cancelled']"/>
        <field name="enrollment_date" readonly="state != 'draft'"/>
    </group>
</group>
```

---

# 11. Update module

Restart Odoo, rồi chạy:

```bash id="b86nkd"
./odoo-bin \
  -d odoo19_dev \
  --addons-path=addons,custom_addons \
  -u x_academy \
  --dev=xml
```

Nếu bạn đang chạy bằng service hoặc IDE, hãy nhớ restart server trước khi update module, vì ta đã sửa Python model.

---

# 12. Test case thủ công sau Level 4

## Test 1 — Course tự sinh mã

Tạo Course mới:

```text id="0brgv6"
Course Name: Odoo ORM Advanced
Seats: 2
Start Date: 2026-07-01
End Date: 2026-07-10
```

Expected:

```text id="xo5q7y"
Code = CRS/2026/00001
```

## Test 2 — Không confirm Course nếu thiếu seats

Tạo Course với:

```text id="799lno"
Seats = 0
```

Bấm Confirm.

Expected:

```text id="s3f1sh"
ValidationError: You must set seats before confirming the course.
```

## Test 3 — Không sửa ngày Course sau khi confirmed

Confirm Course rồi thử sửa `start_date`.

Expected:

```text id="o84a0p"
UserError: You cannot change course identity or dates after the course has been confirmed...
```

## Test 4 — Không enroll vượt Course seats

Course có:

```text id="u0jyro"
Seats = 2
```

Tạo 3 students và 3 enrollments.

Confirm enrollment thứ 3.

Expected:

```text id="4vjz86"
ValidationError: No seats available for this course.
```

## Test 5 — Không enroll vượt Session capacity

Session có:

```text id="hf5f3h"
Max Attendees = 1
```

Confirm 2 enrollments cùng session.

Expected:

```text id="k3j84u"
ValidationError: No seats available for this session.
```

## Test 6 — Instructor không được trùng lịch

Tạo 2 sessions cùng instructor:

```text id="8c4ax2"
Session A: 2026-07-01 09:00 → 2026-07-01 11:00
Session B: 2026-07-01 10:00 → 2026-07-01 12:00
```

Confirm Session A, sau đó confirm Session B.

Expected:

```text id="w3j13w"
ValidationError: Instructor already has another confirmed session during this time.
```

## Test 7 — Confirm enrollment tự thêm student vào session attendees

Tạo enrollment có preferred session rồi bấm Confirm.

Expected:

```text id="jic3hs"
Student xuất hiện trong Session → Attendees.
```

## Test 8 — Cancel enrollment remove student khỏi session attendees

Cancel enrollment đã confirmed.

Expected:

```text id="higz9f"
Student bị remove khỏi Session → Attendees.
```

---

# 13. Tư duy kiến trúc cần ghi nhớ

Ở Level 4, điều quan trọng nhất không phải là code dài hơn, mà là **đặt luật nghiệp vụ đúng chỗ**.

Không nên chỉ dựa vào UI:

```xml id="rm5ww5"
readonly="state != 'draft'"
```

Vì user vẫn có thể thay đổi dữ liệu qua:

```text id="6xmj2p"
import
RPC/API
server action
custom code
automated scripts
```

Do đó, UI chỉ là lớp hỗ trợ trải nghiệm. Luật thật phải nằm trong:

```python id="sdf16p"
create()
write()
unlink()
action_confirm()
@api.constrains()
_sql_constraints
```

Đây là điểm khác biệt giữa một module “demo được” và một module “có thể triển khai cho khách hàng”.

---

# 14. Level 4 đã hoàn thành những gì?

Sau Level 4, module `x_academy` đã có chất lượng gần với một module nghiệp vụ thực tế:

| Thành phần                   | Trạng thái |
| ---------------------------- | ---------- |
| Model structure              | Đã có      |
| Relations                    | Đã có      |
| Views/menu/action            | Đã có      |
| Security group/ACL           | Đã có      |
| Sequence                     | Đã có      |
| Workflow                     | Đã có      |
| Business validation          | Đã có      |
| Capacity control             | Đã có      |
| State-based protection       | Đã có      |
| Auto sync enrollment/session | Đã có      |
| Wizard                       | Chưa       |
| QWeb report                  | Chưa       |
| Email/chatter                | Chưa       |
| Scheduled action             | Chưa       |
| Tests                        | Chưa       |

Bài tiếp theo nên là **[Level 5 — Security chuẩn doanh nghiệp](README-Level-5.md)**: groups theo Odoo 19 `res.groups.privilege`, ACL chi tiết, record rules theo company/owner, field-level security, menu security, và các lỗi bảo mật thường gặp khi develop Odoo module.

[1]: https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/03_basicmodel.html?utm_source=chatgpt.com "Chapter 3: Models And Basic Fields"
[2]: https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/10_constraints.html?utm_source=chatgpt.com "Chapter 10: Constraints — Odoo 19.0 documentation"
