import logging
from odoo import _, fields, models
from odoo.addons.sale_amazon_spapi import const, utils as amazon_utils


_logger = logging.getLogger(__name__)


class AmazonAccount(models.Model):
    _inherit = 'amazon.account'

    def _prepare_order_lines_values(self, order_data, currency, fiscal_pos, shipping_product):
        """ Prepare the values for the order lines to create based on Amazon data.

        Note: self.ensure_one()

        :param dict order_data: The order data related to the items data.
        :param record currency: The currency of the sales order, as a `res.currency` record.
        :param record fiscal_pos: The fiscal position of the sales order, as an
                                  `account.fiscal.position` record.
        :param record shipping_product: The shipping product matching the shipping code, as a
                                        `product.product` record.
        :return: The order lines values.
        :rtype: dict
        """
        def pull_items_data(amazon_order_ref_):
            """ Pull all items data for the order to synchronize.

            :param str amazon_order_ref_: The Amazon reference of the order to synchronize.
            :return: The items data.
            :rtype: list
            """
            items_data_ = []
            # Order items are pulled in batches. If more order items than those returned can be
            # synchronized, the request results are paginated and the next page holds another batch.
            has_next_page_ = True
            while has_next_page_:
                # Pull the next batch of order items.
                items_batch_data_, has_next_page_ = amazon_utils.pull_batch_data(
                    self, 'getOrderItems', {}, path_parameter=amazon_order_ref_
                )
                items_data_ += items_batch_data_['OrderItems']
            return items_data_

        def pull_gift_wraps_data(amazon_order_ref_):
            """ Pull all gift wraps data for the items of the order to synchronize.

            :param str amazon_order_ref_: The Amazon reference of the order to synchronize.
            :return: The gift wraps data.
            :rtype: dict
            """
            restricted_items_data_ = amazon_utils.make_sp_api_request(
                self, 'getOrderItemsBuyerInfo', path_parameter=amazon_order_ref_
            )['payload']['OrderItems']
            return {value_['OrderItemId']: value_ for value_ in restricted_items_data_}

        def convert_to_order_line_values(**kwargs_):
            """ Convert and complete a dict of values to comply with fields of `sale.order.line`.

            :param dict kwargs_: The values to convert and complete.
            :return: The completed values.
            :rtype: dict
            """
            subtotal_ = kwargs_.get('subtotal', 0)
            quantity_ = kwargs_.get('quantity', 1)
            return {
                'name': kwargs_.get('description', ''),
                'product_id': kwargs_.get('product_id'),
                'price_unit': subtotal_ / quantity_ if quantity_ else 0,
                'tax_id': [(6, 0, kwargs_.get('tax_ids', []))],
                'product_uom_qty': quantity_,
                'discount': (kwargs_.get('discount', 0) / subtotal_) * 100 if subtotal_ else 0,
                'display_type': kwargs_.get('display_type', False),
                'amazon_item_ref': kwargs_.get('amazon_item_ref'),
                'amazon_offer_id': kwargs_.get('amazon_offer_id'),
            }

        self.ensure_one()

        amazon_order_ref = order_data['AmazonOrderId']
        marketplace_api_ref = order_data['MarketplaceId']

        items_data = pull_items_data(amazon_order_ref)
        if any(item_data.get('IsGift', 'false') == 'true' for item_data in items_data):
            # Information on gift wraps is considered restricted data and thus not included in
            # items data. Pull them separately.
            gift_wraps_data = pull_gift_wraps_data(amazon_order_ref)
        else:
            gift_wraps_data = {}  # Information on gift wraps are not required.

        order_lines_values = []
        for item_data in items_data:
            # Prepare the values for the product line.
            sku = item_data['SellerSKU']
            marketplace = self.active_marketplace_ids.filtered(
                lambda m: m.api_ref == marketplace_api_ref
            )
            offer = self._get_offer(sku, marketplace)
            product_taxes = offer.product_id.taxes_id.filtered(
                lambda t: t.company_id.id == self.company_id.id
            )
            main_condition = item_data.get('ConditionId')
            sub_condition = item_data.get('ConditionSubtypeId')
            description_template = "[%s] %s" \
                if not main_condition or main_condition.lower() == 'new' \
                else _("[%s] %s\nCondition: %s - %s")
            description_fields = (sku, item_data['Title']) \
                if not main_condition or main_condition.lower() == 'new' \
                else (sku, item_data['Title'], main_condition, sub_condition)
            sales_price = float(item_data.get('ItemPrice', {}).get('Amount', 0.0))
            tax_amount = float(item_data.get('ItemTax', {}).get('Amount', 0.0))
            original_subtotal = sales_price - tax_amount \
                if marketplace.tax_included else sales_price
            taxes = fiscal_pos.map_tax(product_taxes) if fiscal_pos else product_taxes
            subtotal = self._recompute_subtotal(
                original_subtotal, tax_amount, taxes, currency, fiscal_pos
            )
            amazon_item_ref = item_data['OrderItemId']
            order_lines_values.append(convert_to_order_line_values(
                product_id=offer.product_id.id,
                description=description_template % description_fields,
                subtotal=subtotal,
                tax_ids=taxes.ids,
                quantity=item_data['QuantityOrdered'],
                discount=float(item_data.get('PromotionDiscount', {}).get('Amount', '0')),
                amazon_item_ref=amazon_item_ref,
                amazon_offer_id=offer.id,
            ))

            # Prepare the values for the gift wrap line.
            if item_data.get('IsGift', 'false') == 'true':
                item_gift_info = gift_wraps_data[amazon_item_ref]
                gift_wrap_code = item_gift_info.get('GiftWrapLevel')
                gift_wrap_price = float(item_gift_info.get('GiftWrapPrice', {}).get('Amount', '0'))
                if gift_wrap_code and gift_wrap_price != 0:
                    gift_wrap_product = self._get_product(
                        gift_wrap_code, 'default_product', 'Amazon Sales', 'consu'
                    )
                    gift_wrap_product_taxes = gift_wrap_product.taxes_id.filtered(
                        lambda t: t.company_id.id == self.company_id.id
                    )
                    gift_wrap_taxes = fiscal_pos.map_tax(gift_wrap_product_taxes) \
                        if fiscal_pos else gift_wrap_product_taxes
                    gift_wrap_tax_amount = float(
                        item_gift_info.get('GiftWrapTax', {}).get('Amount', '0')
                    )
                    original_gift_wrap_subtotal = gift_wrap_price - gift_wrap_tax_amount \
                        if marketplace.tax_included else gift_wrap_price
                    gift_wrap_subtotal = self._recompute_subtotal(
                        original_gift_wrap_subtotal,
                        gift_wrap_tax_amount,
                        gift_wrap_taxes,
                        currency,
                        fiscal_pos,
                    )
                    order_lines_values.append(convert_to_order_line_values(
                        product_id=gift_wrap_product.id,
                        description=_("[%s] Gift Wrapping Charges for %s") % (
                            gift_wrap_code, offer.product_id.name
                        ),
                        subtotal=gift_wrap_subtotal,
                        tax_ids=gift_wrap_taxes.ids,
                    ))
                gift_message = item_gift_info.get('GiftMessageText')
                if gift_message:
                    order_lines_values.append(convert_to_order_line_values(
                        description=_("Gift message:\n%s") % gift_message,
                        display_type='line_note',
                    ))

            # Prepare the values for the delivery charges.
            # shipping_code = order_data.get('ShipServiceLevel')
            # if shipping_code:
            #     shipping_price = float(item_data.get('ShippingPrice', {}).get('Amount', '0'))
            #     shipping_product_taxes = shipping_product.taxes_id.filtered(
            #         lambda t: t.company_id.id == self.company_id.id
            #     )
            #     shipping_taxes = fiscal_pos.map_tax(shipping_product_taxes) if fiscal_pos \
            #         else shipping_product_taxes
            #     shipping_tax_amount = float(item_data.get('ShippingTax', {}).get('Amount', '0'))
            #     origin_ship_subtotal = shipping_price - shipping_tax_amount \
            #         if marketplace.tax_included else shipping_price
            #     shipping_subtotal = self._recompute_subtotal(
            #         origin_ship_subtotal, shipping_tax_amount, shipping_taxes, currency, fiscal_pos
            #     )
            #     order_lines_values.append(convert_to_order_line_values(
            #         product_id=shipping_product.id,
            #         description=_("[%s] Delivery Charges for %s") % (
            #             shipping_code, offer.product_id.name
            #         ),
            #         subtotal=shipping_subtotal,
            #         tax_ids=shipping_taxes.ids,
            #         discount=float(item_data.get('ShippingDiscount', {}).get('Amount', '0')),
            #     ))

        return order_lines_values
