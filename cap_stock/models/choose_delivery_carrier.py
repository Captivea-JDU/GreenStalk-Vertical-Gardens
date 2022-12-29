# -*- coding: utf-8 -*-

import random
from odoo import fields, models, api, _


class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = 'choose.delivery.carrier'

    def button_confirm(self):
        res = super(ChooseDeliveryCarrier, self).button_confirm()
        if self.order_id and self.order_id.picking_ids:
            for picking in self.order_id.picking_ids:
                picking.carrier_id = self.carrier_id.id
                picking.carrier_tracking_ref = str(random.randint(100000000,999999999))
        return res
