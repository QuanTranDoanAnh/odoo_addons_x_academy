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