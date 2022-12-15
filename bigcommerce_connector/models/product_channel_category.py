import logging

from odoo import fields, models, _

_logger = logging.getLogger(__name__)


class MissingCategory(Exception):

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class ProductChannelCategory(models.Model):
    _name = "product.channel.category"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Product Store Category"
    _order = 'id_on_channel'
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = 'display_name'
    
    display_name = fields.Char(string='Display Name', compute='_compute_display_name')
    name = fields.Char(string='Name', required=True)
    platform = fields.Selection(related='channel_id.platform')
    id_on_channel = fields.Char(string='ID on Store', required=False,  copy=False)
    parent_id = fields.Many2one('product.channel.category', string='Parent Category')
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many('product.channel.category', 'parent_id', string='Child Categories')
    channel_id = fields.Many2one('ecommerce.channel', string='Store', required=True)

    internal_category_id = fields.Many2one('product.category', string='Internal Category')
    need_to_export = fields.Boolean(string='Need to Export', readonly=True, copy=False)
    need_to_export_display = fields.Boolean(compute='_compute_need_to_export_display')
    is_exported_to_store = fields.Boolean(string='Exported to Store', compute='_compute_is_exported_to_store')
    image = fields.Image(string='Image')
    image_url = fields.Char(string="Image URL", compute="_compute_image_url")
    description = fields.Text(string='Description')
    sort_order = fields.Integer(string='Sort Order')
    url = fields.Char(string='URL')
    page_title = fields.Char(string='Page Title')
    search_keywords = fields.Char(string='Search Keywords')
    meta_keywords = fields.Char(string='Meta Keywords')
    meta_description = fields.Text(string='Meta Description')
    is_visible = fields.Boolean(string='Is Visible', default=True)

    _sql_constraints = [
        ('uniq_name', 'unique (id_on_channel,channel_id)',
         'This category already exists !')
    ]