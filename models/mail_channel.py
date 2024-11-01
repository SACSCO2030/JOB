from odoo import api, fields, models, _
import requests
import json
import logging
import re

_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError


class mailChannel(models.Model):
    _inherit = 'mail.channel'

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, *, message_type='notification', **kwargs):
        message = super(mailChannel, self).message_post(**kwargs)
        if not self._context.get('from_odoobot'):
            whatsapp_instance_id = self.env['whatsapp.instance'].with_context({'skip_error': True}).get_whatsapp_instance()
            if whatsapp_instance_id:
                if whatsapp_instance_id.provider == 'whatsapp_chat_api':
                    self.chat_api_send_whatsapp_message(self.channel_partner_ids, kwargs, message, whatsapp_instance_id)
                elif whatsapp_instance_id.provider == 'gupshup':
                    self.gupshup_send_whatsapp_message(self.channel_partner_ids, kwargs, message, whatsapp_instance_id)
        return message

    def convert_email_from_to_name(self, str1):
        result = re.search('"(.*)"', str1)
        return result.group(1)

    def custom_html2plaintext(self, html):
        html = re.sub('<br\s*/?>', '\n', html)
        html = re.sub('<.*?>', ' ', html)
        return html

    def chat_api_send_whatsapp_message(self, partner_ids, kwargs, message_id, whatsapp_instance_id):
        if 'author_id' in kwargs and kwargs.get('author_id'):
            partner_id = self.env['res.partner'].search([('id', '=', kwargs.get('author_id'))])
            no_phone_partners = []
            if whatsapp_instance_id.whatsapp_endpoint and whatsapp_instance_id.whatsapp_token:
                status_url = whatsapp_instance_id.whatsapp_endpoint + '/status?token=' + whatsapp_instance_id.whatsapp_token
                status_response = requests.get(status_url)
                if status_response.status_code == 200 or status_response.status_code == 201:
                    json_response_status = json.loads(status_response.text)
                    if partner_id.country_id.phone_code and partner_id.mobile and json_response_status.get(
                            'status') == 'connected' and json_response_status.get('accountStatus') == 'authenticated':
                        whatsapp_msg_number = partner_id.mobile
                        whatsapp_msg_number_without_space = whatsapp_msg_number.replace(" ", "")
                        if '+' in whatsapp_msg_number_without_space:
                            whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace(
                                '+' + str(partner_id.country_id.phone_code), "")
                        else:
                            whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace(str(partner_id.country_id.phone_code), "")
                        if kwargs.get('body') and not kwargs.get('attachment_ids'):
                            html_to_plain_text = self.custom_html2plaintext(kwargs.get('body'))
                            number_with_code = str(partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code
                            if kwargs.get('email_from'):
                                if '<' in kwargs.get('email_from') and '>' in kwargs.get('email_from'):
                                    body_message = self.convert_email_from_to_name(kwargs.get('email_from')) + '' + str(self.id) + ': ' + html_to_plain_text
                                    self.send_whatsapp_message_from_chat_api(number_with_code, body_message, whatsapp_instance_id, partner_id, message_id)
                                else:
                                    body_message = kwargs.get('email_from') + '' + str(self.id) + ': ' + html_to_plain_text
                                    self.send_whatsapp_message_from_chat_api(number_with_code, body_message, whatsapp_instance_id, partner_id, message_id)
                            else:
                                self.send_whatsapp_message_from_chat_api(number_with_code, html_to_plain_text, whatsapp_instance_id, partner_id, message_id)

                        if kwargs.get('attachment_ids'):
                            caption = ''
                            caption = self.custom_html2plaintext(kwargs.get('body'))
                            if kwargs.get('email_from'):
                                if '<' in kwargs.get('email_from') and '>' in kwargs.get('email_from'):
                                    caption = self.convert_email_from_to_name(kwargs.get('email_from')) + '' + str(self.id) + ': ' + html_to_plain_text
                                    self.send_whatsapp_file_from_chat_api(number_with_code, caption, kwargs.get('attachment_ids'), whatsapp_instance_id, partner_id, message_id)
                                else:
                                    caption = kwargs.get('email_from') + '' + str(self.id) + ': ' + html_to_plain_text
                                    self.send_whatsapp_file_from_chat_api(number_with_code, caption, kwargs.get('attachment_ids'), whatsapp_instance_id, partner_id, message_id)
                            else:
                                self.send_whatsapp_file_from_chat_api(number_with_code, caption, kwargs.get('attachment_ids'), whatsapp_instance_id, partner_id, message_id)

                else:
                    raise UserError(_('Please authorize your mobile number with chat api'))

        else:
            no_phone_partners = []
            for partner_id in partner_ids:
                if whatsapp_instance_id.whatsapp_endpoint and whatsapp_instance_id.whatsapp_token:
                    status_url = whatsapp_instance_id.whatsapp_endpoint + '/status?token=' + whatsapp_instance_id.whatsapp_token
                    status_response = requests.get(status_url)
                    if status_response.status_code == 200 or status_response.status_code == 201:
                        json_response_status = json.loads(status_response.text)
                        if partner_id.country_id.phone_code and partner_id.mobile and json_response_status.get(
                                'status') == 'connected' and json_response_status.get('accountStatus') == 'authenticated':
                            whatsapp_msg_number = partner_id.mobile
                            whatsapp_msg_number_without_space = whatsapp_msg_number.replace(" ", "")
                            if '+' in whatsapp_msg_number_without_space:
                                whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace('+' + str(partner_id.country_id.phone_code),
                                                                                                             "")
                            else:
                                whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace(str(partner_id.country_id.phone_code), "")
                            html_to_plain_text = self.custom_html2plaintext(kwargs.get('body'))
                            number_with_code = str(partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code
                            if kwargs.get('body') and not kwargs.get('attachment_ids'):
                                if kwargs.get('email_from'):
                                    if '<' in kwargs.get('email_from') and '>' in kwargs.get('email_from'):
                                        body_message = self.convert_email_from_to_name(kwargs.get('email_from')) + '' + str(self.id) + ': ' + html_to_plain_text
                                        self.send_whatsapp_message_from_chat_api(number_with_code, body_message, whatsapp_instance_id, partner_id, message_id)
                                    else:
                                        body_message = kwargs.get('email_from') + '' + str(self.id) + ': ' + html_to_plain_text
                                        self.send_whatsapp_message_from_chat_api(number_with_code, body_message, whatsapp_instance_id, partner_id, message_id)
                                else:
                                    self.send_whatsapp_message_from_chat_api(number_with_code, html_to_plain_text, whatsapp_instance_id, partner_id, message_id)

                            if kwargs.get('attachment_ids'):
                                caption = ''
                                caption = self.custom_html2plaintext(kwargs.get('body'))
                                if kwargs.get('email_from'):
                                    if '<' in kwargs.get('email_from') and '>' in kwargs.get('email_from'):
                                        caption = self.convert_email_from_to_name(kwargs.get('email_from')) + '' + str(self.id) + ': ' + html_to_plain_text
                                        self.send_whatsapp_file_from_chat_api(number_with_code, caption, kwargs.get('attachment_ids'), whatsapp_instance_id, partner_id,
                                                                              message_id)
                                    else:
                                        caption = kwargs.get('email_from') + '' + str(self.id) + ': ' + html_to_plain_text
                                        self.send_whatsapp_file_from_chat_api(number_with_code, caption, kwargs.get('attachment_ids'), whatsapp_instance_id, partner_id,
                                                                              message_id)
                                else:
                                    self.send_whatsapp_file_from_chat_api(number_with_code, caption, kwargs.get('attachment_ids'), whatsapp_instance_id, partner_id, message_id)

                    else:
                        raise UserError(_('Please authorize your mobile number with chat api'))

    def send_whatsapp_message_from_chat_api(self, number_with_code, body_message, whatsapp_instance_id, partner_id, message_id):
        url = whatsapp_instance_id.whatsapp_endpoint + '/sendMessage?token=' + whatsapp_instance_id.whatsapp_token
        headers = {"Content-Type": "application/json"}
        tmp_dict = {
            "phone": number_with_code,
            "body": body_message
        }
        response = requests.post(url, json.dumps(tmp_dict), headers=headers)
        if response.status_code == 201 or response.status_code == 200:
            json_send_message_response = json.loads(response.text)
            if json_send_message_response.get('sent'):
                _logger.info("\nSend Message successfully")
                response_dict = response.json()
                self.env['whatsapp.msg'].with_context({'partner_id': partner_id.id}).create_whatsapp_message(number_with_code, tmp_dict.get('body'),
                                                                                                             response_dict.get('id'), response_dict.get('message'),
                                                                                                             "text",
                                                                                                             whatsapp_instance_id,
                                                                                                             'mail.channel', self)
                message_id.with_context({'from_odoobot': True}).write({'whatsapp_message_id': response_dict.get('id')})

    def send_whatsapp_file_from_chat_api(self, number_with_code, caption, attachment_ids,  whatsapp_instance_id, partner_id, message_id):
        url_send_file = whatsapp_instance_id.whatsapp_endpoint + '/sendFile?token=' + whatsapp_instance_id.whatsapp_token
        headers_send_file = {"Content-Type": "application/json"}
        ir_attachment_ids = self.env['ir.attachment'].sudo().search([('id', 'in', attachment_ids)])
        for attachment_id in ir_attachment_ids:
            encoded_file = str(attachment_id.datas)
            if attachment_id.mimetype:
                dict_send_file = {
                    "phone": number_with_code,
                    "body": "data:" + attachment_id.mimetype + ";base64," + encoded_file[2:-1],
                    "filename": attachment_id.name,
                }
                if caption:
                    dict_send_file['caption'] = caption
                response_send_file = requests.post(url_send_file, json.dumps(dict_send_file), headers=headers_send_file)
                if response_send_file.status_code == 201 or response_send_file.status_code == 200:
                    _logger.info("\nSend file attachment successfully")
                    json_send_file_response = json.loads(response_send_file.text)
                    if caption:
                        self.create_whatsapp_message_for_attachment_with_caption(number_with_code, attachment_id, caption, json_send_file_response.get('id'),
                                                                json_send_file_response.get('message'), attachment_id.mimetype,
                                                                whatsapp_instance_id, 'mail.channel', self)
                    else:
                        self.env['whatsapp.msg'].create_whatsapp_message_for_attachment(number_with_code, attachment_id, json_send_file_response.get('id'),
                                                                    json_send_file_response.get('message'), attachment_id.mimetype,
                                                                    whatsapp_instance_id, 'mail.channel', self)

    def create_whatsapp_message_for_attachment_with_caption(self, mobile_with_country, attachment_id, caption, message_id, chatId_message, type, whatsapp_instance_id, model, record):
        whatsapp_messages_dict = {
            'message_id': message_id,
            'name': caption,
            'message_body': caption,
            'fromMe': True,
            'to': mobile_with_country,
            'chatId': chatId_message[8:],
            'type': type,
            'chatName': chatId_message[8:-5],
            'time': fields.Datetime.now(),
            'state': 'sent',
            'whatsapp_instance_id': whatsapp_instance_id.id,
            'whatsapp_message_provider': whatsapp_instance_id.provider,
            'model': model,
            'res_id': record.id,
            'attachment_id': attachment_id.id,
        }
        if 'image' in attachment_id.mimetype:
            whatsapp_messages_dict['msg_image'] = attachment_id.datas
        if model == 'res.partner':
            whatsapp_messages_dict['partner_id'] = record.id
        else:
            if self._context.get('partner_id'):
                whatsapp_messages_dict['partner_id'] = self._context.get('partner_id')
        whatsapp_messages_id = self.env['whatsapp.messages'].sudo().create(whatsapp_messages_dict)
        _logger.info("Whatsapp message created in odoo %s: ", str(whatsapp_messages_id.id))


    def gupshup_send_whatsapp_message(self, partner_ids, kwargs, message_id, whatsapp_instance_id):
        return True
