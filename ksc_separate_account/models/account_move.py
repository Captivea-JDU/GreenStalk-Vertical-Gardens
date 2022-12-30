# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountInvoiceLine(models.Model):
    _inherit = "account.move.line"

    def _get_computed_account(self):
        res = super(AccountInvoiceLine, self)._get_computed_account()
        if self._context.get('team_id'):
            sales_team = self.env['crm.team'].browse(
                self._context.get('team_id') or self._context['team_id'])
            if sales_team.name == 'GreenStalk Gardens store':
                bigcomm_sale_acc = self.env['account.account'].search([('code', '=', '4040')])
                return bigcomm_sale_acc
            elif sales_team.name == 'Amazon':
                amazon_sale_acc = self.env['account.account'].search([('code', '=', '4030')])
                return amazon_sale_acc
        return res
