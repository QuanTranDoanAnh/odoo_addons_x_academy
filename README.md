# My exercise in developing Odoo addon for Odoo CE 19.0

Dưới đây là lộ trình học–làm module Odoo 19 theo hướng **từ đơn giản nhất đến module hoàn chỉnh**, bám theo tài liệu chính thức Odoo 19. Odoo xác định module/addon là đơn vị đóng gói cả server và client extension; một module có thể chứa business objects bằng Python, object views, data files XML/CSV, web controllers và static assets. ([Odoo][1]) Odoo 19 cũng khuyến nghị học theo tutorial **Server framework 101**, đi tuần tự từ new app, models, security, views, relations, computed fields, actions, constraints, inheritance, module interaction và QWeb. ([Odoo][2])

## 1. Tư duy kiến trúc trước khi code

Trong Odoo Server Framework, bạn cần nắm 5 lớp chính:

| Lớp                                                 | Vai trò                                                                                                                                           |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `__manifest__.py`                                   | Khai báo module, dependency, data files, demo files, assets. Manifest là file Python dictionary dùng để Odoo nhận diện module. ([Odoo][3])        |
| `models/*.py`                                       | Định nghĩa business object. Odoo ORM giúp tránh viết SQL thủ công và map Python class/fields xuống database. ([Odoo][4])                          |
| `views/*.xml`                                       | Định nghĩa giao diện: list, form, search, kanban, menu, action. Odoo 19 dùng root `<list>` cho list view. ([Odoo][5])                             |
| `security/*.csv`, `security/*.xml`                  | Phân quyền model access, groups, record rules. Odoo có 2 cơ chế data-driven chính để hạn chế access, gắn với user groups. ([Odoo][6])             |
| `controllers`, `reports`, `tests`, `data`, `wizard` | API/web route, PDF/QWeb report, unit test, seed data, transient wizard. Reports dùng HTML/QWeb và PDF được render bằng `wkhtmltopdf`. ([Odoo][7]) |

Ta sẽ học bằng một module mẫu tên **`x_academy`**. Đây là module quản lý khóa học nội bộ, đủ đơn giản để học nhưng có thể mở rộng thành module toàn diện: Course, Session, Enrollment, Instructor, Student, workflow, wizard, report, security, chatter, cron, API, tests.

---

## 2. Lộ trình từ đơn giản đến toàn diện

### Level 1 — Module tối thiểu: Odoo nhận diện được addon

Link: [Level 1](README-Level-1.md)

Mục tiêu: tạo một module cài được, có model đơn giản, list/form view, menu.

Cấu trúc:

```text
custom_addons/
└── x_academy/
    ├── __init__.py
    ├── __manifest__.py
    ├── models/
    │   ├── __init__.py
    │   └── course.py
    ├── security/
    │   └── ir.model.access.csv
    └── views/
        └── course_views.xml
```

### Level 2 — Module nghiệp vụ cơ bản

Link: [Level 2](README-Level-2.md)

Thêm fields: `Char`, `Text`, `Date`, `Integer`, `Selection`, `Boolean`, `Monetary`.
Thêm workflow button: Draft → Confirmed → Done → Cancelled.

### Level 3 — Quan hệ dữ liệu

Link: [Level 3](README-Level-3.md)

Thêm:

```text
Course 1 - n Session
Course n - n Student
Session n - 1 Instructor
Enrollment nối Student với Course
```

Bạn học `Many2one`, `One2many`, `Many2many`, domain, context.

### Level 4 — Logic nghiệp vụ

Link: [Level 4](README-Level-4.md)

Thêm:

* computed fields
* onchange
* Python constraints
* SQL constraints
* override `create`, `write`, `unlink`
* sequence tự động
* state transition validation

### Level 5 — Security chuẩn doanh nghiệp

Thêm:

* groups: Academy User, Academy Manager
* ACL theo model
* record rules theo owner/company
* hạn chế xóa record đã confirmed/done

Access rights trong Odoo là additive: user có quyền tổng hợp từ tất cả group mà họ thuộc về. ([Odoo][6])

### Level 6 — Wizard, report, email/chatter

Thêm:

* `TransientModel` wizard đăng ký học viên hàng loạt
* QWeb PDF report danh sách học viên
* `mail.thread`, `mail.activity.mixin`
* email template
* scheduled action nhắc lịch học

