Dưới đây là **Level 3 đầy đủ** cho module `x_academy`: thêm quan hệ dữ liệu giữa **Course**, **Session**, **Enrollment**, **Student** và **Instructor**.

Ở Level 3, trọng tâm là học đúng “xương sống” của Odoo Server Framework: business objects được khai báo bằng Python class kế thừa `models.Model`, ORM sẽ quản lý persistence, fields và quan hệ dữ liệu thay vì bạn phải viết SQL trực tiếp. ([Odoo][1]) Quan hệ giữa model trong Odoo thường dùng `Many2one`, `One2many`, `Many2many`; đặc biệt `One2many` luôn phụ thuộc vào một field `Many2one` ở model đối ứng. ([Odoo][2])

---

# 1. Kết quả sau Level 3

Sau bài này, module sẽ có cấu trúc dữ liệu như sau:

```text
Course
 ├── One2many → Session
 └── One2many → Enrollment
                  └── Many2one → Student / res.partner

Session
 ├── Many2one → Course
 ├── Many2one → Instructor / res.partner
 └── Many2many → Attendees / res.partner

res.partner
 ├── is_academy_student
 └── is_academy_instructor
```

Ta sẽ **không tạo model Student/Instructor riêng** ở Level 3, mà kế thừa `res.partner`. Đây là pattern rất hay trong Odoo vì Contact/Partner là master data chuẩn dùng chung cho customer, vendor, employee-like contact, student, instructor.

---

# 2. Cấu trúc module sau Level 3

```text
x_academy/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
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

```python
# custom_addons/x_academy/__manifest__.py

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

Odoo module được khai báo bằng manifest file, trong đó bạn khai báo dependency và danh sách data files cần load khi install/update module. ([Odoo][3])

---

# 4. Cập nhật file import

## `x_academy/__init__.py`

```python
from . import models
```

## `x_academy/models/__init__.py`

```python
from . import course
from . import session
from . import enrollment
from . import res_partner
```

---

# 5. Model 1 — Course

File:

```text
custom_addons/x_academy/models/course.py
```

Code:

```python
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
```

Điểm học chính:

* `session_ids` là `One2many` vì một Course có nhiều Session.
* `enrollment_ids` là `One2many` vì một Course có nhiều Enrollment.
* `confirmed_enrollment_count` được tính từ các enrollment đã xác nhận.
* `action_view_sessions` và `action_view_enrollments` dùng để mở danh sách record liên quan từ smart button.

---

# 6. Model 2 — Session

File:

```text
custom_addons/x_academy/models/session.py
```

Code:

```python
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
```

Điểm học chính:

* `course_id` là `Many2one`: mỗi Session thuộc về một Course.
* `instructor_id` cũng là `Many2one` tới `res.partner`.
* `attendee_ids` là `Many2many`: một session có nhiều attendees, một student có thể tham gia nhiều sessions.
* `domain` giúp lọc Contact chỉ lấy người được đánh dấu là Instructor hoặc Student.

---

# 7. Model 3 — Enrollment

File:

```text
custom_addons/x_academy/models/enrollment.py
```

Code:

```python
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
```

Điểm học chính:

* `Enrollment` là transaction model.
* Nó nối `Course` và `Student`.
* `_sql_constraints` chặn một student đăng ký trùng một course.
* `session_id` là optional để chọn session ưu tiên.
* Constraint đảm bảo session được chọn thuộc đúng course.

---

# 8. Model 4 — Kế thừa `res.partner`

File:

```text
custom_addons/x_academy/models/res_partner.py
```

Code:

```python
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
```

Odoo hỗ trợ inheritance để mở rộng model có sẵn một cách modular, ví dụ thêm field hoặc behavior vào `res.partner` mà không sửa core source code. ([Odoo][4])

---

# 9. Security groups

File:

```text
custom_addons/x_academy/security/security.xml
```

Code:

