
# Bài 2 — Nâng module lên chuẩn nghiệp vụ

Sau khi module Level 1 chạy được, ta thêm constraints.

Sửa `models/course.py`:

```python
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class XAcademyCourse(models.Model):
    _name = "x.academy.course"
    _description = "Academy Course"
    _order = "sequence, name"

    _sql_constraints = [
        (
            "name_unique",
            "unique(name)",
            "Course name must be unique.",
        ),
        (
            "seats_positive",
            "CHECK(seats >= 0)",
            "Seats must be greater than or equal to zero.",
        ),
    ]

    name = fields.Char(string="Course Name", required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    description = fields.Text()
    start_date = fields.Date()
    end_date = fields.Date()
    seats = fields.Integer(default=0)

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
    )

    duration_days = fields.Integer(
        string="Duration (Days)",
        compute="_compute_duration_days",
        store=True,
    )

    @api.depends("start_date", "end_date")
    def _compute_duration_days(self):
        for record in self:
            if record.start_date and record.end_date:
                record.duration_days = (record.end_date - record.start_date).days + 1
            else:
                record.duration_days = 0

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
```

Thêm field vào view:

```xml
<field name="duration_days" readonly="1"/>
```

Ở đây bạn đã học 4 khái niệm nền tảng:

* computed field
* dependency bằng `@api.depends`
* Python constraint bằng `@api.constrains`
* SQL constraint bằng `_sql_constraints`

---

# Bài 3 — Thêm quan hệ dữ liệu

Ta thêm model Session.

File mới:

```text
custom_addons/x_academy/models/session.py
```

```python
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
```

Nhớ import:

```python
# models/__init__.py

from . import course
from . import session
```

Thêm vào `course.py`:

```python
session_ids = fields.One2many(
    comodel_name="x.academy.session",
    inverse_name="course_id",
    string="Sessions",
)
session_count = fields.Integer(
    compute="_compute_session_count",
    string="Sessions",
)

def _compute_session_count(self):
    for record in self:
        record.session_count = len(record.session_ids)
```

Lúc này bạn bắt đầu hiểu “xương sống” của Odoo module: **model + relation + views + access rights**.

---


Bài tiếp theo nên là **Level 3 đầy đủ**: tôi sẽ mở rộng module `x_academy` với `Session`, `Student`, `Instructor`, `Enrollment`, đầy đủ relation fields, menu, views và security tương ứng.