import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)


class WhatsappInstance(models.Model):
    _inherit = "whatsapp.instance"

    sale_order_add_signature = fields.Boolean("Sale Order Add signature?")
    sale_order_add_order_product_details = fields.Boolean("Sale Order Add product details in message?")
    sale_order_add_order_info_msg = fields.Boolean("Sale Order Add information in message?")
    sale_order_add_message_in_chatter = fields.Boolean("Sale Order Add chatter message?")

    account_invoice_add_signature = fields.Boolean("Account Invoice Add signature?")
    account_invoice_add_invoice_product_details = fields.Boolean("Account Invoice Add product details in message?")
    account_invoice_add_invoice_info_msg = fields.Boolean("Account Invoice Add information in message?")
    account_invoice_add_message_in_chatter = fields.Boolean("Account Invoice Add chatter message?")
    account_payment_details = fields.Boolean("Account Payment Add Payment Details")

    delivery_order_add_signature = fields.Boolean("Delivery Order Add signature?")
    delivery_order_add_order_product_details = fields.Boolean("Delivery Order Add product details in message?")
    delivery_order_add_order_info_msg = fields.Boolean("Delivery Order Add information in message?")
    delivery_order_add_message_in_chatter = fields.Boolean("Delivery Order Add chatter message?")

    purchase_order_add_signature = fields.Boolean("Purchase Order Add signature?")
    purchase_order_add_order_product_details = fields.Boolean("Purchase Order Add product details in message?")
    purchase_order_add_order_info_msg = fields.Boolean("Purchase Order Add information in message?")
    purchase_order_add_message_in_chatter = fields.Boolean("Purchase Order Add chatter message?")

    crm_lead_add_signature = fields.Boolean("CRM Lead Add signature?")
    crm_lead_add_message_in_chatter = fields.Boolean("CRM Lead Add chatter message?")

    project_task_add_signature = fields.Boolean("Project Task Add signature?")
    project_task_add_message_in_chatter = fields.Boolean("Project Task Add chatter message?")

    def action_create_missing_templates(self):
        super(WhatsappInstance, self).action_create_missing_templates()
        if self.status == 'enable':
            if self.provider == 'whatsapp_chat_api':
                self.chatapi_create_missing_templates()
            elif self.provider == 'gupshup':
                self.gupshup_create_missing_templates()
        return True

    def chatapi_create_missing_templates(self):
        self.chat_api_create_templates_for_sale_order()
        self.chat_api_create_templates_for_account_invoice()
        self.chat_api_create_templates_for_delivery_order()
        self.chat_api_create_templates_for_account_payment()
        self.chat_api_create_templates_for_purchase_order()
        self.chat_api_create_templates_for_project_task()
        self.chat_api_create_templates_for_crm_lead()
        self.website_signup_page_chat_api()
        self.send_pos_message_chat_api()
        self.account_invoice_payment_remainder()

    def chat_api_create_templates_for_sale_order(self):
        self.sale_order_without_order_details_lines_signature_chat_api()
        self.sale_order_without_order_details_lines_with_signature_chat_api()
        self.sale_order_without_lines_signature_with_order_details_chat_api()
        self.sale_order_without_order_details_signature_with_lines_chat_api()
        self.sale_order_without_lines_with_signature_order_details_chat_api()
        self.sale_order_without_order_details_with_signature_lines_chat_api()
        self.sale_order_without_signature_with_order_details_lines_chat_api()
        self.sale_order_with_signature_order_details_lines_chat_api()

    def sale_order_without_order_details_lines_signature_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'sale_order_without_order_details_lines_signature_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('sale.order').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': False,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Please find attached the order form which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/S00014.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def sale_order_without_order_details_lines_with_signature_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'sale_order_without_order_details_lines_with_signature_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('sale.order').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': True,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Please find attached the order form which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/S00014.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def sale_order_without_lines_signature_with_order_details_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'sale_order_without_lines_signature_with_order_details_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('sale.order').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': False,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Your order {{2}}  is placed' + '\n' + 'Total Amount: {{3}}' + '\n' + 'Please find attached the order form which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator,S00013,$ 3.00',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/S00014.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def sale_order_without_order_details_signature_with_lines_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'sale_order_without_order_details_signature_with_lines_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('sale.order').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': False,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Here are the details of your order.' + '\n' + '{{2}}' + '\nPlease find attached the order form which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator,*Product:* Flash  *Qty:* 1.0 Units  *Unit Price:* 3.0  *Subtotal:* 3.0',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/S00014.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def sale_order_without_lines_with_signature_order_details_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'sale_order_without_lines_with_signature_order_details_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('sale.order').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': True,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Your order {{2}}  is placed' + '\n' + 'Total Amount: {{3}}' + '\nPlease find attached the order form which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator,S00013,$ 3.00',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/S00014.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def sale_order_without_order_details_with_signature_lines_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'sale_order_without_order_details_with_signature_lines_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('sale.order').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': True,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Here are the details of your order.' + '\n' + '{{2}}' + 'Please find attached the order form which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator,*Product:* Flash  *Qty:* 1.0 Units  *Unit Price:* 3.0  *Subtotal:* 3.0',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/S00014.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def sale_order_without_signature_with_order_details_lines_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'sale_order_without_signature_with_order_details_lines_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('sale.order').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': False,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Your order *{{2}}*  is placed' + '\n' + 'Total Amount: {{3}}' + '\nHere are the details of your order.' + '\n' + '{{4}}' + '\nPlease find attached the order form which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator,S00013,$ 3.00,*Product:* Flash  *Qty:* 1.0 Units  *Unit Price:* 3.0  *Subtotal:* 3.0',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/S00014.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def sale_order_with_signature_order_details_lines_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'sale_order_with_signature_order_details_lines_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('sale.order').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': True,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Your order *{{2}}*  is placed' + '\n' + 'Total Amount: {{3}}' + '\nHere are the details of your order.' + '\n' + '{{4}}' + '\nPlease find attached the order form which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator,S00013,$ 3.00,*Product:* Flash  *Qty:* 1.0 Units  *Unit Price:* 3.0  *Subtotal:* 3.0',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/S00014.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def chat_api_create_templates_for_account_invoice(self):
        self.account_invoice_without_invoice_details_lines_signature_chat_api()
        self.account_invoice_without_invoice_details_lines_with_signature_chat_api()
        self.account_invoice_without_lines_signature_with_invoice_details_chat_api()
        self.account_invoice_without_invoice_details_signature_with_lines_chat_api()
        self.account_invoice_without_lines_with_signature_invoice_details_chat_api()
        self.account_invoice_without_invoice_details_with_signature_lines_chat_api()
        self.account_invoice_without_signature_with_invoice_details_lines_chat_api()
        self.account_invoice_with_signature_invoice_details_lines_chat_api()

    def account_invoice_without_invoice_details_lines_signature_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'account_invoice_without_invoice_details_lines_signature_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('account.move').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': False,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Kindly search the invoice pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/INV00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def account_invoice_without_invoice_details_lines_with_signature_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'account_invoice_without_invoice_details_lines_with_signature_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('account.move').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': True,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Kindly search the invoice pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/INV00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def account_invoice_without_lines_signature_with_invoice_details_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'account_invoice_without_lines_signature_with_invoice_details_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('account.move').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': False,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Your {{2}} invoice is created' + '\n' + 'Total Amount: {{3}}' + '\nKindly search the invoice pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator,INV/2022/00008,$ 3.00',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/INV00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def account_invoice_without_invoice_details_signature_with_lines_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'account_invoice_without_invoice_details_signature_with_lines_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('account.move').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': False,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Here are the details of your invoice.' + '\n' + '{{2}}' + '\nKindly search the invoice pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator,*Product:* Flash  *Qty:* 1.0 Units  *Unit Price:* 3.0  *Subtotal:* 3.0',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/INV00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def account_invoice_without_lines_with_signature_invoice_details_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'account_invoice_without_lines_with_signature_invoice_details_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('account.move').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': True,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Your {{2}} invoice is created' + '\n' + 'Total amount: {{3}}' + '\nKindly search the invoice pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator,INV/2022/00008,$ 3.00',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/INV00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def account_invoice_without_invoice_details_with_signature_lines_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'account_invoice_without_invoice_details_with_signature_lines_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('account.move').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': True,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Here are the details of your invoice.' + '\n' + '{{2}}' + '\nKindly search the invoice pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator,*Product:* Flash  *Qty:* 1.0 Units  *Unit Price:* 3.0  *Subtotal:* 3.0',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/INV00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def account_invoice_without_signature_with_invoice_details_lines_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'account_invoice_without_signature_with_invoice_details_lines_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('account.move').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': False,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Your {{2}} invoice is created' + '\n' + 'Total amount: {{3}}' + '\n' + 'Here are the details of your invoice.' + '\n' + '{{4}}' + '\nKindly search the invoice pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator,INV/2022/00008,$ 3.00,*Product:* Flash  *Qty:* 1.0 Units  *Unit Price:* 3.0  *Subtotal:* 3.0',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/INV00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def account_invoice_with_signature_invoice_details_lines_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'account_invoice_with_signature_invoice_details_lines_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('account.move').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': True,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Your {{2}} invoice is created' + '\n' + 'Total amount: {{3}}' + '\n' + 'Here are the details of your invoice.' + '\n' + '{{4}}' + '\nKindly search the invoice pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator,S00013,$ 3.00,*Product:* Flash  *Qty:* 1.0 Units  *Unit Price:* 3.0  *Subtotal:* 3.0',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/INV00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def chat_api_create_templates_for_delivery_order(self):
        self.delivery_order_without_order_details_lines_signature_chat_api()
        self.delivery_order_without_order_details_lines_with_signature_chat_api()
        self.delivery_order_without_lines_signature_with_order_details_chat_api()
        self.delivery_order_without_order_details_signature_with_lines_chat_api()
        self.delivery_order_without_lines_with_signature_order_details_chat_api()
        self.delivery_order_without_order_details_with_signature_lines_chat_api()
        self.delivery_order_without_signature_with_order_details_lines_chat_api()
        self.delivery_order_with_signature_order_details_lines_chat_api()

    def delivery_order_without_order_details_lines_signature_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'delivery_order_without_order_details_lines_signature_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('stock.picking').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': False,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'See the delivery order pdf that will help you get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/Delivery00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def delivery_order_without_order_details_lines_with_signature_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'delivery_order_without_order_details_lines_with_signature_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('stock.picking').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': True,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'See the delivery order pdf that will help you get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/Delivery00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def delivery_order_without_lines_signature_with_order_details_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'delivery_order_without_lines_signature_with_order_details_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('stock.picking').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': False,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Here is your delivery order {{2}} (with reference: {{3}})' + 'See the delivery order pdf that will help you get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator,WH/OUT/00012,S00013',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/Delivery00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def delivery_order_without_order_details_signature_with_lines_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'delivery_order_without_order_details_signature_with_lines_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('stock.picking').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': False,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Here are the details of your delivery order.' + '\n' + '{{2}}' + 'See the delivery order pdf that will help you get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator,*Product:* Flash  *Qty:* 1.0 Units  *Unit Price:* 3.0  *Subtotal:* 3.0',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/S00014.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def delivery_order_without_lines_with_signature_order_details_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'delivery_order_without_lines_with_signature_order_details_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('stock.picking').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': True,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Here is your delivery order {{2}} (with reference: {{3}})' + '\n' + 'See the delivery order pdf that will help you get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator,WH/OUT/00012,S00013',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/Delivery00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def delivery_order_without_order_details_with_signature_lines_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'delivery_order_without_order_details_with_signature_lines_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('stock.picking').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': True,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Here are the details of your delivery order.' + '\n' + '{{2}}' + '\nSee the delivery order pdf that will help you get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator,*Product:* Flash  *Qty:* 1.0 Units  *Unit Price:* 3.0  *Subtotal:* 3.0',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/Delivery00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def delivery_order_without_signature_with_order_details_lines_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'delivery_order_without_signature_with_order_details_lines_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('stock.picking').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': False,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Here is your delivery order {{2}} (with reference: {{3}})' + '\n' + 'Here are the details of your delivery order.' + '\n' + '{{4}}' + '\nSee the delivery order pdf that will help you get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator,WH/OUT/00012,S00013,*Product:* Flash  *Qty:* 1.0 Units  *Unit Price:* 3.0  *Subtotal:* 3.0',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/Delivery00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def delivery_order_with_signature_order_details_lines_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'delivery_order_with_signature_order_details_lines_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('stock.picking').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': True,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Here is your delivery order {{2}} (with reference: {{3}})' + '\n' + 'Here are the details of your delivery order.' + '\n' + '{{4}}' + '\nSee the delivery order pdf that will help you get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator,WH/OUT/00012,S00013,*Product:* Flash  *Qty:* 1.0 Units  *Unit Price:* 3.0  *Subtotal:* 3.0',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/Delivery00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def chat_api_create_templates_for_account_payment(self):
        self.account_payment_without_payment_details_signature_chat_api()
        self.account_payment_without_payment_details_with_signature_chat_api()
        self.account_payment_without_signature_with_payment_details_chat_api()
        self.account_payment_with_signature_payment_details_chat_api()

    def account_payment_without_payment_details_signature_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'account_payment_without_payment_details_signature_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('account.payment').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': False,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Kindly search the payment receipt pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/Payment Receipt.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def account_payment_without_payment_details_with_signature_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'account_payment_without_payment_details_with_signature_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('account.payment').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': True,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Kindly search the payment receipt pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/Payment Receipt.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def account_payment_without_signature_with_payment_details_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'account_payment_without_signature_with_payment_details_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('account.payment').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': False,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Payment of your account {{2}}' + '\n' + 'Total amount: {{3}}' + '\n' + 'The following are your payment details.' + '\n' + '*Payment Type:* {{4}}' + '\n' + '*Payment Journal:* {{5}}' + '\n' + '*Payment date:* {{6}}' + '\n' + '*Memo:* {{7}}' + '\n' + 'Kindly search the payment receipt pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator,BNK1/2022/07/0002,$198.95,inbound,Bank,2022-07-12,INV/2022/00002',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/Payment Receipt.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def account_payment_with_signature_payment_details_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'account_payment_with_signature_payment_details_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('account.payment').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': True,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Payment of your account {{2}}' + '\n' + 'Total amount: {{3}}' + '\n' + 'The following are your payment details.' + '\n' + '*Payment Type:* {{4}}' + '\n' + '*Payment Journal:* {{5}}' + '\n' + '*Payment date:* {{6}}' + '\n' + '*Memo:* {{7}}' + '\n' + 'Kindly search the payment receipt pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator,BNK1/2022/07/0002,$198.95,inbound,Bank,2022-07-12,INV/2022/00002',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/Payment Receipt.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def chat_api_create_templates_for_purchase_order(self):
        self.purchase_order_without_order_details_lines_signature_chat_api()
        self.purchase_order_without_order_details_lines_with_signature_chat_api()
        self.purchase_order_without_lines_signature_with_order_details_chat_api()
        self.purchase_order_without_order_details_signature_with_lines_chat_api()
        self.purchase_order_without_lines_with_signature_order_details_chat_api()
        self.purchase_order_without_order_details_with_signature_lines_chat_api()
        self.purchase_order_without_signature_with_order_details_lines_chat_api()
        self.purchase_order_with_signature_order_details_lines_chat_api()

    def purchase_order_without_order_details_lines_signature_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'purchase_order_without_order_details_lines_signature_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('purchase.order').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': False,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Kindly search the purchase order pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/P00002.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def purchase_order_without_order_details_lines_with_signature_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'purchase_order_without_order_details_lines_with_signature_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('purchase.order').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': True,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Kindly search the purchase order pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/P00002.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def purchase_order_without_lines_signature_with_order_details_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'purchase_order_without_lines_signature_with_order_details_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('purchase.order').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': False,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Here is your Purchase order {{2}}' + '\n' + 'Total Amount: {{3}}' + 'Kindly search the purchase order pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator,P00002,$ 347.50',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/P00002.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def purchase_order_without_order_details_signature_with_lines_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'purchase_order_without_order_details_signature_with_lines_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('purchase.order').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': False,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Here are the details of your order.' + '\n' + '{{2}}' + 'Kindly search the purchase order pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator,*Product:* Office Lamp  *Qty:* 20.0 Units  *Unit Price:* 132.5  *Subtotal:* 2650.0',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/P00002.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def purchase_order_without_lines_with_signature_order_details_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'purchase_order_without_lines_with_signature_order_details_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('purchase.order').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': True,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Here is your Purchase order {{2}}' + '\n' + 'Total Amount: {{3}}' + 'Kindly search the purchase order pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator,P00002,$ 347.50',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/P00002.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def purchase_order_without_order_details_with_signature_lines_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'purchase_order_without_order_details_with_signature_lines_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('purchase.order').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': True,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Here are the details of your order.' + '\n' + '{{2}}' + 'Kindly search the purchase order pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator,*Product:* Flash  *Qty:* 1.0 Units  *Unit Price:* 3.0  *Subtotal:* 3.0',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/P00002.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def purchase_order_without_signature_with_order_details_lines_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'purchase_order_without_signature_with_order_details_lines_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('purchase.order').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': False,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Here is your Purchase order {{2}}' + '\n' + 'Total Amount: {{3}}' + 'Here are the details of your order.' + '\n' + '{{4}}' + 'Kindly search the purchase order pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator,P00002,$ 347.50,*Product:* Office Lamp  *Qty:* 20.0 Units  *Unit Price:* 132.5  *Subtotal:* 2650.0',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/P00002.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def purchase_order_with_signature_order_details_lines_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'purchase_order_with_signature_order_details_lines_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('purchase.order').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': True,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Here is your Purchase order *{{2}}*' + '\n' + 'Total Amount: {{3}}' + 'Here are the details of your order.' + '\n' + '{{4}}' + 'Kindly search the purchase order pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_message': 'Administrator,P00002,$ 347.50,*Product:* Office Lamp  *Qty:* 20.0 Units  *Unit Price:* 132.5  *Subtotal:* 2650.0',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/P00002.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def chat_api_create_templates_for_project_task(self):
        self.project_task_without_signature_chat_api_template()
        self.project_task_with_signature_chat_api_template()

    def project_task_without_signature_chat_api_template(self):
        whatsapp_templates_dict = {
            'name': 'project_task_without_signature_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('project.task').id,
            'template_type': 'simple',
            'default_template': True,
            'header_text': 'New task assigned to you',
            'send_template': False,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'New task assigned to you.' + '\n' + '*Project*: {{2}}' + '\n' + '*Task name*: {{3}}' + '\n' + '*Deadline*: {{4}}' + '\n' + '*Description*: {{5}}',
            'header': 'text',
            'interactive_actions': 'quick_replies',
            'quick_reply1': 'Done',
            'sample_message': "Administrator,Planning and budget,Research and Development,22-07-13,Planning and Budgeting is an analytical application that helps you set top-down targets and generate a bottom-up budget, which is at the foundation of your organization's operations.",
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def project_task_with_signature_chat_api_template(self):
        whatsapp_templates_dict = {
            'name': 'project_task_with_signature_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('project.task').id,
            'template_type': 'simple',
            'default_template': True,
            'header_text': 'New task assigned to you',
            'send_template': True,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'New task assigned to you.' + '\n' + '*Project*: {{2}}' + '\n' + '*Task name*: {{3}}' + '\n' + '*Deadline*: {{4}}' + '\n' + '*Description*: {{5}}',
            'header': 'text',
            'interactive_actions': 'quick_replies',
            'quick_reply1': 'Done',
            'sample_message': "Administrator,Planning and budget,Research and Development,22-07-13,Planning and Budgeting is an analytical application that helps you set top-down targets and generate a bottom-up budget, which is at the foundation of your organization's operations.",
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def chat_api_create_templates_for_crm_lead(self):
        self.crm_lead_without_signature_chat_api()
        self.crm_lead_with_signature_chat_api()

    def crm_lead_without_signature_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'crm_lead_without_signature_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('crm.lead').id,
            'template_type': 'simple',
            'default_template': True,
            'header_text': 'New lead assigned to you.',
            'send_template': False,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'New lead assigned to you.' + '\n' + '*Lead Name*: {{2}}' + '\n' + '*Customer*: {{3}}' + '\n' + '*Email*: {{4}}' + '\n' + '*Phone*: {{5}}' + '\n' + '*Expected closing date*: {{6}}' + '\n' + '*Description*: {{7}}',
            'header': 'text',
            'sample_message': "Administrator,Office Design Project ,Azure Interior,john.b@tech.info,+1 312-349-2324,2022-07-13,This new workspace between the East 4th-5th Ring Road of Beijing City aims to provide for its users with both a space to work in and also relax and feel close to nature.",
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def crm_lead_with_signature_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'crm_lead_with_signature_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('crm.lead').id,
            'template_type': 'simple',
            'default_template': True,
            'header_text': 'New lead assigned to you.',
            'send_template': True,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'New lead assigned to you.' + '\n' + '*Lead Name*: {{2}}' + '\n' + '*Customer*: {{3}}' + '\n' + '*Email*: {{4}}' + '\n' + '*Phone*: {{5}}' + '\n' + '*Expected closing date*: {{6}}' + '\n' + '*Description*: {{7}}',
            'header': 'text',
            'sample_message': "Administrator,Planning and budget,Research and Development,22-07-13,Planning and Budgeting is an analytical application that helps you set top-down targets and generate a bottom-up budget, which is at the foundation of your organization's operations.",
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def website_signup_page_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'website_signup_page_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('res.users').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': False,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'You have successfully registered on our portal.' + '\n' + 'The connected email id is {{2}}',
            'header': 'text',
            'sample_message': "Administrator,admin@gmail.com",
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def send_pos_message_chat_api(self):
        whatsapp_templates_dict = {
            'name': 'send_pos_message_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('pos.order').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': False,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Your point of sale order *{{2}}* is placed.' + '\n' + 'Total amount: {{3}}' + '\n' + 'Here are the details of your order.' + '\n' + '{{4}}',
            'header': 'text',
            'sample_message': "Administrator,Shop/001,$219.08,*Product:* Office Lamp  *Qty:* 20.0 Units  *Unit Price:* 132.5  *Subtotal:* 2650.0",
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def account_invoice_payment_remainder(self):
        whatsapp_templates_dict = {
            'name': 'account_invoice_payment_remainder_' + self.sequence,
            'category': 'MARKETING',
            'model_id': self.env['ir.model']._get('account.move').id,
            'template_type': 'simple',
            'default_template': True,
            'send_template': False,
            'provider': 'whatsapp_chat_api',
            'body': 'Hello {{1}}' + '\n' + 'Your invoice {{2}} is pending.' + '\n' + 'Total Amount {{3}} and Due Amount {{4}}',
            'header': 'text',
            'sample_message': "Administrator,INV/2022/00001,$ 233.0,$ 150.0",
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def gupshup_create_missing_templates(self):
        self.gupshup_create_templates_for_sale_order()
        self.gupshup_create_templates_for_account_invoice()
        self.gupshup_create_templates_for_delivery_order()
        self.gupshup_create_templates_for_account_payment()
        self.gupshup_create_templates_for_purchase_order()
        self.gupshup_create_templates_for_project_task()
        self.gupshup_create_templates_for_crm_lead()
        self.website_signup_page_gupshup()
        self.send_pos_message_gupshup()
        self.gupshup_account_invoice_payment_remainder()

    def gupshup_create_templates_for_sale_order(self):
        self.sale_order_without_order_details_lines_signature_gupshup()
        self.sale_order_without_order_details_lines_with_signature_gupshup()
        self.sale_order_without_lines_signature_with_order_details_gupshup()
        self.sale_order_without_order_details_signature_with_lines_gupshup()
        self.sale_order_without_lines_with_signature_order_details_gupshup()
        self.sale_order_without_order_details_with_signature_lines_gupshup()
        self.sale_order_without_signature_with_order_details_lines_gupshup()
        self.sale_order_with_signature_order_details_lines_gupshup()

    def sale_order_without_order_details_lines_signature_gupshup(self):
        whatsapp_templates_dict = {
            'name': 'sale_order_without_order_details_lines_signature_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('sale.order').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'so_without_order_details_lines_signature',
            'body': 'Hello {{1}}' + '\n' + 'Please find attached the order form which will help you to get detailed information.',
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/S00014.pdf',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Please find attached the order form which will help you to get detailed information.',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def sale_order_without_order_details_lines_with_signature_gupshup(self):
        instance_signature = ''
        if self.signature:
            instance_signature = self.signature
        else:
            instance_signature = self.env.user.company_id.name

        whatsapp_templates_dict = {
            'name': 'sale_order_without_order_details_lines_with_signature_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('sale.order').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'so_without_order_details_lines_with_signature',
            'body': 'Hello {{1}}' + '\n' + 'Please find attached the order form which will help you to get detailed information.' + '\n\n' + '{{2}}',
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/S00014.pdf',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Please find attached the order form which will help you to get detailed information.' + '\n\n' + '---------------------------------' + '\n' '---------------------------------' + '\n' + instance_signature,
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def sale_order_without_lines_signature_with_order_details_gupshup(self):
        whatsapp_templates_dict = {
            'name': 'sale_order_without_lines_signature_with_order_details_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('sale.order').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'so_without_lines_signature_with_order_details',
            'body': 'Hello {{1}}' + '\n' + 'Your order {{2}}  is placed' + '\n' + 'Total Amount: {{3}}' + '\n' + 'Please find attached the order form which will help you to get detailed information.',
            'header': 'media_document',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Your order S00013  is placed' + '\n' + 'Total Amount: $ 3.00' + '\n' + 'Please find attached the order form which will help you to get detailed information.',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/S00014.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def sale_order_without_order_details_signature_with_lines_gupshup(self):
        whatsapp_templates_dict = {
            'name': 'sale_order_without_order_details_signature_with_lines_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('sale.order').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'so_without_order_details_signature_with_lines',
            'body': 'Hello {{1}}' + '\n' + 'Here are the details of your order.' + '\n' + '{{2}}' + '\nPlease find attached the order form which will help you to get detailed information.',
            'header': 'media_document',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Here are the details of your order.' + '\n' + '*Product:* Flash  *Qty:* 1.0 Units  *Unit Price:* 3.0  *Subtotal:* 3.0' + '\nPlease find attached the order form which will help you to get detailed information.',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/S00014.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def sale_order_without_lines_with_signature_order_details_gupshup(self):
        instance_signature = ''
        if self.signature:
            instance_signature = self.signature
        else:
            instance_signature = self.env.user.company_id.name
        whatsapp_templates_dict = {
            'name': 'sale_order_without_lines_with_signature_order_details_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('sale.order').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'so_without_lines_with_signature_order_details',
            'body': 'Hello {{1}}' + '\n' + 'Your order {{2}}  is placed' + '\n' + 'Total Amount: {{3}}' + '\nPlease find attached the order form which will help you to get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + '{{4}}',
            'header': 'media_document',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Your order S00013  is placed' + '\n' + 'Total Amount: $ 3.00' + '\nPlease find attached the order form which will help you to get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + instance_signature,
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/S00014.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def sale_order_without_order_details_with_signature_lines_gupshup(self):
        instance_signature = ''
        if self.signature:
            instance_signature = self.signature
        else:
            instance_signature = self.env.user.company_id.name
        whatsapp_templates_dict = {
            'name': 'sale_order_without_order_details_with_signature_lines_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('sale.order').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'body': 'Hello {{1}}' + '\n' + 'Here are the details of your order.' + '\n' + '{{2}}' + 'Please find attached the order form which will help you to get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' '{{3}}',
            'header': 'media_document',
            'gupshup_template_labels': 'so_without_order_details_with_signature_lines',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Here are the details of your order.' + '\n' + '*Product:* Flash  *Qty:* 1.0 Units  *Unit Price:* 3.0  *Subtotal:* 3.0' + 'Please find attached the order form which will help you to get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + instance_signature,
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/S00014.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def sale_order_without_signature_with_order_details_lines_gupshup(self):
        whatsapp_templates_dict = {
            'name': 'sale_order_without_signature_with_order_details_lines_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('sale.order').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'body': 'Hello {{1}}' + '\n' + 'Your order *{{2}}*  is placed' + '\n' + 'Total Amount: {{3}}' + '\nHere are the details of your order.' + '\n' + '{{4}}' + '\nPlease find attached the order form which will help you to get detailed information.',
            'header': 'media_document',
            'gupshup_template_labels': 'so_without_signature_with_order_details_lines',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Your order *S00013*  is placed' + '\n' + 'Total Amount: $ 3.00' + '\nHere are the details of your order.' + '\n' + '*Product:* Flash  *Qty:* 1.0 Units  *Unit Price:* 3.0  *Subtotal:* 3.0' + '\nPlease find attached the order form which will help you to get detailed information.',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/S00014.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def sale_order_with_signature_order_details_lines_gupshup(self):
        instance_signature = ''
        if self.signature:
            instance_signature = self.signature
        else:
            instance_signature = self.env.user.company_id.name
        whatsapp_templates_dict = {
            'name': 'sale_order_with_signature_order_details_lines_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('sale.order').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'so_with_signature_order_details_lines',
            'body': 'Hello {{1}}' + '\n' + 'Your order *{{2}}*  is placed' + '\n' + 'Total Amount: {{3}}' + '\nHere are the details of your order.' + '\n' + '{{4}}' + '\nPlease find attached the order form which will help you to get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + '{{5}}',
            'header': 'media_document',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Your order *S00013*  is placed' + '\n' + 'Total Amount: $ 3.00' + '\nHere are the details of your order.' + '\n' + '*Product:* Flash  *Qty:* 1.0 Units  *Unit Price:* 3.0  *Subtotal:* 3.0' + '\nPlease find attached the order form which will help you to get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + instance_signature,
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/S00014.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def gupshup_create_templates_for_account_invoice(self):
        self.account_invoice_without_invoice_details_lines_signature_gupshup()
        self.account_invoice_without_invoice_details_lines_with_signature_gupshup()
        self.account_invoice_without_lines_signature_with_invoice_details_gupshup()
        self.account_invoice_without_invoice_details_signature_with_lines_gupshup()
        self.account_invoice_without_lines_with_signature_invoice_details_gupshup()
        self.account_invoice_without_invoice_details_with_signature_lines_gupshup()
        self.account_invoice_without_signature_with_invoice_details_lines_gupshup()
        self.account_invoice_with_signature_invoice_details_lines_gupshup()

    def account_invoice_without_invoice_details_lines_signature_gupshup(self):
        whatsapp_templates_dict = {
            'name': 'account_invoice_without_invoice_details_lines_signature_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('account.move').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'invoice_without_invoice_details_lines_signature',
            'body': 'Hello {{1}}' + '\n' + 'Kindly search the invoice pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Kindly search the invoice pdf document which will help you to get detailed information.',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/INV00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def account_invoice_without_invoice_details_lines_with_signature_gupshup(self):
        instance_signature = ''
        if self.signature:
            instance_signature = self.signature
        else:
            instance_signature = self.env.user.company_id.name
        whatsapp_templates_dict = {
            'name': 'account_invoice_without_invoice_details_lines_with_signature_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('account.move').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'inv_without_invoice_details_lines_with_signature',
            'body': 'Hello {{1}}' + '\n' + 'Kindly search the invoice pdf document which will help you to get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + '{{2}}',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Kindly search the invoice pdf document which will help you to get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + instance_signature,
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/INV00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def account_invoice_without_lines_signature_with_invoice_details_gupshup(self):
        whatsapp_templates_dict = {
            'name': 'account_invoice_without_lines_signature_with_invoice_details_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('account.move').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'inv_without_lines_signature_with_invoice_details',
            'body': 'Hello {{1}}' + '\n' + 'Your {{2}} invoice is created' + '\n' + 'Total Amount: {{3}}' + '\nKindly search the invoice pdf document which will help you to get detailed information.',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Your INV/2022/00008 invoice is created' + '\n' + 'Total Amount: $ 3.00' + '\nKindly search the invoice pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/INV00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def account_invoice_without_invoice_details_signature_with_lines_gupshup(self):
        whatsapp_templates_dict = {
            'name': 'account_invoice_without_invoice_details_signature_with_lines_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('account.move').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'inv_without_invoice_details_signature_with_lines',
            'body': 'Hello {{1}}' + '\n' + 'Here are the details of your invoice.' + '\n' + '{{2}}' + '\nKindly search the invoice pdf document which will help you to get detailed information.',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Here are the details of your invoice.' + '\n' + '*Product:* Flash  *Qty:* 1.0 Units  *Unit Price:* 3.0  *Subtotal:* 3.0' + '\nKindly search the invoice pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/INV00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def account_invoice_without_lines_with_signature_invoice_details_gupshup(self):
        instance_signature = ''
        if self.signature:
            instance_signature = self.signature
        else:
            instance_signature = self.env.user.company_id.name
        whatsapp_templates_dict = {
            'name': 'account_invoice_without_lines_with_signature_invoice_details_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('account.move').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'inv_without_lines_with_signature_invoice_details',
            'body': 'Hello {{1}}' + '\n' + 'Your {{2}} invoice is created' + '\n' + 'Total amount: {{3}}' + '\nKindly search the invoice pdf document which will help you to get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + '{{4}}',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Your INV/2022/00008 invoice is created' + '\n' + 'Total amount: $ 3.00' + '\nKindly search the invoice pdf document which will help you to get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + instance_signature,
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/INV00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def account_invoice_without_invoice_details_with_signature_lines_gupshup(self):
        instance_signature = ''
        if self.signature:
            instance_signature = self.signature
        else:
            instance_signature = self.env.user.company_id.name
        whatsapp_templates_dict = {
            'name': 'account_invoice_without_invoice_details_with_signature_lines_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('account.move').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'body': 'Hello {{1}}' + '\n' + 'Here are the details of your invoice.' + '\n' + '{{2}}' + '\nKindly search the invoice pdf document which will help you to get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + '{{3}}',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Here are the details of your invoice.' + '\n' + '*Product:* Flash  *Qty:* 1.0 Units  *Unit Price:* 3.0  *Subtotal:* 3.0' + '\nKindly search the invoice pdf document which will help you to get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + instance_signature,
            'header': 'media_document',
            'gupshup_template_labels': 'inv_without_invoice_details_with_signature_lines',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/INV00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def account_invoice_without_signature_with_invoice_details_lines_gupshup(self):
        whatsapp_templates_dict = {
            'name': 'account_invoice_without_signature_with_invoice_details_lines_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('account.move').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'inv_without_signature_with_invoice_details_lines',
            'body': 'Hello {{1}}' + '\n' + 'Your {{2}} invoice is created' + '\n' + 'Total amount: {{3}}' + '\n' + 'Here are the details of your invoice.' + '\n' + '{{4}}' + '\nKindly search the invoice pdf document which will help you to get detailed information.',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Your INV/2022/00008 invoice is created' + '\n' + 'Total amount: $ 3.00' + '\n' + 'Here are the details of your invoice.' + '\n' + '*Product:* Flash  *Qty:* 1.0 Units  *Unit Price:* 3.0  *Subtotal:* 3.0' + '\nKindly search the invoice pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/INV00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def account_invoice_with_signature_invoice_details_lines_gupshup(self):
        instance_signature = ''
        if self.signature:
            instance_signature = self.signature
        else:
            instance_signature = self.env.user.company_id.name
        whatsapp_templates_dict = {
            'name': 'account_invoice_with_signature_invoice_details_lines_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('account.move').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'inv_with_signature_invoice_details_lines',
            'body': 'Hello {{1}}' + '\n' + 'Your {{2}} invoice is created' + '\n' + 'Total amount: {{3}}' + '\n' + 'Here are the details of your invoice.' + '\n' + '{{4}}' + '\nKindly search the invoice pdf document which will help you to get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + '{{5}}',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Your S00013 invoice is created' + '\n' + 'Total amount: $ 3.00' + '\n' + 'Here are the details of your invoice.' + '\n' + '*Product:* Flash  *Qty:* 1.0 Units  *Unit Price:* 3.0  *Subtotal:* 3.0' + '\nKindly search the invoice pdf document which will help you to get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + instance_signature,
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/INV00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def gupshup_create_templates_for_delivery_order(self):
        self.delivery_order_without_order_details_lines_signature_gupshup()
        self.delivery_order_without_order_details_lines_with_signature_gupshup()
        self.delivery_order_without_lines_signature_with_order_details_gupshup()
        self.delivery_order_without_order_details_signature_with_lines_gupshup()
        self.delivery_order_without_lines_with_signature_order_details_gupshup()
        self.delivery_order_without_order_details_with_signature_lines_gupshup()
        self.delivery_order_without_signature_with_order_details_lines_gupshup()
        self.delivery_order_with_signature_order_details_lines_gupshup()

    def delivery_order_without_order_details_lines_signature_gupshup(self):
        whatsapp_templates_dict = {
            'name': 'delivery_order_without_order_details_lines_signature_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('stock.picking').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'body': 'Hello {{1}}' + '\n' + 'See the delivery order pdf that will help you get detailed information.',
            'gupshup_template_labels': 'do_without_order_details_lines_signature',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/Delivery00007.pdf',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'See the delivery order pdf that will help you get detailed information.',
            'header': 'media_document',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def delivery_order_without_order_details_lines_with_signature_gupshup(self):
        instance_signature = ''
        if self.signature:
            instance_signature = self.signature
        else:
            instance_signature = self.env.user.company_id.name
        whatsapp_templates_dict = {
            'name': 'delivery_order_without_order_details_lines_with_signature_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('stock.picking').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'body': 'Hello {{1}}' + '\n' + 'See the delivery order pdf that will help you get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + '{{2}}',
            'gupshup_template_labels': 'do_without_order_details_lines_with_signature',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'See the delivery order pdf that will help you get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + instance_signature,
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/Delivery00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def delivery_order_without_lines_signature_with_order_details_gupshup(self):
        whatsapp_templates_dict = {
            'name': 'delivery_order_without_lines_signature_with_order_details_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('stock.picking').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'do_without_lines_signature_with_order_details',
            'body': 'Hello {{1}}' + '\n' + 'Here is your delivery order {{2}} (with reference: {{3}})' + '\n' + 'See the delivery order pdf that will help you get detailed information.',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Here is your delivery order WH/OUT/00012 (with reference: S00013)' + '\n' + 'See the delivery order pdf that will help you get detailed information.',
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/Delivery00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def delivery_order_without_order_details_signature_with_lines_gupshup(self):
        whatsapp_templates_dict = {
            'name': 'delivery_order_without_order_details_signature_with_lines_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('stock.picking').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'do_without_order_details_signature_with_lines',
            'body': 'Hello {{1}}' + '\n' + 'Here are the details of your delivery order.' + '\n' + '{{2}}' + '\n' + 'See the delivery order pdf that will help you get detailed information.',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Here are the details of your delivery order.' + '\n' + '*Product:* Flash  *Qty:* 1.0 Units  *Unit Price:* 3.0  *Subtotal:* 3.0' + '\n' + 'See the delivery order pdf that will help you get detailed information.',
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/Delivery00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def delivery_order_without_lines_with_signature_order_details_gupshup(self):
        instance_signature = ''
        if self.signature:
            instance_signature = self.signature
        else:
            instance_signature = self.env.user.company_id.name
        whatsapp_templates_dict = {
            'name': 'delivery_order_without_lines_with_signature_order_details_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('stock.picking').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'do_without_lines_with_signature_order_details',
            'body': 'Hello {{1}}' + '\n' + 'Here is your delivery order {{2}} (with reference: {{3}})' + '\n' + 'See the delivery order pdf that will help you get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + '{{4}}',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Here is your delivery order WH/OUT/00012 (with reference: S00013)' + '\n' + 'See the delivery order pdf that will help you get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + instance_signature,
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/Delivery00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def delivery_order_without_order_details_with_signature_lines_gupshup(self):
        instance_signature = ''
        if self.signature:
            instance_signature = self.signature
        else:
            instance_signature = self.env.user.company_id.name
        whatsapp_templates_dict = {
            'name': 'delivery_order_without_order_details_with_signature_lines_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('stock.picking').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'do_without_order_details_with_signature_lines',
            'body': 'Hello {{1}}' + '\n' + 'Here are the details of your delivery order.' + '\n' + '{{2}}' + '\nSee the delivery order pdf that will help you get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + '{{3}}',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Here are the details of your delivery order.' + '\n' + '*Product:* Flash  *Qty:* 1.0 Units  *Unit Price:* 3.0  *Subtotal:* 3.0' + '\nSee the delivery order pdf that will help you get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + instance_signature,
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/Delivery00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def delivery_order_without_signature_with_order_details_lines_gupshup(self):
        whatsapp_templates_dict = {
            'name': 'delivery_order_without_signature_with_order_details_lines_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('stock.picking').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'do_without_signature_with_order_details_lines',
            'body': 'Hello {{1}}' + '\n' + 'Here is your delivery order {{2}} (with reference: {{3}})' + '\n' + 'Here are the details of your delivery order.' + '\n' + '{{4}}' + '\nSee the delivery order pdf that will help you get detailed information.',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Here is your delivery order WH/OUT/00012 (with reference: S00013)' + '\n' + 'Here are the details of your delivery order.' + '\n' + '*Product:* Flash  *Qty:* 1.0 Units  *Unit Price:* 3.0  *Subtotal:* 3.0' + '\nSee the delivery order pdf that will help you get detailed information.',
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/Delivery00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def delivery_order_with_signature_order_details_lines_gupshup(self):
        instance_signature = ''
        if self.signature:
            instance_signature = self.signature
        else:
            instance_signature = self.env.user.company_id.name
        whatsapp_templates_dict = {
            'name': 'delivery_order_with_signature_order_details_lines_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('stock.picking').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'do_with_signature_order_details_lines',
            'body': 'Hello {{1}}' + '\n' + 'Here is your delivery order {{2}} (with reference: {{3}})' + '\n' + 'Here are the details of your delivery order.' + '\n' + '{{4}}' + '\nSee the delivery order pdf that will help you get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + '{{5}}',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Here is your delivery order WH/OUT/00012 (with reference: S00013)' + '\n' + 'Here are the details of your delivery order.' + '\n' + '*Product:* Flash  *Qty:* 1.0 Units  *Unit Price:* 3.0  *Subtotal:* 3.0' + '\nSee the delivery order pdf that will help you get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + instance_signature,
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/Delivery00007.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def gupshup_create_templates_for_account_payment(self):
        self.account_payment_without_payment_details_signature_gupshup()
        self.account_payment_without_payment_details_with_signature_gupshup()
        self.account_payment_without_signature_with_payment_details_gupshup()
        self.account_payment_with_signature_payment_details_gupshup()

    def account_payment_without_payment_details_signature_gupshup(self):
        whatsapp_templates_dict = {
            'name': 'account_payment_without_payment_details_signature_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('account.payment').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'payment_without_payment_details_signature',
            'body': 'Hello {{1}}' + '\n' + 'Kindly search the payment receipt pdf document which will help you to get detailed information.',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Kindly search the payment receipt pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/Payment Receipt.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def account_payment_without_payment_details_with_signature_gupshup(self):
        instance_signature = ''
        if self.signature:
            instance_signature = self.signature
        else:
            instance_signature = self.env.user.company_id.name
        whatsapp_templates_dict = {
            'name': 'account_payment_without_payment_details_with_signature_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('account.payment').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'payment_without_payment_details_with_signature',
            'body': 'Hello {{1}}' + '\n' + 'Kindly search the payment receipt pdf document which will help you to get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + '{{2}}',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Kindly search the payment receipt pdf document which will help you to get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + instance_signature,
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/Payment Receipt.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def account_payment_without_signature_with_payment_details_gupshup(self):
        whatsapp_templates_dict = {
            'name': 'account_payment_without_signature_with_payment_details_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('account.payment').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'payment_without_signature_with_payment_details',
            'body': 'Hello {{1}}' + '\n' + 'Payment of your account {{2}}' + '\n' + 'Total amount: {{3}}' + '\n' + 'The following are your payment details.' + '\n' + '*Payment Type:* {{4}}' + '\n' + '*Payment Journal:* {{5}}' + '\n' + '*Payment date:* {{6}}' + '\n' + '*Memo:* {{7}}' + '\n' + 'Kindly search the payment receipt pdf document which will help you to get detailed information.',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Payment of your account BNK1/2022/07/0002' + '\n' + 'Total amount: $198.95' + '\n' + 'The following are your payment details.' + '\n' + '*Payment Type:* inbound' + '\n' + '*Payment Journal:* Bank' + '\n' + '*Payment date:* 2022-07-12' + '\n' + '*Memo:* INV/2022/00002' + '\n' + 'Kindly search the payment receipt pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/Payment Receipt.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def account_payment_with_signature_payment_details_gupshup(self):
        instance_signature = ''
        if self.signature:
            instance_signature = self.signature
        else:
            instance_signature = self.env.user.company_id.name
        whatsapp_templates_dict = {
            'name': 'account_payment_with_signature_payment_details_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('account.payment').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'payment_with_signature_payment_details',
            'body': 'Hello {{1}}' + '\n' + 'Payment of your account {{2}}' + '\n' + 'Total amount: {{3}}' + '\n' + 'The following are your payment details.' + '\n' + '*Payment Type:* {{4}}' + '\n' + '*Payment Journal:* {{5}}' + '\n' + '*Payment date:* {{6}}' + '\n' + '*Memo:* {{7}}' + '\n' + 'Kindly search the payment receipt pdf document which will help you to get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + '{{8}}',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Payment of your account BNK1/2022/07/0002' + '\n' + 'Total amount: $198.95' + '\n' + 'The following are your payment details.' + '\n' + '*Payment Type:* inbound' + '\n' + '*Payment Journal:* Bank' + '\n' + '*Payment date:* 2022-07-12' + '\n' + '*Memo:* INV/2022/00002' + '\n' + 'Kindly search the payment receipt pdf document which will help you to get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + instance_signature,
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/Payment Receipt.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def gupshup_create_templates_for_purchase_order(self):
        self.purchase_order_without_order_details_lines_signature_gupshup()
        self.purchase_order_without_order_details_lines_with_signature_gupshup()
        self.purchase_order_without_lines_signature_with_order_details_gupshup()
        self.purchase_order_without_order_details_signature_with_lines_gupshup()
        self.purchase_order_without_lines_with_signature_order_details_gupshup()
        self.purchase_order_without_order_details_with_signature_lines_gupshup()
        self.purchase_order_without_signature_with_order_details_lines_gupshup()
        self.purchase_order_with_signature_order_details_lines_gupshup()

    def purchase_order_without_order_details_lines_signature_gupshup(self):
        whatsapp_templates_dict = {
            'name': 'purchase_order_without_order_details_lines_signature_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('purchase.order').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'po_without_order_details_lines_signature',
            'body': 'Hello {{1}}' + '\n' + 'Kindly search the purchase order pdf document which will help you to get detailed information.',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Kindly search the purchase order pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/P00002.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def purchase_order_without_order_details_lines_with_signature_gupshup(self):
        instance_signature = ''
        if self.signature:
            instance_signature = self.signature
        else:
            instance_signature = self.env.user.company_id.name

        whatsapp_templates_dict = {
            'name': 'purchase_order_without_order_details_lines_with_signature_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('purchase.order').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'po_without_order_details_lines_with_signature',
            'body': 'Hello {{1}}' + '\n' + 'Kindly search the purchase order pdf document which will help you to get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + '{{2}}',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Kindly search the purchase order pdf document which will help you to get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + instance_signature,
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/P00002.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def purchase_order_without_lines_signature_with_order_details_gupshup(self):
        whatsapp_templates_dict = {
            'name': 'purchase_order_without_lines_signature_with_order_details_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('purchase.order').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'po_without_lines_signature_with_order_details',
            'body': 'Hello {{1}}' + '\n' + 'Here is your Purchase order {{2}}' + '\n' + 'Total Amount: {{3}}' + '\n' + 'Kindly search the purchase order pdf document which will help you to get detailed information.',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Here is your Purchase order P00002' + '\n' + 'Total Amount: $ 347.50' + '\n' + 'Kindly search the purchase order pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/P00002.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def purchase_order_without_order_details_signature_with_lines_gupshup(self):
        whatsapp_templates_dict = {
            'name': 'purchase_order_without_order_details_signature_with_lines_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('purchase.order').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'po_without_order_details_signature_with_lines',
            'body': 'Hello {{1}}' + '\n' + 'Here are the details of your order.' + '\n' + '{{2}}' + '\n' + 'Kindly search the purchase order pdf document which will help you to get detailed information.',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Here are the details of your order.' + '\n' + '*Product:* Office Lamp  *Qty:* 20.0 Units  *Unit Price:* 132.5  *Subtotal:* 2650.0' + '\n' + 'Kindly search the purchase order pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/P00002.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def purchase_order_without_lines_with_signature_order_details_gupshup(self):
        instance_signature = ''
        if self.signature:
            instance_signature = self.signature
        else:
            instance_signature = self.env.user.company_id.name
        whatsapp_templates_dict = {
            'name': 'purchase_order_without_lines_with_signature_order_details_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('purchase.order').id,
            'template_type': 'simple',
            'default_template': True,
            'gupshup_template_labels': 'po_without_lines_with_signature_order_details',
            'provider': 'gupshup',
            'body': 'Hello {{1}}' + '\n' + 'Here is your Purchase order {{2}}' + '\n' + 'Total Amount: {{3}}' + '\n' + 'Kindly search the purchase order pdf document which will help you to get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + '{{4}}',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Here is your Purchase order P00002' + '\n' + 'Total Amount: $ 347.50' + '\n' + 'Kindly search the purchase order pdf document which will help you to get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + instance_signature,
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/P00002.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def purchase_order_without_order_details_with_signature_lines_gupshup(self):
        instance_signature = ''
        if self.signature:
            instance_signature = self.signature
        else:
            instance_signature = self.env.user.company_id.name
        whatsapp_templates_dict = {
            'name': 'purchase_order_without_order_details_with_signature_lines_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('purchase.order').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'po_without_order_details_with_signature_lines',
            'body': 'Hello {{1}}' + '\n' + 'Here are the details of your order.' + '\n' + '{{2}}' + '\n' + 'Kindly search the purchase order pdf document which will help you to get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + '{{3}}',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Here are the details of your order.' + '\n' + '*Product:* Flash  *Qty:* 1.0 Units  *Unit Price:* 3.0  *Subtotal:* 3.0' + '\n' + 'Kindly search the purchase order pdf document which will help you to get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + instance_signature,
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/P00002.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def purchase_order_without_signature_with_order_details_lines_gupshup(self):
        whatsapp_templates_dict = {
            'name': 'purchase_order_without_signature_with_order_details_lines_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('purchase.order').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'po_without_signature_with_order_details_lines',
            'body': 'Hello {{1}}' + '\n' + 'Here is your Purchase order {{2}}' + '\n' + 'Total Amount: {{3}}' + '\n' + 'Here are the details of your order.' + '\n' + '{{4}}' + '\n' + 'Kindly search the purchase order pdf document which will help you to get detailed information.',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Here is your Purchase order P00002' + '\n' + 'Total Amount: $ 347.50' + '\n' + 'Here are the details of your order.' + '\n' + '*Product:* Office Lamp  *Qty:* 20.0 Units  *Unit Price:* 132.5  *Subtotal:* 2650.0' + '\n' + 'Kindly search the purchase order pdf document which will help you to get detailed information.',
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/P00002.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def purchase_order_with_signature_order_details_lines_gupshup(self):
        instance_signature = ''
        if self.signature:
            instance_signature = self.signature
        else:
            instance_signature = self.env.user.company_id.name
        whatsapp_templates_dict = {
            'name': 'purchase_order_with_signature_order_details_lines_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('purchase.order').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'po_with_signature_order_details_lines',
            'body': 'Hello {{1}}' + '\n' + 'Here is your Purchase order *{{2}}*' + '\n' + 'Total Amount: {{3}}' + '\n' + 'Here are the details of your order.' + '\n' + '{{4}}' + '\n' + 'Kindly search the purchase order pdf document which will help you to get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + '{{5}}',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Here is your Purchase order *P00002*' + '\n' + 'Total Amount: $ 347.50' + '\n' + 'Here are the details of your order.' + '\n' + '*Product:* Office Lamp  *Qty:* 20.0 Units  *Unit Price:* 132.5  *Subtotal:* 2650.0' + '\n' + 'Kindly search the purchase order pdf document which will help you to get detailed information.' + '\n\n' + '-----------------------------------------------------------' + '\n' + instance_signature,
            'header': 'media_document',
            'sample_url': 'https://www.pragtech.co.in/pdf/whatsapp/P00002.pdf',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def gupshup_create_templates_for_project_task(self):
        self.project_task_without_signature_gupshup_template()
        self.project_task_with_signature_gupshup_template()

    def project_task_without_signature_gupshup_template(self):
        whatsapp_templates_dict = {
            'name': 'project_task_without_signature_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('project.task').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'project_task_without_signature',
            'body': 'Hello {{1}}' + '\n' + 'New task assigned to you.' + '\n' + '*Project*: {{2}}' + '\n' + '*Task name*: {{3}}' + '\n' + '*Deadline*: {{4}}' + '\n' + '*Description*: {{5}}',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'New task assigned to you.' + '\n' + '*Project*: Planning and budget' + '\n' + '*Task name*: Research and Development' + '\n' + '*Deadline*: 22-07-13' + '\n' + "*Description*: Planning and Budgeting is an analytical application that helps you set top-down targets and generate a bottom-up budget, which is at the foundation of your organization's operations.",
            'header': 'text',
            'interactive_actions': 'quick_replies',
            'quick_reply1': 'Done',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def project_task_with_signature_gupshup_template(self):
        instance_signature = ''
        if self.signature:
            instance_signature = self.signature
        else:
            instance_signature = self.env.user.company_id.name
        whatsapp_templates_dict = {
            'name': 'project_task_with_signature_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('project.task').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'project_task_with_signature',
            'body': 'Hello {{1}}' + '\n' + 'New task assigned to you.' + '\n' + '*Project*: {{2}}' + '\n' + '*Task name*: {{3}}' + '\n' + '*Deadline*: {{4}}' + '\n' + '*Description*: {{5}}' + '\n\n' + '-----------------------------------------------------------' + '\n' + '{{6}}',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'New task assigned to you.' + '\n' + '*Project*: Planning and budget' + '\n' + '*Task name*: Research and Development' + '\n' + '*Deadline*: 22-07-13' + '\n' + "*Description*: Planning and Budgeting is an analytical application that helps you set top-down targets and generate a bottom-up budget, which is at the foundation of your organization's operations." + '\n\n' + '-----------------------------------------------------------' + '\n' + instance_signature,
            'header': 'text',
            'interactive_actions': 'quick_replies',
            'quick_reply1': 'Done',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def gupshup_create_templates_for_crm_lead(self):
        self.crm_lead_without_signature_gupshup()
        self.crm_lead_with_signature_gupshup()

    def crm_lead_without_signature_gupshup(self):
        whatsapp_templates_dict = {
            'name': 'crm_lead_without_signature_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('crm.lead').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'lead_without_signature',
            'body': 'Hello {{1}}' + '\n' + 'New lead assigned to you.' + '\n' + '*Lead Name*: {{2}}' + '\n' + '*Customer*: {{3}}' + '\n' + '*Email*: {{4}}' + '\n' + '*Phone*: {{5}}' + '\n' + '*Expected closing date*: {{6}}' + '\n' + '*Description*: {{7}}',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'New lead assigned to you.' + '\n' + '*Lead Name*: Office Design Project' + '\n' + '*Customer*: Azure Interior' + '\n' + '*Email*: john.b@tech.info' + '\n' + '*Phone*: +1 312-349-2324' + '\n' + '*Expected closing date*: 2022-07-13' + '\n' + '*Description*: This new workspace between the East 4th-5th Ring Road of Beijing City aims to provide for its users with both a space to work in and also relax and feel close to nature.',
            'header': 'text',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def crm_lead_with_signature_gupshup(self):
        instance_signature = ''
        if self.signature:
            instance_signature = self.signature
        else:
            instance_signature = self.env.user.company_id.name
        whatsapp_templates_dict = {
            'name': 'crm_lead_with_signature_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('crm.lead').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'lead_with_signature',
            'body': 'Hello {{1}}' + '\n' + 'New lead assigned to you.' + '\n' + '*Lead Name*: {{2}}' + '\n' + '*Customer*: {{3}}' + '\n' + '*Email*: {{4}}' + '\n' + '*Phone*: {{5}}' + '\n' + '*Expected closing date*: {{6}}' + '\n' + '*Description*: {{7}}' + '\n\n' + '-----------------------------------------------------------' + '\n' + '{{8}}',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'New lead assigned to you.' + '\n' + '*Lead Name*: Office Design Project' + '\n' + '*Customer*: Azure Interior' + '\n' + '*Email*: john.b@tech.info' + '\n' + '*Phone*: +1 312-349-2324' + '\n' + '*Expected closing date*: 2022-07-13' + '\n' + '*Description*: This new workspace between the East 4th-5th Ring Road of Beijing City aims to provide for its users with both a space to work in and also relax and feel close to nature.' + '\n\n' + '-----------------------------------------------------------' + '\n' + instance_signature,
            'header': 'text',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def website_signup_page_gupshup(self):
        whatsapp_templates_dict = {
            'name': 'website_signup_page_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('res.users').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'website_signup_page',
            'body': 'Hello {{1}}' + '\n' + 'You have successfully registered on our portal.' + '\n' + 'The connected email id is {{2}}',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'You have successfully registered on our portal.' + '\n' + 'The connected email id is admin@gmail.com',
            'header': 'text',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def send_pos_message_gupshup(self):
        whatsapp_templates_dict = {
            'name': 'send_pos_message_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('pos.order').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'send_pos_message',
            'body': 'Hello {{1}}' + '\n' + 'Your point of sale order *{{2}}* is placed.' + '\n' + 'Total amount: {{3}}' + '\n' + 'Here are the details of your order.' + '\n' + '{{4}}',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Your point of sale order *Shop/001* is placed.' + '\n' + 'Total amount: $219.08' + '\n' + 'Here are the details of your order.' + '\n' + '*Product:* Office Lamp  *Qty:* 20.0 Units  *Unit Price:* 132.5  *Subtotal:* 2650.0',
            'header': 'text',
            'sample_message': "Administrator,Shop/001,$219.08,*Product:* Office Lamp  *Qty:* 20.0 Units  *Unit Price:* 132.5  *Subtotal:* 2650.0",
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))

    def gupshup_account_invoice_payment_remainder(self):
        whatsapp_templates_dict = {
            'name': 'account_invoice_payment_remainder_' + self.sequence,
            'category': 'TRANSACTIONAL',
            'model_id': self.env['ir.model']._get('account.move').id,
            'template_type': 'simple',
            'default_template': True,
            'provider': 'gupshup',
            'gupshup_template_labels': 'account_invoice_payment_remainder',
            'body': 'Hello {{1}}' + '\n' + 'Your invoice {{2}} is pending.' + '\n' + 'Total Amount {{3}} and Due Amount {{4}}',
            'gupshup_sample_message': 'Hello Administrator' + '\n' + 'Your invoice INV/2022/00001 is pending.' + '\n' + 'Total Amount $ 233.0 and Due Amount $ 150.0',
            'header': 'text',
            'whatsapp_instance_id': self.id
        }
        whatsapp_template_obj = self.env['whatsapp.templates']
        whatsapp_template_id = whatsapp_template_obj.sudo().search(
            [('name', '=', whatsapp_templates_dict.get('name')), ('whatsapp_instance_id', '=', self.id)], limit=1)
        if whatsapp_template_id:
            whatsapp_template_id.sudo().write(whatsapp_templates_dict)
            _logger.info("Whatsapp template is updated in odoo %s: ", str(whatsapp_template_id.id))
        else:
            whatsapp_template_id = whatsapp_template_obj.sudo().create(whatsapp_templates_dict)
            _logger.info("Whatsapp template is created in odoo %s: ", str(whatsapp_template_id.id))
