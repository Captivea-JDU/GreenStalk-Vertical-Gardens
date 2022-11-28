import logging

from odoo import fields, models, _

_logger = logging.getLogger(__name__)


class OrderProcessRule(models.Model):
    _name = 'order.process.rule'
    _description = 'Order Process Rule'
    _order = 'sequence, id desc'

    sequence = fields.Integer(string='Sequence')
    name = fields.Char(string='Name', required=True)
    channel_id = fields.Many2one('ecommerce.channel', string='Store', ondelete='cascade')
    platform = fields.Selection(related='channel_id.platform')
    order_status_channel_ids = fields.Many2many('order.status.channel',
                                                'fulfillment_status_ref',
                                                'status_id',
                                                'rule_id',
                                                string='Order Status',
                                                domain="[('platform', '=', platform), ('type', '=', 'fulfillment')]",
                                                required=True)
    payment_status_channel_ids = fields.Many2many('order.status.channel',
                                                  'payment_status_ref', 'status_id', 'rule_id', string='Payment Status',
                                                  domain="[('platform', '=', platform), ('type', '=', 'payment')]",
                                                  required=False)
    has_payment_statuses = fields.Boolean(compute='_compute_has_payment_statuses')

    is_order_confirmed = fields.Boolean(string='Confirm Order')
    is_invoice_created = fields.Boolean(string='Create Invoice')
    is_payment_created = fields.Boolean(string='Create Payment')

    create_invoice_trigger = fields.Selection(selection=[
        ('order_confirmed', 'After confirming sales order'),
        ('fully_shipped', 'After fully shipped')
    ], default='order_confirmed')