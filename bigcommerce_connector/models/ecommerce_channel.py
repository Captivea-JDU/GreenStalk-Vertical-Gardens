import json
from datetime import datetime, timedelta
from babel.dates import format_date

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.misc import get_lang

from ..utils.bigcommerce_api_helper import BigCommerceAPIHelper

class EcommerceChannel(models.Model):
    _name = "ecommerce.channel"
    _description = "eCommerce Channel"
    
    @api.model
    def _default_measure_unit(self):
        return self.env['uom.uom'].search([('name', '=', 'inch(es)')], limit=1).id

    name = fields.Char(string='Name', required=True, copy=False)
    platform = fields.Selection(selection=[('bigcommerce', 'BigCommerce')],
                                string='Platform',
                                readonly=False,
                                required=False)
    app_client_id = fields.Char(string='Client ID')
    app_access_token = fields.Char(string='Access Token')
    store_hash = fields.Char(string='Store Hash')
    active = fields.Boolean(string='Active', default=True, copy=False)

    status = fields.Selection([('connected', 'Connected'), ('disconnected', 'Disconnected')],
                              help='Connection status with channel', default='connected', compute='_get_status',
                              inverse='_set_status')
    last_sync_order = fields.Datetime(string='Last Order Sync', readonly=False, default=fields.Datetime.now)
    min_order_date_created = fields.Datetime(string='Minimum date the order was created',
                                             help='Only get order created after this time')
    menu_listing_id = fields.Many2one('ir.ui.menu', readonly=True)
    menu_order_id = fields.Many2one('ir.ui.menu', readonly=True)
    
    company_id = fields.Many2one('res.company', "Company",
                                 readonly=True,
                                 default=lambda self: self.env.company, required=False)

    kanban_dashboard = fields.Text(compute='_compute_kanban_dashboard')
    show_on_dashboard = fields.Boolean(string='Show journal on dashboard',
                                       help="Whether this journal should be displayed on the dashboard or not",
                                       default=True)
    color = fields.Integer("Color Index", default=0)
    
    weight_unit = fields.Selection([('oz', 'Ounce(s)'),
                                    ('lb', 'Pound(s)'),
                                    ('g', 'Gram(s)'),
                                    ('kg', 'Kilogram(s)'),
                                    ('t', 'Tonne(s)')], string='Weight Measurement', default='lb')

    dimension_unit = fields.Selection([('in', 'Inch(es)'),
                                       ('cm', 'Centimeter(s)'),
                                       ('m', 'Meter(s)'),
                                       ('mm', 'Millimeter(s)'),
                                       ('yd', 'Yard(s)')], string='Length Measurement', default='in')
    
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    currency_ids = fields.Many2many('res.currency', string='Currencies',
                                    help='All currencies supported by this store')
    
    # Product Configuration
    auto_create_master_product = fields.Boolean(string='Auto Create Product if Not Found', default=True)

    default_categ_id = fields.Many2one('product.channel.category', string='Default Category')
    
    # Inventory Configuration
    is_enable_inventory_sync = fields.Boolean(string='Enable Inventory Sync')
    is_allow_manual_bulk_inventory_sync = fields.Boolean(string='Allow Bulk Sync Manually')
    last_all_inventory_sync = fields.Datetime(string='Last all inventory updated')
    default_warehouse_id = fields.Many2one('stock.warehouse', string='Default Warehouse',
                                           help='This warehouse is used in doing fulfillment')
    active_warehouse_ids = fields.Many2many('stock.warehouse', string='Active Warehouses',
                                            domain="[('company_id', '=', company_id)]")
    percentage_inventory_sync = fields.Float(string='Percentage', default=100.0)
    is_enable_maximum_inventory_sync = fields.Boolean(string='Enable Maximum Quantity')
    is_enable_minimum_inventory_sync = fields.Boolean(string='Enable Minimum Quantity')
    maximum_inventory_sync = fields.Integer(string='Maximum Quantity')
    minimum_inventory_sync = fields.Integer(string='Minimum Quantity', default=0)
    is_running_bulk_inventory_sync = fields.Boolean(string='Running bulk inventory sync')
    exclude_inventory_sync_ids = fields.One2many('exclude.inventory.sync', 'channel_id', 'Exclude Products to Sync Inventory')

    inventory_help_text = fields.Char(string='Inventory Help Text', compute='_compute_inventory_help_text')

    auto_export_shipment_to_store = fields.Boolean(string='Auto export shipment to store', default=True, 
                                                   help='Shipment will be updated automatically when it validated in Odoo')

    # Order Configuration
    allow_update_order = fields.Boolean('Allow to update orders after the first sync', default=True)

    order_prefix = fields.Char(string='Order Prefix')
    sales_team_id = fields.Many2one('crm.team', string='Sales Team')
    min_order_date_to_import = fields.Date('Order Date to Import')
    default_guest_customer = fields.Char(string='Guest Customer Name', required=True, default='Guest')
    default_tax_product_id = fields.Many2one('product.product', string='Tax')
    default_discount_product_id = fields.Many2one('product.product', string='Discount')
    default_fee_product_id = fields.Many2one('product.product', string='Fee')
    default_shipping_cost_product_id = fields.Many2one('product.product', string='Shipping Cost')
    default_handling_cost_product_id = fields.Many2one('product.product', string='Handling Cost')
    default_wrapping_cost_product_id = fields.Many2one('product.product', string='Wrapping Cost')

    default_order_tag_ids = fields.Many2many(
        comodel_name='crm.tag',
        relation='ecommerce_channel_sale_tag_rel',
        string='Default Order Tags',
        help='Order Tags are included when creating new orders',
    )
    default_shipping_policy = fields.Selection([
        ('direct', 'As soon as possible'),
        ('one', 'When all products are ready')],
        default=lambda self: self.env['ir.default'].get_model_defaults('sale.order').get('picking_policy') or 'direct',
        string='Shipping Policy',
        help="If you deliver all products at once, the delivery order will be scheduled based on the greatest "
        "product lead time. Otherwise, it will be based on the shortest.")

    order_process_rule_ids = fields.One2many('order.process.rule', 'channel_id', string='Actions')

    default_payment_journal_id = fields.Many2one('account.journal', string='Default Payment Journal',
                                                 domain="[('type', 'in', ['bank', 'cash'])]")

    default_payment_method_id = fields.Many2one('account.payment.method',
                                                string='Default Payment Method',
                                                readonly=False,
                                                store=True,
                                                compute='_compute_payment_method_id',
                                                domain="[('id', 'in', available_payment_method_ids)]")

    default_deposit_account_id = fields.Many2one(
        'account.account',
        string='Default Deposit Account',
        domain=lambda self: [
            ('user_type_id', 'in', [self.env.ref('account.data_account_type_current_liabilities').id]),
            ('deprecated', '=', False),
            ('reconcile', '=', True),
        ])

    payment_method_mapping_ids = fields.One2many('payment.method.mapping', 'channel_id', string='Payment Method Mapping')

    available_payment_method_ids = fields.Many2many(
        'account.payment.method', compute='_compute_payment_method_fields')

    is_import_customer_allowed = fields.Boolean(default=True)
    default_customer_id = fields.Many2one('res.partner')

    kanban_dashboard_graph = fields.Text(compute='_compute_kanban_dashboard_graph')
    
    def get_graph_datas(self):
        last_30_days = datetime.now().replace(hour=0, minute=0, second=0) - timedelta(days=30)

        def build_graph_data(start_date, end_date, amount):
            # display date in locale format
            name = format_date(start_date, 'd LLLL Y', locale=locale)
            short_name = format_date(start_date, 'd MMM', locale=locale)
            short_name += ' - ' + format_date(end_date, 'd MMM', locale=locale)
            return {'x': short_name,
                    'y': amount,
                    'name': name}

        query = """
            SELECT DATE(o.date_order) AS order_date,
                  COALESCE(SUM(o.amount_total), 0) AS total
            FROM sale_order AS o
            WHERE o.date_order >= %s
              AND o.channel_id = %s
              AND o.state IN ('sale', 'done')
            GROUP BY order_date
        """
        locale = get_lang(self.env).code
        self.env.cr.execute(query, (last_30_days, self.id))
        query_result = self.env.cr.dictfetchall()
        data = []

        week_start = int(self.env['res.lang']._lang_get(self.env.user.lang).week_start) - 1
        week_end = week_start - 1 if week_start != 0 else 6

        # Set default
        today = datetime.today().replace(hour=23, minute=59, second=59)
        index = last_30_days
        while index < today:
            start_of_week = index.replace(hour=0, minute=0, second=0)
            shift = (7 + week_end - index.weekday()) % 7
            end_of_week = (index + timedelta(days=shift)).replace(hour=23, minute=59, second=59)
            if end_of_week > today:
                end_of_week = today
            rows = list(filter(lambda r: start_of_week.date() <= r['order_date'] <= end_of_week.date(), query_result))
            data.append(build_graph_data(start_of_week.date(), end_of_week.date(), sum([r['total'] for r in rows]) or 0))
            index = end_of_week + timedelta(days=1)

        return [{
            'values': data,
            'title': '',
            'key': _('Total sales'),
            'area': True, 'color': '#875A7B',
            'currency': {
                'symbol': self.env.company.currency_id.symbol,
                'position': self.env.company.currency_id.position,
                'id': self.env.company.currency_id.id
            }
        }]
        
    def _compute_kanban_dashboard(self):
        for record in self:
            record.kanban_dashboard = json.dumps(record.get_dashboard_datas())

    def _compute_kanban_dashboard_graph(self):
        for record in self:
            record.kanban_dashboard_graph = json.dumps(record.get_graph_datas())
        
    @api.depends('default_payment_journal_id')
    def _compute_payment_method_fields(self):
        for record in self:
            available_payment_methods = record.default_payment_journal_id.mapped('inbound_payment_method_line_ids.payment_method_id')
            record.available_payment_method_ids = available_payment_methods

    @api.depends('default_payment_journal_id')
    def _compute_payment_method_id(self):
        for record in self:
            available_payment_method_ids = record.default_payment_journal_id.mapped('inbound_payment_method_line_ids.payment_method_id')
            if available_payment_method_ids:
                record.default_payment_method_id = available_payment_method_ids[0]._origin
            else:
                record.default_payment_method_id = False
                
    def get_dashboard_datas(self):
        self.ensure_one()
        last_30_days = datetime.now().replace(hour=0, minute=0, second=0) - timedelta(days=30)

        query = """
            SELECT COALESCE(COUNT(o.id), 0) AS unit,
                  COALESCE(SUM(o.amount_total), 0) AS total
            FROM sale_order AS o
            WHERE o.date_order >= %s
              AND o.channel_id = %s
              AND o.state IN ('sale', 'done')
        """

        self.env.cr.execute(query, (last_30_days, self.id))
        query_result = self.env.cr.dictfetchall()
        result = {'sales_unit': 0, 'sales_total': 0}
        if query_result:
            result.update({'sales_unit': query_result[0]['unit'], 'sales_total': query_result[0]['total']})
        result['sales_total'] = self.company_id.currency_id.format_value(result['sales_total'])
        return result

    def check_connection(self):
        self.ensure_one()
        cust_method_name = '_%s_check_connection' % self.platform
        if hasattr(self, cust_method_name):
            return getattr(self, cust_method_name)()
        return True
    
    def button_check_connection(self):
        response = self.check_connection()
        if not response:
            raise ValidationError(_('Invalid credentials, please verify that you type the correct info and try again.'))
        return response
    
    
    def _get_status(self):
        for record in self:
            record.with_context(for_channel_creation=True).status = 'connected' if record.active else 'disconnected'

    def _set_status(self):
        for record in self:
            record.with_context(for_channel_creation=True).active = False if record.status == 'disconnected' else True

    def _get_menus(self):
        self.ensure_one()
        menus = self.with_context(active_test=False).menu_listing_id + self.with_context(active_test=False).menu_order_id
        return menus
    
    def reconnect(self):
        self.ensure_one()
        if self.check_connection():
            self._get_menus().sudo().write({'active': True})
            action = self.env["ir.actions.actions"]._for_xml_id('bigcommerce_connector.action_channel_overview')
            action['target'] = 'main'
            # Update last sync order after re-connecting
            self.sudo().write({'active': True, 'last_sync_order': fields.Datetime.now()})
            # TODO Need to discuss about data of channel after reconnected
            return action
        else:
            raise ValidationError(_("Cannot reconnect. "
                                    "You can reach out to our support team by email at support_omniborder@novobi.com."))

    def disconnect(self):
        self.ensure_one()
        self._get_menus().sudo().write({'active': False})
        action = self.env["ir.actions.actions"]._for_xml_id('bigcommerce_connector.action_channel_overview')
        action['target'] = 'main'
        self.sudo().write({'active': False})
        return action
    
    def open_settings(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id('bigcommerce_connector.action_ecommerce_channel_setting')
        action['res_id'] = self.id
        if self.platform:
            action['context'] = {'include_platform': True,
                                 'only_active_menu': True,
                                 'default_channel_id': self.id}
            form_view = self.env.ref('bigcommerce_connector.view_ecommerce_channel_form_settings')
            action.update({
                'views': [(form_view.id, 'form')],
                'view_id': form_view.id
            })
            action['display_name'] = self.name
        return action
    
    def open_product_channel_categories(self):
        raise ValidationError(_("You can reach out to our support team by email at support_omniborder@novobi.com."))
    
    def open_product_brands(self):
        raise ValidationError(_("You can reach out to our support team by email at support_omniborder@novobi.com."))
    
    def open_tax_classes(self):
        raise ValidationError(_("You can reach out to our support team by email at support_omniborder@novobi.com."))
    
    def open_customer_groups(self):
        raise ValidationError(_("You can reach out to our support team by email at support_omniborder@novobi.com."))
    
    def open_channel_pricelist(self):
        raise ValidationError(_("You can reach out to our support team by email at support_omniborder@novobi.com."))
    
    def open_payment_gateways(self):
        raise ValidationError(_("You can reach out to our support team by email at support_omniborder@novobi.com."))
    
    def action_import_product_manually(self):
        raise ValidationError(_("You can reach out to our support team by email at support_omniborder@novobi.com."))
    
    def open_import_other_data(self):
        raise ValidationError(_("You can reach out to our support team by email at support_omniborder@novobi.com."))
    
    def action_import_order_manually(self):
        raise ValidationError(_("You can reach out to our support team by email at support_omniborder@novobi.com."))
    
    def open_log_import_product(self):
        raise ValidationError(_("You can reach out to our support team by email at support_omniborder@novobi.com."))
    
    def open_log_import_other_data(self):
        raise ValidationError(_("You can reach out to our support team by email at support_omniborder@novobi.com."))
    
    def open_log_import_order(self):
        raise ValidationError(_("You can reach out to our support team by email at support_omniborder@novobi.com."))
    
    def refresh_currencies(self):
        self.ensure_one()
        cust_method_name = '_%s_refresh_currencies' % self.platform
        if hasattr(self, cust_method_name):
            return getattr(self, cust_method_name)()
        return True
    
    @api.model
    def _bulk_sync(self, channel_id):
        self.env['stock.move'].inventory_sync(channel_id=channel_id, all_records=True)
        
    def bulk_inventory_sync(self):
        self.ensure_one()
        self = self.sudo()
        if not self.active:
            raise UserError(_('Your channel has been disconnected. Please contact your administrator.'))

        if self.is_running_bulk_inventory_sync:
            raise UserError(_('Inventory Syncing is running.'))

        if not self.is_enable_inventory_sync:
            raise UserError(_('Bulk inventory sync cannot do now, please make sure the inventory sync is enabled.'))

        self.write({
            'last_all_inventory_sync': fields.Datetime.now(),
            'is_running_bulk_inventory_sync': True,
            'warning_message': False
        })
        try:
            self._bulk_sync(self.id)
        except Exception as e:
            raise ValidationError(e)

    
    def _bigcommerce_check_connection(self):
        api = BigCommerceAPIHelper(self)
        res = api.send(method='GET', path='v2/store')
        if res.status_code == 200:
            return {
                'effect': {
                    'type': 'rainbow_man',
                    'message': _("Everything is correctly set up !"),
                }
            }
        return False