```xml
<odoo>
    <record id="module_category_x_academy" model="ir.module.category">
        <field name="name">Academy</field>
        <field name="sequence">30</field>
    </record>

    <record id="privilege_x_academy" model="res.groups.privilege">
        <field name="name">Academy</field>
        <field name="sequence">30</field>
        <field name="category_id" ref="x_academy.module_category_x_academy"/>
    </record>

    <record id="group_x_academy_user" model="res.groups">
        <field name="name">Academy User</field>
        <field name="privilege_id" ref="x_academy.privilege_x_academy"/>
    </record>

    <record id="group_x_academy_manager" model="res.groups">
        <field name="name">Academy Manager</field>
        <field name="privilege_id" ref="x_academy.privilege_x_academy"/>
        <field name="implied_ids" eval="[(4, ref('x_academy.group_x_academy_user'))]"/>
    </record>
</odoo>
```

---

# 10. Access rights

File:

```text
custom_addons/x_academy/security/ir.model.access.csv
```

Code:

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_x_academy_course_user,x.academy.course.user,model_x_academy_course,x_academy.group_x_academy_user,1,1,1,0
access_x_academy_course_manager,x.academy.course.manager,model_x_academy_course,x_academy.group_x_academy_manager,1,1,1,1
access_x_academy_session_user,x.academy.session.user,model_x_academy_session,x_academy.group_x_academy_user,1,1,1,0
access_x_academy_session_manager,x.academy.session.manager,model_x_academy_session,x_academy.group_x_academy_manager,1,1,1,1
access_x_academy_enrollment_user,x.academy.enrollment.user,model_x_academy_enrollment,x_academy.group_x_academy_user,1,1,1,0
access_x_academy_enrollment_manager,x.academy.enrollment.manager,model_x_academy_enrollment,x_academy.group_x_academy_manager,1,1,1,1
```

Odoo access rights cấp quyền theo model và theo group. Nếu user không có access right phù hợp cho operation trên model thì user không có quyền thực hiện operation đó; access rights cũng có tính cộng dồn theo các group mà user thuộc về. ([Odoo][5])

---

# 11. Course views

File:

```text
custom_addons/x_academy/views/course_views.xml
```

Code:

```xml
<odoo>
    <record id="x_academy_course_view_list" model="ir.ui.view">
        <field name="name">x.academy.course.view.list</field>
        <field name="model">x.academy.course</field>
        <field name="arch" type="xml">
            <list string="Courses">
                <field name="sequence" widget="handle"/>
                <field name="name"/>
                <field name="code"/>
                <field name="start_date"/>
                <field name="end_date"/>
                <field name="seats"/>
                <field name="confirmed_enrollment_count"/>
                <field name="state"/>
            </list>
        </field>
    </record>

    <record id="x_academy_course_view_form" model="ir.ui.view">
        <field name="name">x.academy.course.view.form</field>
        <field name="model">x.academy.course</field>
        <field name="arch" type="xml">
            <form string="Course">
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

                    <field name="state"
                           widget="statusbar"
                           statusbar_visible="draft,confirmed,done"/>
                </header>

                <sheet>
                    <div class="oe_button_box" name="button_box">
                        <button name="action_view_sessions"
                                type="object"
                                class="oe_stat_button"
                                icon="fa-calendar">
                            <field name="session_count"
                                   widget="statinfo"
                                   string="Sessions"/>
                        </button>

                        <button name="action_view_enrollments"
                                type="object"
                                class="oe_stat_button"
                                icon="fa-users">
                            <field name="confirmed_enrollment_count"
                                   widget="statinfo"
                                   string="Enrollments"/>
                        </button>
                    </div>

                    <group>
                        <group>
                            <field name="name"/>
                            <field name="code"/>
                            <field name="active"/>
                            <field name="seats"/>
                            <field name="confirmed_enrollment_count" readonly="1"/>
                        </group>
                        <group>
                            <field name="start_date"/>
                            <field name="end_date"/>
                            <field name="duration_days" readonly="1"/>
                        </group>
                    </group>

                    <notebook>
                        <page string="Description">
                            <field name="description"/>
                        </page>

                        <page string="Sessions">
                            <field name="session_ids" context="{'default_course_id': id}">
                                <list editable="bottom">
                                    <field name="name"/>
                                    <field name="date_start"/>
                                    <field name="date_end"/>
                                    <field name="instructor_id"/>
                                    <field name="attendee_count"/>
                                    <field name="state"/>
                                </list>
                            </field>
                        </page>

                        <page string="Enrollments">
                            <field name="enrollment_ids" context="{'default_course_id': id}">
                                <list editable="bottom">
                                    <field name="student_id"/>
                                    <field name="session_id"/>
                                    <field name="enrollment_date"/>
                                    <field name="state"/>
                                </list>
                            </field>
                        </page>
                    </notebook>
                </sheet>
            </form>
        </field>
    </record>

    <record id="x_academy_course_view_search" model="ir.ui.view">
        <field name="name">x.academy.course.view.search</field>
        <field name="model">x.academy.course</field>
        <field name="arch" type="xml">
            <search string="Search Courses">
                <field name="name"/>
                <field name="code"/>
                <field name="state"/>

                <filter name="filter_confirmed"
                        string="Confirmed"
                        domain="[('state', '=', 'confirmed')]"/>

                <filter name="filter_done"
                        string="Done"
                        domain="[('state', '=', 'done')]"/>

                <separator/>

                <filter name="group_by_state"
                        string="Group by Status"
                        context="{'group_by': 'state'}"/>
            </search>
        </field>
    </record>

    <record id="x_academy_course_action" model="ir.actions.act_window">
        <field name="name">Courses</field>
        <field name="res_model">x.academy.course</field>
        <field name="view_mode">list,form</field>
        <field name="search_view_id" ref="x_academy_course_view_search"/>
    </record>
