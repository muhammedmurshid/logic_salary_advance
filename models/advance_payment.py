from odoo import fields, models, api, _
import time


class EmployeeSalaryAdvancePayment(models.Model):
    _name = "employee.advance.payment"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, help="Employee")
    date = fields.Date(string='Date', required=True, help="Submit date")
    reason = fields.Text(string='Reason', help="Reason")
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    advance = fields.Float(string='Advance', required=True)
    payment_method = fields.Many2one('account.journal', string='Payment Method')
    exceed_condition = fields.Boolean(string='Exceed than Maximum',
                                      help="The Advance is greater than the maximum percentage in salary structure")
    department = fields.Many2one('hr.department', string='Department')
    state = fields.Selection([('draft', 'Draft'),
                              ('paid', 'Paid'),
                              ('cancel', 'Cancelled')], string='Status', default='draft', track_visibility='onchange')
    debit = fields.Many2one('account.account', string='Debit Account')
    credit = fields.Many2one('account.account', string='Credit Account')
    journal = fields.Many2one('account.journal', string='Journal')
    employee_contract_id = fields.Many2one('hr.contract', string='Contract')
    name = fields.Char(string='Name', readonly=True, default=lambda self: 'Adv/')
    id_rec = fields.Integer('ID')
    adv_type = fields.Selection([('advance', 'Advance'), ('loan', 'Loan')], string='Advance type')

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].get('salary.advance.seq') or ' '
        res_id = super(EmployeeSalaryAdvancePayment, self).create(vals)
        return res_id

    def cancel(self):
        self.state = 'cancel'

    def back_home(self):
        self.state = 'draft'

    def payment_paid(self):
        self.message_post(body="Paid")

        aa = self.env['logic.salary.advance'].search([])
        for i in aa:
            if i.id == self.id_rec:
                activity_id = self.env['mail.activity'].search(
                    [('res_id', '=', self.id), ('user_id', '=', self.env.user.id), (
                        'activity_type_id', '=', self.env.ref('logic_salary_advance.mail_activity_advance_alert').id)])
                activity_id.action_feedback(feedback='Paid')
                other_activity_ids = self.env['mail.activity'].search([('res_id', '=', self.id_rec), (
                    'activity_type_id', '=', self.env.ref('logic_salary_advance.mail_activity_advance_alert').id)])

                other_activity_ids.unlink()
                i.state = 'paid'
        move_obj = self.env['account.move']
        timenow = time.strftime('%Y-%m-%d')
        line_ids = []
        debit_sum = 0.0
        credit_sum = 0.0
        for request in self:
            amount = request.advance
            request_name = request.employee_id
            reference = request.name
            journal_id = request.journal.id
            move = {
                'narration': 'Salary Advance Of ' + request_name,
                'ref': reference,
                'journal_id': journal_id,
                'date': timenow,
            }

            debit_account_id = request.debit.id
            credit_account_id = request.credit.id

            if debit_account_id:
                debit_line = (0, 0, {
                    'name': request_name,
                    'account_id': debit_account_id,
                    'journal_id': journal_id,
                    'date': timenow,
                    'debit': amount > 0.0 and amount or 0.0,
                    'credit': amount < 0.0 and -amount or 0.0,
                })
                line_ids.append(debit_line)
                debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

            if credit_account_id:
                credit_line = (0, 0, {
                    'name': request_name,
                    'account_id': credit_account_id,
                    'journal_id': journal_id,
                    'date': timenow,
                    'debit': amount < 0.0 and -amount or 0.0,
                    'credit': amount > 0.0 and amount or 0.0,
                })
                line_ids.append(credit_line)
                credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
            move.update({'line_ids': line_ids})
            print("move.update({'line_ids': line_ids})", move.update({'invoice_line_ids': line_ids}))
            draft = move_obj.create(move)
            draft.post()
            self.state = 'paid'
            return True


class ResUsersK(models.Model):
    _inherit = 'hr.employee'

    sample_custom = fields.Boolean(string='Director')
