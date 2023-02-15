# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from collections import defaultdict



class StockPicking(models.Model):
    _inherit = 'stock.picking'

    state = fields.Selection(selection_add=[('to_approve', 'To Approve'),('assigned',)])
    is_approved = fields.Boolean(string='Approved')
    sale_note = fields.Text(related='sale_id.customer_message', string='Notes')
    tag_ids = fields.Many2many('crm.tag', related='sale_id.tag_ids', string='Tags')

    def action_set_approved(self):
        for record in self:
            record.is_approved = True

    @api.depends('move_type', 'immediate_transfer', 'move_lines.state', 'move_lines.picking_id', 'is_approved', 'tag_ids')
    def _compute_state(self):
        ''' State of a picking depends on the state of its related stock.move
        - Draft: only used for "planned pickings"
        - Waiting: if the picking is not ready to be sent so if
          - (a) no quantity could be reserved at all or if
          - (b) some quantities could be reserved and the shipping policy is "deliver all at once"
        - Waiting another move: if the picking is waiting for another move
        - Ready: if the picking is ready to be sent so if:
          - (a) all quantities are reserved or if
          - (b) some quantities could be reserved and the shipping policy is "as soon as possible"
        - Done: if the picking is done.
        - Cancelled: if the picking is cancelled
        '''
        picking_moves_state_map = defaultdict(dict)
        picking_move_lines = defaultdict(set)
        for move in self.env['stock.move'].search([('picking_id', 'in', self.ids)]):
            picking_id = move.picking_id
            move_state = move.state
            picking_moves_state_map[picking_id.id].update({
                'any_draft': picking_moves_state_map[picking_id.id].get('any_draft', False) or move_state == 'draft',
                'all_cancel': picking_moves_state_map[picking_id.id].get('all_cancel', True) and move_state == 'cancel',
                'all_cancel_done': picking_moves_state_map[picking_id.id].get('all_cancel_done', True) and move_state in ('cancel', 'done'),
                'all_done_are_scrapped': picking_moves_state_map[picking_id.id].get('all_done_are_scrapped', True) and (move.scrapped if move_state == 'done' else True),
                'any_cancel_and_not_scrapped': picking_moves_state_map[picking_id.id].get('any_cancel_and_not_scrapped', False) or (move_state == 'cancel' and not move.scrapped),
            })
            picking_move_lines[picking_id.id].add(move.id)
        for picking in self:
            picking_id = (picking.ids and picking.ids[0]) or picking.id
            if not picking_moves_state_map[picking_id]:
                picking.state = 'draft'
            elif picking_moves_state_map[picking_id]['any_draft']:
                picking.state = 'draft'
            elif picking_moves_state_map[picking_id]['all_cancel']:
                picking.state = 'cancel'
            elif picking_moves_state_map[picking_id]['all_cancel_done']:
                if picking_moves_state_map[picking_id]['all_done_are_scrapped'] and picking_moves_state_map[picking_id]['any_cancel_and_not_scrapped']:
                    picking.state = 'cancel'
                else:
                    picking.state = 'done'
            else:
                relevant_move_state = self.env['stock.move'].browse(picking_move_lines[picking_id])._get_relevant_state_among_moves()
                # Custom Code Start
                pick_tags = picking.tag_ids.mapped('name')
                if 'Large Order' in pick_tags or 'Billing Address Mismatch' in pick_tags or 'Customer Added Note' in pick_tags or 'Customs' in pick_tags:
                    if relevant_move_state not in ('draft', 'cancel', 'done') and not picking.is_approved:
                        picking.state = 'to_approve'
                    elif picking.immediate_transfer and relevant_move_state not in ('draft', 'cancel', 'done') and picking.is_approved:
                        picking.state = 'assigned'
                    elif relevant_move_state == 'partially_available':
                        picking.state = 'assigned'
                    else:
                        picking.state = relevant_move_state
                    # Custom Code End
                else:
                    if picking.immediate_transfer and relevant_move_state not in ('draft', 'cancel', 'done'):
                        picking.state = 'assigned'
                    elif relevant_move_state == 'partially_available':
                        picking.state = 'assigned'
                    else:
                        picking.state = relevant_move_state