</odoo>
```

Trong Odoo, views thường được định nghĩa bằng XML cùng với action và menu; Odoo 19 tutorial dùng root `<list>` cho list view. ([Odoo][6])

---

# 12. Session views

File:

```text
custom_addons/x_academy/views/session_views.xml
```

Code:

```xml
<odoo>
    <record id="x_academy_session_view_list" model="ir.ui.view">
        <field name="name">x.academy.session.view.list</field>
        <field name="model">x.academy.session</field>
        <field name="arch" type="xml">
            <list string="Sessions">
                <field name="name"/>
                <field name="course_id"/>
                <field name="date_start"/>
                <field name="date_end"/>
                <field name="instructor_id"/>
                <field name="attendee_count"/>
                <field name="state"/>
            </list>
        </field>
    </record>

    <record id="x_academy_session_view_form" model="ir.ui.view">
        <field name="name">x.academy.session.view.form</field>
        <field name="model">x.academy.session</field>
        <field name="arch" type="xml">
            <form string="Session">
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

                    <field name="state"
                           widget="statusbar"
                           statusbar_visible="draft,confirmed,done"/>
                </header>

                <sheet>
                    <group>
                        <group>
                            <field name="name"/>
                            <field name="course_id"/>
                            <field name="instructor_id"/>
                        </group>
                        <group>
                            <field name="date_start"/>
                            <field name="date_end"/>
                            <field name="attendee_count" readonly="1"/>
                        </group>
                    </group>

                    <notebook>
                        <page string="Attendees">
                            <field name="attendee_ids" widget="many2many_tags"/>
                        </page>
                    </notebook>
                </sheet>
            </form>
        </field>
    </record>

    <record id="x_academy_session_view_calendar" model="ir.ui.view">
        <field name="name">x.academy.session.view.calendar</field>
        <field name="model">x.academy.session</field>
        <field name="arch" type="xml">
            <calendar string="Sessions"
                      date_start="date_start"
                      date_stop="date_end"
                      color="course_id">
                <field name="name"/>
                <field name="course_id"/>
                <field name="instructor_id"/>
            </calendar>
        </field>
    </record>

    <record id="x_academy_session_view_search" model="ir.ui.view">
        <field name="name">x.academy.session.view.search</field>
        <field name="model">x.academy.session</field>
        <field name="arch" type="xml">
            <search string="Search Sessions">
                <field name="name"/>
                <field name="course_id"/>
                <field name="instructor_id"/>
                <field name="state"/>

                <filter name="filter_confirmed"
                        string="Confirmed"
                        domain="[('state', '=', 'confirmed')]"/>

                <separator/>

                <filter name="group_by_course"
                        string="Group by Course"
                        context="{'group_by': 'course_id'}"/>

                <filter name="group_by_instructor"
                        string="Group by Instructor"
                        context="{'group_by': 'instructor_id'}"/>
            </search>
        </field>
    </record>

    <record id="x_academy_session_action" model="ir.actions.act_window">
        <field name="name">Sessions</field>
        <field name="res_model">x.academy.session</field>
        <field name="view_mode">list,form,calendar</field>
        <field name="search_view_id" ref="x_academy_session_view_search"/>
    </record>
