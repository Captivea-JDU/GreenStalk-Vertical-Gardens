# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def create(self, vals):
        result = super(StockPicking, self).create(vals)
        if result.origin:
            sale_order = self.env['sale.order'].search([('name', '=', result.origin)])
            if sale_order and sale_order.tag_ids:
                sale_tag = sale_order.tag_ids[0].name
                result.x_studio_inventory_tags = sale_tag
        return result
