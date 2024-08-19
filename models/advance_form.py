from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError


class LogicSalaryAdvance(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _name = 'logic.salary.advance'
    _rec_name = 'name'
    _description = 'Salary Advance'

    name = fields.Char(string='Name', readonly=True, default=lambda self: 'Adv/')
    employee_id = fields.Many2one('hr.employee', string='Employee', default=lambda self: self.env.user.employee_id,
                                  readonly=True)
    date = fields.Date(string='Date', required=True, default=lambda self: fields.Date.today(), help="Submit date")
    branch = fields.Many2one('logic.base.branches', string='Branch', default=lambda self: self.env.user.employee_id.branch_id)
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
    department = fields.Many2one('hr.department', string='Department', related='employee_id.department_id')
    no_of_months = fields.Integer(string='Loan for how many months')

    state = fields.Selection([('draft', 'Draft'),
                              ('submit', 'Submitted'),
                              ('hr_approve', 'HR Approval'),
                              ('approve', 'Approved'),
                              ('reject', 'Rejected'),
                              ('paid', 'Paid')], string='Status', default='draft', track_visibility='onchange')
    director_approval = fields.Many2one('hr.employee', string='Director approval',
                                        domain=[('sample_custom', '=', 'True')])
    advance_emp_type = fields.Selection([('loan', 'Loan'), ('advance', 'Advance')], string='Type', default='advance',
                                        readonly=True)
    month_type = fields.Selection([('current', 'Current Month')], string='From which month',
                                  default='current', readonly=True)

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
        ss = self.env['logic.salary.advance'].search([])
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

        users = ss.env.ref('logic_salary_advance.hr_advance').users
        for j in users:
            activity_type = self.env.ref('logic_salary_advance.mail_activity_advance_alert')
            self.activity_schedule('logic_salary_advance.mail_activity_advance_alert', user_id=j.id,
                                   note='Received a new Advance request')

    def action_change_branches_from_employees(self):
        rec = self.env['logic.salary.advance'].sudo().search([])
        for i in rec:
            i.sudo().update({
                'branch': i.employee_id.branch_id.id
            })


    def activity_schedule_advance_request(self):
        print('hhhi')
        ss = self.env['logic.salary.advance'].search([])
        for i in ss:
            if i.state == 'hr_approve':
                users = ss.env.ref('logic_salary_advance.hr_advance').users
                for j in users:
                    activity_type = i.env.ref('logic_salary_advance.mail_activity_advance_alert')
                    i.activity_schedule('logic_salary_advance.mail_activity_advance_alert', user_id=j.id,
                                        note='Received a new Advance request')

    def activity_schedule_advance_request_accounts(self):
        print('hhhi')
        ss = self.env['logic.salary.advance'].search([])
        for i in ss:
            if i.state == 'approve':
                users = ss.env.ref('logic_salary_advance.accounts_advance').users
                for j in users:
                    activity_type = i.env.ref('logic_salary_advance.mail_activity_advance_alert')
                    i.activity_schedule('logic_salary_advance.mail_activity_advance_alert', user_id=j.id,
                                        note='Received a new Advance request')

    def hr_approval(self):
        ss = self.env['logic.salary.advance'].search([])
        print('account')

        activity_id = self.env['mail.activity'].search([('res_id', '=', self.id), ('user_id', '=', self.env.user.id), (
            'activity_type_id', '=', self.env.ref('logic_salary_advance.mail_activity_advance_alert').id)])
        activity_id.action_feedback(feedback='HR Approved Advance Request')
        other_activity_ids = self.env['mail.activity'].search([('res_id', '=', self.id), (
            'activity_type_id', '=', self.env.ref('logic_salary_advance.mail_activity_advance_alert').id)])
        other_activity_ids.unlink()
        users = ss.env.ref('logic_salary_advance.accounts_advance').users
        for j in users:
            activity_type = self.env.ref('logic_salary_advance.mail_activity_advance_alert')
            self.activity_schedule('logic_salary_advance.mail_activity_advance_alert', user_id=j.id,
                                   note='Received a new Advance request')
        self.message_post(body="HR Approved Advance Request")
        print(self.department.id)
        if self.exceed_condition == True:
            if not self.director_approval:
                raise models.ValidationError("Please select the Director who approved the request!")
            else:

                payment = self.env['employee.advance.payment'].create([{
                    'employee_id': self.employee_id.id,
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
                'employee_id': self.employee_id.id,
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
        self.message_post(body="Rejected")

        activity_id = self.env['mail.activity'].search([('res_id', '=', self.id), ('user_id', '=', self.env.user.id), (
            'activity_type_id', '=', self.env.ref('logic_salary_advance.mail_activity_advance_alert').id)])
        activity_id.action_feedback(feedback='Rejected')
        other_activity_ids = self.env['mail.activity'].search([('res_id', '=', self.id), (
            'activity_type_id', '=', self.env.ref('logic_salary_advance.mail_activity_advance_alert').id)])
        other_activity_ids.unlink()
        self.state = 'reject'