</odoo>
```

---

# 13. Enrollment views

File:

```text
custom_addons/x_academy/views/enrollment_views.xml
```

Code:

```xml
<odoo>
    <record id="x_academy_enrollment_view_list" model="ir.ui.view">
        <field name="name">x.academy.enrollment.view.list</field>
        <field name="model">x.academy.enrollment</field>
        <field name="arch" type="xml">
            <list string="Enrollments">
                <field name="name"/>
                <field name="course_id"/>
                <field name="student_id"/>
                <field name="session_id"/>
                <field name="enrollment_date"/>
                <field name="state"/>
            </list>
        </field>
    </record>

    <record id="x_academy_enrollment_view_form" model="ir.ui.view">
        <field name="name">x.academy.enrollment.view.form</field>
        <field name="model">x.academy.enrollment</field>
        <field name="arch" type="xml">
            <form string="Enrollment">
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

                    <field name="state"
                           widget="statusbar"
                           statusbar_visible="draft,confirmed,done"/>
                </header>

                <sheet>
                    <group>
                        <group>
                            <field name="name" readonly="1"/>
                            <field name="course_id"/>
                            <field name="student_id"/>
                        </group>
                        <group>
                            <field name="session_id"
                                   domain="[('course_id', '=', course_id)]"/>
                            <field name="enrollment_date"/>
                        </group>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

    <record id="x_academy_enrollment_view_search" model="ir.ui.view">
        <field name="name">x.academy.enrollment.view.search</field>
        <field name="model">x.academy.enrollment</field>
        <field name="arch" type="xml">
            <search string="Search Enrollments">
                <field name="name"/>
                <field name="course_id"/>
                <field name="student_id"/>
                <field name="session_id"/>
                <field name="state"/>

                <filter name="filter_confirmed"
                        string="Confirmed"
                        domain="[('state', '=', 'confirmed')]"/>

                <filter name="filter_cancelled"
                        string="Cancelled"
                        domain="[('state', '=', 'cancelled')]"/>

                <separator/>

                <filter name="group_by_course"
                        string="Group by Course"
                        context="{'group_by': 'course_id'}"/>

                <filter name="group_by_student"
                        string="Group by Student"
                        context="{'group_by': 'student_id'}"/>

                <filter name="group_by_state"
                        string="Group by Status"
                        context="{'group_by': 'state'}"/>
            </search>
        </field>
    </record>

    <record id="x_academy_enrollment_action" model="ir.actions.act_window">
        <field name="name">Enrollments</field>
        <field name="res_model">x.academy.enrollment</field>
        <field name="view_mode">list,form</field>
        <field name="search_view_id" ref="x_academy_enrollment_view_search"/>
    </record>
