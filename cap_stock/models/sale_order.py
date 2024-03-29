# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def create(self, vals):
        result = super(SaleOrder, self).create(vals)
        if result.team_id and result.team_id.name == 'GreenStalk Gardens store':
            if result.amount_total > 1000:
                large_order_tag = self.env['crm.tag'].search([('name', '=', 'Large Order')])
                if large_order_tag:
                    result.tag_ids |= large_order_tag

            if (result.partner_invoice_id.street != result.partner_shipping_id.street or result.partner_invoice_id.city != result.partner_shipping_id.city or result.partner_invoice_id.state_id != result.partner_shipping_id.state_id or result.partner_invoice_id.zip != result.partner_shipping_id.zip or result.partner_invoice_id.country_id != result.partner_shipping_id.country_id) and result.amount_total > 150:
                billing_address_mismatch_tag = self.env['crm.tag'].search([('name', '=', 'Billing Address Mismatch')])
                if billing_address_mismatch_tag:
                    result.tag_ids |= billing_address_mismatch_tag

            if result.customer_message:
                customer_added_note_tag = self.env['crm.tag'].search([('name', '=', 'Customer Added Note')])
                if customer_added_note_tag:
                    result.tag_ids |= customer_added_note_tag

            if result.partner_id:
                us_country = self.env['res.country'].search([('code', '=', 'US')])
                if result.partner_id.country_id and result.partner_id.country_id.id != us_country.id:
                    custom_tag = self.env['crm.tag'].search([('name', '=', 'Customs')])
                    if custom_tag:
                        result.tag_ids |= custom_tag
        else:
            result.tag_ids = [(5, 0, 0)]
        return result

    @api.onchange('order_line', 'partner_invoice_id', 'partner_shipping_id', 'customer_message', 'team_id', 'partner_id')
    def onchange_get_tags(self):
        for result in self:
            result.tag_ids = [(5, 0, 0)]
            if result.team_id and result.team_id.name == 'GreenStalk Gardens store':
                if result.amount_total > 1000:
                    large_order_tag = self.env['crm.tag'].search([('name', '=', 'Large Order')])
                    if large_order_tag:
                        result.tag_ids |= large_order_tag

                if (result.partner_invoice_id.street != result.partner_shipping_id.street or result.partner_invoice_id.city != result.partner_shipping_id.city or result.partner_invoice_id.state_id != result.partner_shipping_id.state_id or result.partner_invoice_id.zip != result.partner_shipping_id.zip or result.partner_invoice_id.country_id != result.partner_shipping_id.country_id) and result.amount_total > 150:
                    billing_address_mismatch_tag = self.env['crm.tag'].search([('name', '=', 'Billing Address Mismatch')])
                    if billing_address_mismatch_tag:
                        result.tag_ids |= billing_address_mismatch_tag

                if result.customer_message:
                    customer_added_note_tag = self.env['crm.tag'].search([('name', '=', 'Customer Added Note')])
                    if customer_added_note_tag:
                        result.tag_ids |= customer_added_note_tag

                if result.partner_id:
                    us_country = self.env['res.country'].search([('code', '=', 'US')])
                    if result.partner_id.country_id and result.partner_id.country_id.id != us_country.id:
                        custom_tag = self.env['crm.tag'].search([('name', '=', 'Customs')])
                        if custom_tag:
                            result.tag_ids |= custom_tag
