{
    'name': "Salary Advance",
    'version': "14.0.1.0",
    'sequence': "0",
    'depends': ['mail', 'base'],
    'data': [
        'security/user_groups.xml',
        'security/ir.model.access.csv',
        'security/rules.xml',
        'views/advance_view.xml',
        'views/advance_payment.xml',
        'views/advance_return.xml'

    ],
    'demo': [],
    'summary': "logic_salary_advance",
    'description': "this_is_my_app",
    'installable': True,
    'auto_install': False,
    'license': "LGPL-3",
    'application': True
}
