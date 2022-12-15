from odoo import models, _
from odoo.tools.misc import formatLang

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    def format_value(self, value, currency=False):
        currency_id = currency or self.env.user.company_id.currency_id
        if self.env.context.get('no_format'):
            return currency_id.round(value)
        if currency_id.is_zero(value):
            # don't print -0.0 in reports
            value = abs(value)
        res = formatLang(self.env, value, currency_obj=currency_id)
        return res