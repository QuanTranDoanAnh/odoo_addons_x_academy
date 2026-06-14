
# Bài 1 — Viết module Odoo 19 đơn giản nhất nhưng chạy được

Giả định bạn đã có Odoo 19 Community từ GitHub và có thư mục:

```text
~/odoo19/
├── odoo/
├── addons/
└── custom_addons/
```

Tạo module:

```bash
cd ~/odoo19/custom_addons
mkdir -p x_academy/models x_academy/security x_academy/views
touch x_academy/__init__.py
touch x_academy/models/__init__.py
```

## 1. File `__manifest__.py`

Tạo:

```python
# custom_addons/x_academy/__manifest__.py

{
    "name": "X Academy",
    "summary": "Simple academy management module for Odoo 19 learning",
    "version": "19.0.1.0.0",
    "category": "Training",
    "author": "Your Company",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/course_views.xml",
    ],
    "application": True,
    "installable": True,
}
```

Ý nghĩa:

* `depends`: module phụ thuộc. Ở đây chỉ cần `base`.
* `data`: file luôn được load khi install/update module.
* `application=True`: module hiện như một app độc lập.
* `installable=True`: cho phép cài.

## 2. File import gốc

```python
# custom_addons/x_academy/__init__.py

from . import models
```

```python
# custom_addons/x_academy/models/__init__.py

from . import course
```

## 3. File model đầu tiên

```python
# custom_addons/x_academy/models/course.py

from odoo import fields, models


class XAcademyCourse(models.Model):
    _name = "x.academy.course"
    _description = "Academy Course"
    _order = "sequence, name"

    name = fields.Char(string="Course Name", required=True)
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

Điểm cần nhớ:

* `_name`: technical name của model.
* `_description`: mô tả model.
* `_order`: thứ tự mặc định.
* field trong Python class sẽ được ORM map xuống database.
* method `action_*` sẽ được gọi từ button trong form view.

## 4. File security ACL

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_x_academy_course_user,x.academy.course.user,model_x_academy_course,base.group_user,1,1,1,1
```

File path:

```text
custom_addons/x_academy/security/ir.model.access.csv
```

Nếu thiếu file này, user thường sẽ thấy lỗi không có quyền đọc/tạo/sửa record.

## 5. File view, action, menu

```xml
<!-- custom_addons/x_academy/views/course_views.xml -->

<odoo>
    <record id="x_academy_course_view_list" model="ir.ui.view">
        <field name="name">x.academy.course.view.list</field>
        <field name="model">x.academy.course</field>
        <field name="arch" type="xml">
            <list string="Courses">
                <field name="sequence" widget="handle"/>
                <field name="name"/>
                <field name="start_date"/>
                <field name="end_date"/>
                <field name="seats"/>
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
                    <group>
                        <group>
                            <field name="name"/>
                            <field name="active"/>
                            <field name="seats"/>
                        </group>
                        <group>
                            <field name="start_date"/>
                            <field name="end_date"/>
                        </group>
                    </group>

                    <notebook>
                        <page string="Description">
                            <field name="description"/>
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
                <field name="state"/>
                <filter name="filter_confirmed"
                        string="Confirmed"
                        domain="[('state', '=', 'confirmed')]"/>
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

    <menuitem id="x_academy_root_menu"
              name="Academy"
              sequence="10"/>

    <menuitem id="x_academy_course_menu"
              name="Courses"
              parent="x_academy_root_menu"
              action="x_academy_course_action"
              sequence="10"/>
</odoo>
```

Điểm quan trọng của Odoo 19: list view dùng root tag `<list>`, không nên dùng thói quen cũ `<tree>` khi viết mới. ([Odoo][5])

## 6. Chạy và cài module

Từ thư mục source Odoo:

```bash
./odoo-bin \
  -d odoo19_dev \
  --addons-path=addons,custom_addons \
  -u x_academy \
  --dev=xml
```

Sau đó vào Odoo:

```text
Apps → Update Apps List → tìm "X Academy" → Install
```

Nếu module đã install rồi, mỗi lần sửa Python/model/security/view, chạy:

```bash
./odoo-bin -d odoo19_dev --addons-path=addons,custom_addons -u x_academy --dev=xml
```

Nếu chỉ sửa XML view, `--dev=xml` giúp refresh nhanh hơn trong quá trình phát triển.