Odoo ORM có 3 loại model quan trọng: `Model` cho dữ liệu lưu database bình thường, `TransientModel` cho dữ liệu tạm như wizard, và `AbstractModel` cho class trừu tượng/tái sử dụng. ([Odoo][4])

### Level 7 — Tích hợp với module Odoo chuẩn

Thêm:

* inherit `res.partner` để đánh dấu Student/Instructor
* inherit `sale.order` nếu bán khóa học
* tạo product course
* tạo invoice hoặc subscription nếu cần

### Level 8 — Controller/API, import/export, tests, performance

Thêm:

* JSON controller cho app bên ngoài
* import data XML/CSV
* unit tests
* performance optimization
* packaging theo chuẩn OCA-like

Odoo hỗ trợ Python unit tests, JS unit tests và tour/integration tests; Python tests đặt trong thư mục `tests` và import từ `tests/__init__.py`. ([Odoo][8])

---

## 3. Module hoàn chỉnh nên có cấu trúc như thế nào?

Khi module trưởng thành, cấu trúc nên như sau:

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
├── wizard/
│   ├── __init__.py
│   └── enrollment_wizard.py
├── security/
│   ├── security.xml
│   ├── ir.model.access.csv
│   └── record_rules.xml
├── views/
│   ├── course_views.xml
│   ├── session_views.xml
│   ├── enrollment_views.xml
│   ├── res_partner_views.xml
│   └── menus.xml
├── reports/
│   ├── course_report.xml
│   └── course_report_templates.xml
├── data/
│   ├── sequence.xml
│   ├── mail_template.xml
│   └── cron.xml
├── controllers/
│   ├── __init__.py
│   └── main.py
├── tests/
│   ├── __init__.py
│   └── test_course.py
├── static/
│   └── description/
│       └── icon.png
└── demo/
    └── demo_data.xml
```

Đây là cấu trúc đủ tốt cho module production nhỏ đến vừa.

---

## 4. Capstone: module toàn diện cần đạt những chức năng nào?

Với module `x_academy`, bản toàn diện nên có:

| Nhóm chức năng | Nội dung                                             |
| -------------- | ---------------------------------------------------- |
| Master data    | Course, Session, Instructor, Student                 |
| Transaction    | Enrollment, Attendance                               |
| Workflow       | Draft → Confirmed → In Progress → Done → Cancelled   |
| Security       | User/Manager/Admin, record rule theo company         |
| UX             | List, Form, Search, Kanban, Calendar                 |
| Automation     | Sequence, scheduled reminder                         |
| Wizard         | Bulk enroll students                                 |
| Report         | Course roster PDF, attendance sheet                  |
| Integration    | JSON route cho external app                          |
| Extension      | Inherit `res.partner`, optional inherit `sale.order` |
| Quality        | Unit tests, demo data, performance check             |
| Packaging      | Manifest chuẩn, license, icon, README, versioning    |

---

## 5. Cách học hiệu quả nhất cho bạn

Với mục tiêu của bạn là xây dựng Odoo service business và vertical packs, tôi khuyên học theo thứ tự này:

1. **Nắm module anatomy**: manifest, init, models, views, security.
2. **Làm 5 module nhỏ**: Task, Course, Asset, Approval, Credit Limit.
3. **Sau đó mới học inherit module chuẩn**: `sale`, `purchase`, `stock`, `account`.
4. **Tiếp theo học Odoo business logic thật**: SO → DO → Invoice, PO → Receipt → Bill, Inventory Valuation.
5. **Cuối cùng mới xây vertical pack**: Wholesale, Vietnam Compliance, Education, Distribution.


---

[1]: https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/01_architecture.html "Chapter 1: Architecture Overview — Odoo 19.0 documentation"
[2]: https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101.html "Server framework 101 — Odoo 19.0 documentation"
[3]: https://www.odoo.com/documentation/19.0/developer/reference/backend/module.html "Module Manifests — Odoo 19.0 documentation"
[4]: https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html "ORM API — Odoo 19.0 documentation"
[5]: https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/06_basicviews.html?utm_source=chatgpt.com "Chapter 6: Basic Views — Odoo 19.0 documentation"
[6]: https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html "Security in Odoo — Odoo 19.0 documentation"
[7]: https://www.odoo.com/documentation/19.0/developer/reference/backend/reports.html?utm_source=chatgpt.com "QWeb Reports — Odoo 19.0 documentation"
[8]: https://www.odoo.com/documentation/19.0/developer/reference/backend/testing.html?utm_source=chatgpt.com "Testing Odoo — Odoo 19.0 documentation"
