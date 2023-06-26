from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError


class LogicSalaryAdvance(models.Model):
    _inherit = 'mail.thread'
    _name = 'logic.salary.advance'
    _rec_name = 'name'

    name = fields.Char(string='Name', readonly=True, default=lambda self: 'Adv/')
    employee_id = fields.Char(string='Employee', default=lambda self: self.env.user.name, readonly=True)
    date = fields.Date(string='Date', required=True, default=lambda self: fields.Date.today(), help="Submit date")
    branch = fields.Many2one('logic.branches', string='Branch')
    reason = fields.Text(string='Reason', help="Reason")
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    advance = fields.Float(string='Request advance amount', required=True)
    allowed_amount = fields.Monetary(string='Allowed amount', widget="monetary")
    payment_method = fields.Many2one('account.journal', string='Payment Method')
    exceed_condition = fields.Boolean(string='Exceed than Maximum',
                                      help="The Advance is greater than the maximum percentage in salary structure")
    department = fields.Many2one('hr.department', string='Department')
    no_of_months = fields.Integer(string='Loan for how many months')

    state = fields.Selection([('draft', 'Draft'),
                              ('submit', 'Submitted'),
                              ('hr_approve', 'HR Approval'),
                              ('approve', 'Approved'),
                              ('reject', 'Rejected'),
                              ('paid', 'Paid')], string='Status', default='draft', track_visibility='onchange')
    director_approval = fields.Many2one('hr.employee', string='Director approval',
                                        domain=[('sample_custom', '=', 'True')])
    advance_emp_type = fields.Selection([('loan', 'Loan'), ('advance', 'Advance')], string='Type')
    month_type = fields.Selection([('current', 'Current Month'), ('next', 'Next Month')], string='From which month')

    @api.onchange('advance')
    def advance_onchange(self):
        self.allowed_amount = self.advance

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].get('salary.advance.seq') or ' '
        res_id = super(LogicSalaryAdvance, self).create(vals)
        return res_id

    pending_amount = fields.Float(string='Pending amount', readonly=True)

    def submit(self):
        payment = self.env['employee.advance.payment'].search([])
        return_amt = self.env['advance.return'].search([])
        total = 0
        total_ret = 0
        for pay in payment:
            if self.employee_id == pay.employee_id and pay.state == 'paid':
                print(pay.advance, 'adv')
                print('yes')
                total += pay.advance
            # else:
            #     print('no')
            #     total = 0
        print(total, 'dd')
        for ret in return_amt:
            if self.employee_id == ret.employee_id.name and ret.state == 'return':
                print(ret.advance, 'rt')
                total_ret += ret.advance
            # else:
            #     total_ret = 0

        print(total_ret, 'kk')
        print(total - total_ret, 'total')
        self.pending_amount = total - total_ret
        if self.advance > 5000:
            self.exceed_condition = True
        self.state = 'hr_approve'
        print(self.id, 'id')

    def hr_approval(self):
        print(self.department.id)
        if self.exceed_condition == True:
            if not self.director_approval:
                raise models.ValidationError("Please select the Director who approved the request!")
            else:

                payment = self.env['employee.advance.payment'].create([{
                    'employee_id': self.employee_id,
                    'date': self.date,
                    'reason': self.reason,
                    'advance': self.allowed_amount,
                    'department': self.department.id,
                    'id_rec': self.id,
                    'adv_type': self.advance_emp_type,

                }])
                self.state = 'approve'
        else:

            payment = self.env['employee.advance.payment'].create([{
                'employee_id': self.employee_id,
                'date': self.date,
                'reason': self.reason,
                'advance': self.allowed_amount,
                'department': self.department.id,
                'id_rec': self.id,
                'adv_type': self.advance_emp_type,

            }])
            self.state = 'approve'

    make_visible = fields.Boolean(string="User", default=True, compute='get_hr')

    @api.depends('make_visible')
    def get_hr(self):
        print('kkkll')
        user_crnt = self.env.user.id

        res_user = self.env['res.users'].search([('id', '=', self.env.user.id)])
        if res_user.has_group('logic_salary_advance.hr_advance'):
            self.make_visible = False

        else:
            self.make_visible = True

    make_visible_employee = fields.Boolean(string="User", default=True, compute='get_employee')

    @api.depends('make_visible_employee')
    def get_employee(self):
        print('kkkll')
        user_crnt = self.env.user.id

        res_user = self.env['res.users'].search([('id', '=', self.env.user.id)])
        if res_user.has_group('logic_salary_advance.user_advance'):
            self.make_visible_employee = False

        else:
            self.make_visible_employee = True

    def rejected(self):
        self.state = 'reject'