</odoo>
```

---

# 14. Partner view inheritance

File:

```text
custom_addons/x_academy/views/res_partner_views.xml
```

Code:

```xml
<odoo>
    <record id="x_academy_res_partner_view_form_inherit" model="ir.ui.view">
        <field name="name">res.partner.view.form.inherit.x.academy</field>
        <field name="model">res.partner</field>
        <field name="inherit_id" ref="base.view_partner_form"/>
        <field name="arch" type="xml">
            <xpath expr="//sheet//notebook" position="inside">
                <page string="Academy">
                    <group>
                        <group string="Academy Roles">
                            <field name="is_academy_student"/>
                            <field name="is_academy_instructor"/>
                        </group>
                    </group>

                    <notebook>
                        <page string="Enrollments" invisible="not is_academy_student">
                            <field name="academy_enrollment_ids">
                                <list>
                                    <field name="course_id"/>
                                    <field name="session_id"/>
                                    <field name="enrollment_date"/>
                                    <field name="state"/>
                                </list>
                            </field>
                        </page>

                        <page string="Instructor Sessions" invisible="not is_academy_instructor">
                            <field name="academy_instructor_session_ids">
                                <list>
                                    <field name="name"/>
                                    <field name="course_id"/>
                                    <field name="date_start"/>
                                    <field name="date_end"/>
                                    <field name="state"/>
                                </list>
                            </field>
                        </page>
                    </notebook>
                </page>
            </xpath>
        </field>
    </record>
</odoo>
```

Sau khi cài module, vào **Contacts**, mở một contact bất kỳ, bạn sẽ thấy tab **Academy**. Tại đó có thể tick:

```text
Academy Student
Academy Instructor
```

---

# 15. Menus

File:

```text
custom_addons/x_academy/views/menus.xml
```

Code:

```xml
<odoo>
    <menuitem id="x_academy_root_menu"
              name="Academy"
              sequence="10"/>

    <menuitem id="x_academy_course_menu"
              name="Courses"
              parent="x_academy_root_menu"
              action="x_academy_course_action"
              sequence="10"/>

    <menuitem id="x_academy_session_menu"
              name="Sessions"
              parent="x_academy_root_menu"
              action="x_academy_session_action"
              sequence="20"/>

    <menuitem id="x_academy_enrollment_menu"
              name="Enrollments"
              parent="x_academy_root_menu"
              action="x_academy_enrollment_action"
              sequence="30"/>
</odoo>
```

---

# 16. Update module

Chạy:

```bash
./odoo-bin \
  -d odoo19_dev \
  --addons-path=addons,custom_addons \
  -u x_academy \
  --dev=xml
```

Sau đó vào:

```text
Settings → Users & Companies → Users
```

Gán user của bạn vào group:

```text
Academy / Academy Manager
```

Nếu chưa thấy menu **Academy**, hãy:

```text
Apps → Update Apps List
```

rồi upgrade module `X Academy`.

---

# 17. Test nghiệp vụ thủ công

## Bước 1 — Tạo Student và Instructor

Vào **Contacts**:

Tạo hoặc mở contact:

```text
Nguyen Van Student
```

Tick:

```text
Academy Student = True
```

Tạo hoặc mở contact:

```text
Tran Thi Instructor
```

Tick:

```text
Academy Instructor = True
```

## Bước 2 — Tạo Course

Vào:

```text
Academy → Courses → New
```

Nhập:

```text
Course Name: Odoo Developer Foundation
Course Code: ODOO-DEV-001
Seats: 20
Start Date: 2026-07-01
End Date: 2026-07-15
```

Bấm:

```text
Confirm
```

## Bước 3 — Tạo Session

Trong Course, tab **Sessions**, thêm:

```text
Name: Session 1 - ORM & Models
Date Start: 2026-07-01 09:00
Date End: 2026-07-01 12:00
Instructor: Tran Thi Instructor
```

Hoặc vào:

```text
Academy → Sessions → New
```

## Bước 4 — Tạo Enrollment

Vào:

```text
Academy → Enrollments → New
```

Nhập:

```text
Course: Odoo Developer Foundation
Student: Nguyen Van Student
Preferred Session: Session 1 - ORM & Models
```

Bấm:

```text
Confirm
```

Nếu course chưa Confirm hoặc đã hết seats, hệ thống sẽ raise `ValidationError`.

---

# 18. Các lỗi thường gặp

## Lỗi 1 — External ID not found: `model_x_academy_session`

Nguyên nhân thường là file model chưa được import.

Kiểm tra:

```python
# models/__init__.py

