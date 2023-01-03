# -*- coding: utf-8 -*-

from odoo import fields, models


class OrderProcessRuleExtend(models.Model):
    _inherit = 'order.process.rule'

    def _create_posted_invoice_from_order(self, order):
        invoices = order.with_context({'order': order})._create_invoices()
        if self.create_invoice_trigger == 'fully_shipped':
            # Invoice Date should be the date done of the last of shipment
            date = order._compute_invoice_date() or fields.Date.today()
            invoices.update({'date': date})
        invoices.action_post()
        return invoices
