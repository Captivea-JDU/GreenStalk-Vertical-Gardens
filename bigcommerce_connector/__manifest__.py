{
    'name': 'BigCommerce Odoo Connector',
    'version': '15.1.0',
    'summary': '',
    'author': 'Novobi',
    'category': 'Sales',
    'website': 'https://novobi.com',
    'depends': [
        'sale_enterprise', 'stock_enterprise'
    ],
    'data': [
        'security/listing_channel_security.xml',
        'security/ir.model.access.csv',

        'views/ecommerce_channel_views.xml'
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'bigcommerce_connector/static/src/js/kanban_dashboard_graph.js',
            'bigcommerce_connector/static/src/js/boolean_button_widget.js',
            'bigcommerce_connector/static/src/scss/style.scss',
        ],
        'web.assets_qweb': [
            'bigcommerce_connector/static/src/xml/boolean_button.xml'
        ],
    },
    'images': ['static/description/main_screenshot.png'],
	'price': 1000,
	'currency': 'USD',
	'support': 'info@novobi.com',
    'license': 'OPL-1'
}