from . import course
from . import session
from . import enrollment
from . import res_partner
```

Sau đó restart Odoo và update module.

---

## Lỗi 2 — Không thấy menu Academy

Kiểm tra:

```python
"data": [
    ...
    "views/menus.xml",
]
```

Sau đó:

```text
Apps → Update Apps List → Upgrade module
```

---

## Lỗi 3 — Access Error

Kiểm tra:

1. User đã được gán group `Academy User` hoặc `Academy Manager`.
2. File `security/security.xml` được load trước `ir.model.access.csv`.
3. `ir.model.access.csv` không bị sai dấu phẩy hoặc sai external id.

---

## Lỗi 4 — Field không tồn tại trong view

Ví dụ lỗi:

```text
Field "academy_enrollment_ids" does not exist in model "res.partner"
```

Nguyên nhân:

* quên import `res_partner.py`
* chưa restart Odoo
* chưa update module

---

# 19. Điều bạn vừa học được ở Level 3

Sau bài này, bạn đã nắm được phần rất quan trọng trong Odoo module development:

| Chủ đề            | Bạn đã dùng                                                     |
| ----------------- | --------------------------------------------------------------- |
| Custom model      | `x.academy.course`, `x.academy.session`, `x.academy.enrollment` |
| Model inheritance | `_inherit = "res.partner"`                                      |
| Many2one          | Session → Course, Enrollment → Course, Enrollment → Student     |
| One2many          | Course → Sessions, Course → Enrollments                         |
| Many2many         | Session → Attendees                                             |
| Domain            | Chỉ chọn Partner là Student/Instructor                          |
| Search view       | Filter, group by                                                |
| Smart button      | Course → Sessions, Course → Enrollments                         |
| ACL               | User và Manager rights                                          |
| Workflow button   | Draft, Confirmed, Done, Cancelled                               |
| Constraint        | Không cho enrollment trùng, session phải thuộc đúng course      |

Bài tiếp theo nên là **Level 4 — Business Logic chuyên sâu**: thêm sequence tự động cho Course/Enrollment, override `create/write/unlink`, computed fields nâng cao, onchange nâng cao, rule không cho sửa/xóa khi record đã Confirmed/Done, và kiểm soát capacity theo course/session.

[1]: https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/03_basicmodel.html?utm_source=chatgpt.com "Chapter 3: Models And Basic Fields"
[2]: https://www.odoo.com/documentation/19.0/applications/studio/fields.html?utm_source=chatgpt.com "Fields and widgets — Odoo 19.0 documentation"
[3]: https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/01_architecture.html?utm_source=chatgpt.com "Chapter 1: Architecture Overview"
[4]: https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/12_inheritance.html?utm_source=chatgpt.com "Chapter 12: Inheritance — Odoo 19.0 documentation"
[5]: https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html?utm_source=chatgpt.com "Security in Odoo — Odoo 19.0 documentation"
[6]: https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/06_basicviews.html?utm_source=chatgpt.com "Chapter 6: Basic Views — Odoo 19.0 documentation"
