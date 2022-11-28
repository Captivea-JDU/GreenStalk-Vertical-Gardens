from odoo import fields, models, _
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    channel_id = fields.Many2one('ecommerce.channel', string='Store', readonly=True)
