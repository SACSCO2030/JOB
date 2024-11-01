# -*- coding: utf-8 -*-
import logging
import json
import requests
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import base64
import time
import re
import datetime

from odoo.tools.safe_eval import safe_eval, time
from requests.structures import CaseInsensitiveDict
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)
try:
    import phonenumbers
    from phonenumbers.phonenumberutil import region_code_for_country_code

    _sms_phonenumbers_lib_imported = True

except ImportError:
    _sms_phonenumbers_lib_imported = False
    _logger.info(
        "The `phonenumbers` Python module is not available. "
        "Phone number validation will be skipped. "
        "Try `pip3 install phonenumbers` to install it."
    )


class SendWAMessageResPartner(models.TransientModel):
    _name = 'whatsapp.msg.res.partner'
    _description = 'Send WhatsApp Message'

    def _default_unique_user(self):
        IPC = self.env['ir.config_parameter'].sudo()
        dbuuid = IPC.get_param('database.uuid')
        return dbuuid + '_' + str(self.env.uid)

    partner_ids = fields.Many2many('res.partner', 'whatsapp_msg_res_partner_res_partner_rel', 'wizard_id', 'partner_id', 'Recipients')
    message = fields.Text('Message', required=True)
    attachment_ids = fields.Many2many('ir.attachment', 'whatsapp_msg_res_partner_ir_attachments_rel', 'wizard_id', 'attachment_id', 'Attachments')
    unique_user = fields.Char(default=_default_unique_user)

    def _phone_get_country(self, partner):
        if 'country_id' in partner:
            return partner.country_id
        return self.env.user.company_id.country_id

    def _msg_sanitization(self, partner, field_name):
        number = partner[field_name]
        if number and _sms_phonenumbers_lib_imported:
            country = self._phone_get_country(partner)
            country_code = country.code if country else None
            try:
                phone_nbr = phonenumbers.parse(number, region=country_code, keep_raw_input=True)
            except phonenumbers.phonenumberutil.NumberParseException:
                return number
            if not phonenumbers.is_possible_number(phone_nbr) or not phonenumbers.is_valid_number(phone_nbr):
                return number
            phone_fmt = phonenumbers.PhoneNumberFormat.E164
            return phonenumbers.format_number(phone_nbr, phone_fmt)
        else:
            return number

    def _get_records(self, model):
        if self.env.context.get('active_ids'):
            records = model.browse(self.env.context.get('active_ids', []))
        else:
            records = model.browse(self.env.context.get('active_id', []))
        return records

    @api.model
    def default_get(self, fields):
        result = super(SendWAMessageResPartner, self).default_get(fields)
        active_model = self.env.context.get('active_model')
        res_id = self.env.context.get('active_id')
        rec = self.env[active_model].browse(res_id)
        Attachment = self.env['ir.attachment']
        res_name = 'Invoice_' + rec.number.replace('/', '_') if active_model == 'account.move' else rec.name.replace('/', '_')
        msg = result.get('message', '')
        result['message'] = msg
        if not self.env.context.get('default_recipients') and active_model:
            model = self.env[active_model]
            partners = self._get_records(model)
            phone_numbers = []
            no_phone_partners = []
            for partner in partners:
                number = self._msg_sanitization(partner, self.env.context.get('field_name') or 'mobile')
                if number:
                    phone_numbers.append(number)
                else:
                    no_phone_partners.append(partner.name)
            if len(partners) > 1:
                if no_phone_partners:
                    raise UserError(_('Missing mobile number for %s.') % ', '.join(no_phone_partners))
            result['partner_ids'] = [(6, 0, partners.ids)]

            result['message'] = msg
        return result

    def action_send_msg_res_partner(self):
        whatsapp_instance_id = self.env['whatsapp.instance'].get_whatsapp_instance()
        active_model = self.env.context.get('active_model')
        no_phone_partners = []
        if whatsapp_instance_id.provider == "whatsapp_chat_api":
            try:
                status_url = whatsapp_instance_id.whatsapp_endpoint + '/status?token=' + whatsapp_instance_id.whatsapp_token
                status_response = requests.get(status_url)
            except Exception as e_log:
                _logger.exception(e_log)
                raise UserError(_('Please add proper whatsapp endpoint or whatsapp token'))
            if status_response.status_code == 200 or status_response.status_code == 201:
                json_response_status = json.loads(status_response.text)
                if json_response_status.get('status') == 'connected' and json_response_status.get('accountStatus') == 'authenticated':
                    for res_partner_id in self.partner_ids:
                        if res_partner_id.country_id.phone_code and res_partner_id.mobile:
                            whatsapp_number = res_partner_id.mobile
                            whatsapp_msg_number_without_space = whatsapp_number.replace(" ", "")
                            if '+' in whatsapp_msg_number_without_space:
                                whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace(
                                    '+' + str(res_partner_id.country_id.phone_code), "")
                            else:
                                whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace(str(res_partner_id.country_id.phone_code), "")
                            url = whatsapp_instance_id.whatsapp_endpoint + '/sendMessage?token=' + whatsapp_instance_id.whatsapp_token
                            headers = {"Content-Type": "application/json"}
                            mobile_with_country = str(res_partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code
                            tmp_dict = {
                                "phone": str(res_partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
                                "body": self.message}
                            response = requests.post(url, json.dumps(tmp_dict), headers=headers)
                            if response.status_code == 201 or response.status_code == 200:
                                json_send_message_response = json.loads(response.text)
                                self.env['whatsapp.msg'].create_whatsapp_message(mobile_with_country, self.message, json_send_message_response.get('id'),
                                                                                 json_send_message_response.get('message'),
                                                                                 "text", whatsapp_instance_id, active_model, res_partner_id)
                                if not json_send_message_response.get('sent') and json_send_message_response.get(
                                        'error') and json_send_message_response.get('error').get(
                                    'message') == 'Recipient is not a valid WhatsApp user':
                                    no_phone_partners.append(res_partner_id.name)
                                elif json_send_message_response.get('sent'):
                                    _logger.info("\nSend Message successfully")
                                    if self.attachment_ids:
                                        for attachment in self.attachment_ids:
                                            with open("/tmp/" + attachment.name, 'wb') as tmp:
                                                encoded_file = str(attachment.datas)
                                                url_send_file = whatsapp_instance_id.whatsapp_endpoint + '/sendFile?token=' + whatsapp_instance_id.whatsapp_token
                                                headers_send_file = {"Content-Type": "application/json"}
                                                dict_send_file = {
                                                    "phone": str(res_partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
                                                    "body": "data:" + attachment.mimetype + ";base64," + encoded_file[2:-1],
                                                    "caption": attachment.name,
                                                    "filename": attachment.name
                                                }
                                                response_send_file = requests.post(url_send_file, json.dumps(dict_send_file),
                                                                                   headers=headers_send_file)
                                                if response_send_file.status_code == 201 or response_send_file.status_code == 200:
                                                    _logger.info("\nSend file attachment successfully11")
                                                    json_send_file_response = json.loads(response_send_file.text)
                                                    if json_send_file_response.get('sent'):
                                                        self.env['whatsapp.msg'].create_whatsapp_message_for_attachment(mobile_with_country, attachment,
                                                                                                                        json_send_file_response.get('id'),
                                                                                                                        json_send_file_response.get('message'), attachment.mimetype,
                                                                                                                        whatsapp_instance_id, active_model, res_partner_id)
                        else:
                            raise UserError(_('Please enter %s mobile number or select country', res_partner_id.name))
                    if len(no_phone_partners) >= 1:
                        raise UserError(_('Please add valid whatsapp number for %s customer') % ', '.join(no_phone_partners))
            else:
                raise UserError(_('Please authorize your mobile number with chat api'))

        elif whatsapp_instance_id.provider == "gupshup":
            for res_partner_id in self.partner_ids:
                if res_partner_id.country_id.phone_code and res_partner_id.mobile:
                    whatsapp_number = res_partner_id.mobile
                    whatsapp_msg_number_without_space = whatsapp_number.replace(" ", "")
                    whatsapp_msg_number_without_plus = whatsapp_msg_number_without_space.replace('+', '')
                    whatsapp_msg_number_without_code = ''
                    if '+' in whatsapp_msg_number_without_space:
                        whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace('+' + str(res_partner_id.country_id.phone_code), "")
                    else:
                        whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace(str(res_partner_id.country_id.phone_code), "")
                    whatsapp_msg_source_number = whatsapp_instance_id.gupshup_source_number
                    headers = {"Content-Type": "application/x-www-form-urlencoded", "apikey": whatsapp_instance_id.whatsapp_gupshup_api_key}
                    opt_in_list_url = "https://api.gupshup.io/sm/api/v1/users/" + whatsapp_instance_id.whatsapp_gupshup_app_name
                    opt_in_list_response = requests.get(opt_in_list_url, headers=headers)
                    registered_numbers = [user['phoneCode'] for user in opt_in_list_response.json().get('users')]
                    if whatsapp_msg_number_without_code not in registered_numbers:
                        opt_in_url = "https://api.gupshup.io/sm/api/v1/app/opt/in/" + whatsapp_instance_id.whatsapp_gupshup_app_name
                        opt_in_response = requests.post(opt_in_url, data={'user': whatsapp_msg_number_without_plus}, headers=headers)
                        if opt_in_response.status_code == 202:
                            _logger.info("\nOpt-in partner successfully")
                        template_id = self.gupshup_get_template_id(whatsapp_instance_id)
                        data = {
                            'source': whatsapp_msg_source_number,
                            'destination': whatsapp_msg_number_without_plus,
                            'template': json.dumps({
                                'id': template_id,
                                'params': [res_partner_id.name]
                            })
                        }
                        send_template_url = 'https://api.gupshup.io/sm/api/v1/template/msg'
                        tmpl_response = requests.post(send_template_url, headers=headers, data=data)
                        if tmpl_response.status_code in [200, 201, 202]:
                            _logger.info("\nInitial Template called successfully")
                    temp_data = {
                        'channel': 'whatsapp',
                        'source': whatsapp_msg_source_number,
                        'destination': whatsapp_msg_number_without_plus,
                        'message': json.dumps({
                            'type': 'text',
                            'text': self.message
                        })
                    }
                    url = 'https://api.gupshup.io/sm/api/v1/msg'
                    response = requests.post(url, headers=headers, data=temp_data)
                    if response.status_code in [202, 201, 200]:
                        _logger.info("\nSend Message successfully")
                        response_dict = response.json()
                        self.gupshup_create_whatsapp_message(whatsapp_msg_number_without_plus, self.message, response_dict.get('messageId'), whatsapp_instance_id, 'res.partner',
                                                             res_partner_id)
                        if self.attachment_ids:
                            for attachment in self.attachment_ids:
                                attachment_data = {
                                    'channel': 'whatsapp',
                                    'source': whatsapp_msg_source_number,
                                    'destination': whatsapp_msg_number_without_plus,
                                }
                                attachment_data = self.gupshup_create_attachment_dict_for_send_message(attachment, attachment_data)

                                response = requests.post(url, data=attachment_data, headers=headers)
                                if response.status_code in [202, 201, 200]:
                                    _logger.info("\nSend Attachment successfully")
                                    response_dict = response.json()
                                    self.gupshup_create_whatsapp_message_for_attachment(whatsapp_msg_number_without_plus, attachment, response_dict.get('messageId'),
                                                                                        attachment.mimetype,
                                                                                        whatsapp_instance_id, 'res.partner', res_partner_id)
        elif whatsapp_instance_id.provider == "meta":
            whatsapp_instance_id = self.env['whatsapp.instance'].get_whatsapp_instance()
            if whatsapp_instance_id.provider == "meta":
                if whatsapp_instance_id.whatsapp_meta_phone_number_id and whatsapp_instance_id.whatsapp_meta_api_token:
                    for res_partner_id in self.partner_ids:
                        if res_partner_id.country_id.phone_code and res_partner_id.mobile:
                            whatsapp_msg_number = res_partner_id.mobile
                            whatsapp_msg_number_without_space = whatsapp_msg_number.replace(" ", "")
                            whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace(
                                '+' + str(res_partner_id.country_id.phone_code), "")
                            recipient_phone_number = str(res_partner_id.country_id.phone_code) + whatsapp_msg_number_without_code
                            phone_id = whatsapp_instance_id.whatsapp_meta_phone_number_id
                            access_token = whatsapp_instance_id.whatsapp_meta_api_token
                            url = "https://graph.facebook.com/v16.0/{}/messages".format(phone_id)
                            req_headers = CaseInsensitiveDict()
                            req_headers["Authorization"] = "Bearer " + access_token
                            req_headers["Content-Type"] = "application/json"

                            data_json = {
                                "messaging_product": "whatsapp",
                                "recipient_type": "individual",
                                "to": recipient_phone_number,
                                "type": "text",
                                "text": {
                                    "body": self.message,
                                }
                            }
                            response = requests.post(url, headers=req_headers, json=data_json)
                            if response.status_code in [202, 201, 200]:
                                _logger.info("\nSend Message successfully")
                                response_dict = response.json()
                                self.meta_create_whatsapp_message(recipient_phone_number, self.message,response_dict.get('messages')[0].get('id'), whatsapp_instance_id, 'res.partner',
                                                             res_partner_id)
                        
                            if self.attachment_ids:
                                for attachment in self.attachment_ids:
                                    attachment_data = False
                                    data_json = {
                                        "messaging_product": "whatsapp",
                                        "recipient_type": "individual",
                                        "to": recipient_phone_number,
                                        "type": "image",
                                        "image": {
                                            "link": attachment.public_url,
                                            "caption": attachment.name
                                        },
                                    }
                                    if attachment.mimetype in ['application/pdf', 'application/zip', 'application/vnd.oasis.opendocument.text',
                                                                 'application/msword']:
                                        data_json = {
                                            "messaging_product": "whatsapp",
                                            "recipient_type": "individual",
                                            "to": recipient_phone_number,
                                            "type": "document",
                                            "document": {
                                                "link": attachment.public_url,
                                                "filename": attachment.name
                                            }
                                        }
                                    elif attachment.mimetype in ['audio/aac', 'audio/mp4', 'audio/amr',
                                                                 'audio/mpeg']:
                                        data_json = {
                                            "messaging_product": "whatsapp",
                                            "recipient_type": "individual",
                                            "to": recipient_phone_number,
                                            "type": "audio",
                                            "audio": {
                                                "link": attachment.public_url,
                                            }
                                        }
                                    elif attachment.mimetype in ['video/mp4', 'video/3gpp', 'video/mpeg']:
                                        data_json = {
                                            "messaging_product": "whatsapp",
                                            "recipient_type": "individual",
                                            "to": recipient_phone_number,
                                            "type": "video",
                                            "video": {
                                                "link": attachment.public_url,
                                            }
                                        }
                                    response = requests.post(url, headers=req_headers, data=json.dumps(data_json))
                                    if response.status_code in [202, 201, 200]:
                                        _logger.info("\nSend attachment successfully")
                                        response_dict = response.json()
                                        self.meta_create_whatsapp_message_for_attachment(recipient_phone_number, attachment, response_dict.get('messages')[0].get('id'),
                                                                                        attachment.mimetype,
                                                                                        whatsapp_instance_id, 'res.partner', res_partner_id)
                        else:
                            raise ValidationError(str(response.status_code)+" Error occured, pls try again")
                else:
                    raise ValidationError("No message author")


    def gupshup_create_attachment_dict_for_send_message(self, attachment_id, attachment_data):
        if 'image' in attachment_id.mimetype:
            attachment_data.update({
                'message': json.dumps({
                    'type': 'image',
                    'originalUrl': attachment_id.public_url,
                    'caption': attachment_id.name
                })
            })
        elif 'audio' in attachment_id.mimetype:
            attachment_data.update({
                'message': json.dumps({
                    'type': 'audio',
                    'url': attachment_id.public_url,
                })
            })
        elif 'video' in attachment_id.mimetype:
            attachment_data.update({
                'message': json.dumps({
                    'type': 'video',
                    'url': attachment_id.public_url,
                    'caption': attachment_id.name
                })
            })
        else:
            attachment_data.update({
                'message': json.dumps({
                    'type': 'file',
                    'url': attachment_id.public_url,
                    'filename': attachment_id.name
                })
            })
        return attachment_data

    def gupshup_get_template_id(self, whatsapp_instance_id):
        response = requests.get('https://api.gupshup.io/sm/api/v1/template/list/' + str(whatsapp_instance_id.whatsapp_gupshup_app_name),
                                headers={"apikey": whatsapp_instance_id.whatsapp_gupshup_api_key})
        if response.status_code in [202, 201, 200]:
            json_response = json.loads(response.text)
            template_id = json_response.get('templates')[0].get('id')

            return template_id

    def gupshup_create_whatsapp_message(self, mobile_with_country, message, message_id, whatsapp_instance_id, model, record, attachment_id=False):
        whatsapp_messages_dict = {
            'message_id': message_id,
            'name': message,
            'message_body': message,
            'fromMe': True,
            'to': mobile_with_country,
            'type': type,
            'time': fields.Datetime.now(),
            'state': 'sent',
            'whatsapp_instance_id': whatsapp_instance_id.id,
            'whatsapp_message_provider': whatsapp_instance_id.provider,
            'model': model,
            'res_id': record.id,
            'senderName': whatsapp_instance_id.gupshup_source_number,
            'chatName': mobile_with_country,
        }
        if attachment_id:
            whatsapp_messages_dict['attachment_id'] = attachment_id.id
        if model == 'res.partner':
            whatsapp_messages_dict['partner_id'] = record.id
        else:
            if self._context.get('partner_id'):
                whatsapp_messages_dict['partner_id'] = self._context.get('partner_id')
            elif not model == 'mail.channel' and not model == 'odoo.group' and not model == 'whatsapp.marketing' and not self.env.context.get(
                    'skip_partner') and not model == 'pos.order':
                if record.partner_id:
                    whatsapp_messages_dict['partner_id'] = record.partner_id.id
        whatsapp_messages_id = self.env['whatsapp.messages'].sudo().create(whatsapp_messages_dict)
        _logger.info("Whatsapp message created in odoo from gupshup %s: ", str(whatsapp_messages_id.id))

    def gupshup_create_whatsapp_message_for_attachment(self, mobile_with_country, attachment_id, message_id, type, whatsapp_instance_id, model, record):
        whatsapp_messages_dict = {
            'message_id': message_id,
            'name': attachment_id.name,
            'message_body': attachment_id.name,
            'fromMe': True,
            'to': mobile_with_country,
            'type': type,
            'time': fields.Datetime.now(),
            'state': 'sent',
            'whatsapp_instance_id': whatsapp_instance_id.id,
            'whatsapp_message_provider': whatsapp_instance_id.provider,
            'model': model,
            'res_id': record.id,
            'attachment_id': attachment_id.id,
            'senderName': whatsapp_instance_id.gupshup_source_number,
            'chatName': mobile_with_country,
        }
        if 'image' in attachment_id.mimetype:
            whatsapp_messages_dict['msg_image'] = attachment_id.datas
        if model == 'res.partner':
            whatsapp_messages_dict['partner_id'] = record.id
        else:
            if self._context.get('partner_id'):
                whatsapp_messages_dict['partner_id'] = self._context.get('partner_id')
            elif not model == 'mail.channel' and not model == 'odoo.group' and not model == 'whatsapp.marketing' and not self.env.context.get('skip_partner'):
                if record.partner_id:
                    whatsapp_messages_dict['partner_id'] = record.partner_id.id
        whatsapp_messages_id = self.env['whatsapp.messages'].sudo().create(whatsapp_messages_dict)
        _logger.info("Whatsapp message created in odoo from gupshup %s: ", str(whatsapp_messages_id.id))

    def meta_create_whatsapp_message(self, mobile_with_country, message, message_id, whatsapp_instance_id, model, record, attachment_id=False):
        whatsapp_messages_dict = {
            'message_id': message_id,
            'name': message,
            'message_body': message,
            'fromMe': True,
            'to': mobile_with_country,
            'type': type,
            'time': fields.Datetime.now(),
            'state': 'sent',
            'whatsapp_instance_id': whatsapp_instance_id.id,
            'whatsapp_message_provider': whatsapp_instance_id.provider,
            'model': model,
            'res_id': record.id,
            'senderName': whatsapp_instance_id.whatsapp_meta_phone_number_id,
            'chatName': mobile_with_country,
        }
        if attachment_id:
            whatsapp_messages_dict['attachment_id'] = attachment_id.id
        if model == 'res.partner':
            whatsapp_messages_dict['partner_id'] = record.id
        else:
            if self._context.get('partner_id'):
                whatsapp_messages_dict['partner_id'] = self._context.get('partner_id')
            elif not model == 'mail.channel' and not model == 'odoo.group' and not model == 'whatsapp.marketing' and not self.env.context.get(
                    'skip_partner') and not model == 'pos.order':
                if record.partner_id:
                    whatsapp_messages_dict['partner_id'] = record.partner_id.id
        whatsapp_messages_id = self.env['whatsapp.messages'].sudo().create(whatsapp_messages_dict)
        _logger.info("Whatsapp message created in odoo from meta %s: ", str(whatsapp_messages_id.id))


    def meta_create_whatsapp_message_for_attachment(self, mobile_with_country, attachment_id, message_id, type, whatsapp_instance_id, model, record):
        whatsapp_messages_dict = {
            'message_id': message_id,
            'name': attachment_id.name,
            'message_body': attachment_id.name,
            'fromMe': True,
            'to': mobile_with_country,
            'type': type,
            'time': fields.Datetime.now(),
            'state': 'sent',
            'whatsapp_instance_id': whatsapp_instance_id.id,
            'whatsapp_message_provider': whatsapp_instance_id.provider,
            'model': model,
            'res_id': record.id,
            'attachment_id': attachment_id.id,
            'senderName': whatsapp_instance_id.whatsapp_meta_phone_number_id,
            'chatName': mobile_with_country,
        }
        if 'image' in attachment_id.mimetype:
            whatsapp_messages_dict['msg_image'] = attachment_id.datas
        if model == 'res.partner':
            whatsapp_messages_dict['partner_id'] = record.id
        else:
            if self._context.get('partner_id'):
                whatsapp_messages_dict['partner_id'] = self._context.get('partner_id')
            elif not model == 'mail.channel' and not model == 'odoo.group' and not model == 'whatsapp.marketing' and not self.env.context.get('skip_partner'):
                if record.partner_id:
                    whatsapp_messages_dict['partner_id'] = record.partner_id.id
        whatsapp_messages_id = self.env['whatsapp.messages'].sudo().create(whatsapp_messages_dict)
        _logger.info("Whatsapp message created in odoo from gupshup %s: ", str(whatsapp_messages_id.id))



class SendWAMessageSendResPartner(models.TransientModel):
    _name = 'whatsapp.msg.send.partner'
    _description = 'Send WhatsApp Message'

    def _default_unique_user(self):
        IPC = self.env['ir.config_parameter'].sudo()
        dbuuid = IPC.get_param('database.uuid')
        return dbuuid + '_' + str(self.env.uid)

    partner_ids = fields.Many2many('res.partner', 'whatsapp_msg_send_partner_res_partner_rel', 'wizard_id', 'partner_id', 'Recipients')
    message = fields.Text('Message', required=True)
    attachment_ids = fields.Many2many('ir.attachment', 'whatsapp_msg_send_partner_ir_attachments_rel', 'wizard_id', 'attachment_id', 'Attachments')
    unique_user = fields.Char(default=_default_unique_user)

    def _phone_get_country(self, partner):
        if 'country_id' in partner:
            return partner.country_id
        return self.env.user.company_id.country_id

    def _msg_sanitization(self, partner, field_name):
        number = partner[field_name]
        if number and _sms_phonenumbers_lib_imported:
            country = self._phone_get_country(partner)
            country_code = country.code if country else None
            try:
                phone_nbr = phonenumbers.parse(number, region=country_code, keep_raw_input=True)
            except phonenumbers.phonenumberutil.NumberParseException:
                return number
            if not phonenumbers.is_possible_number(phone_nbr) or not phonenumbers.is_valid_number(phone_nbr):
                return number
            phone_fmt = phonenumbers.PhoneNumberFormat.E164
            return phonenumbers.format_number(phone_nbr, phone_fmt)
        else:
            return number

    def _get_records(self, model):
        if self.env.context.get('active_domain'):
            records = model.search(self.env.context.get('active_domain'))
        elif self.env.context.get('active_ids'):
            records = model.browse(self.env.context.get('active_ids', []))
        else:
            records = model.browse(self.env.context.get('active_id', []))
        return records

    @api.model
    def default_get(self, fields):
        result = super(SendWAMessageSendResPartner, self).default_get(fields)
        active_model = self.env.context.get('active_model')
        res_id = self.env.context.get('active_id')
        if res_id:
            rec = self.env[active_model].browse(res_id)
            Attachment = self.env['ir.attachment']
            res_name = 'Invoice_' + rec.number.replace('/', '_') if active_model == 'account.move' else rec.name.replace('/', '_')
            msg = result.get('message', '')
            result['message'] = msg

            if not self.env.context.get('default_recipients') and active_model:
                model = self.env[active_model]
                partners = self._get_records(model)
                phone_numbers = []
                no_phone_partners = []

                for partner in partners:
                    number = self._msg_sanitization(partner, self.env.context.get('field_name') or 'mobile')
                    if number:
                        phone_numbers.append(number)
                    else:
                        no_phone_partners.append(partner.name)
                if len(partners) > 1:
                    if no_phone_partners:
                        raise UserError(_('Missing mobile number for %s.') % ', '.join(no_phone_partners))
                result['partner_ids'] = [(6, 0, partners.ids)]
                result['message'] = msg
        return result

    def action_send_msg_res_partner(self):
        whatsapp_instance_id = self.env['whatsapp.instance'].get_whatsapp_instance()
        param = self.env['res.config.settings'].sudo().get_values()
        active_id = self.partner_ids
        active_model = 'res.partner'
        phone_numbers = []
        no_phone_partners = []
        if whatsapp_instance_id.provider == "whatsapp_chat_api":
            try:
                status_url = whatsapp_instance_id.whatsapp_endpoint + '/status?token=' + whatsapp_instance_id.whatsapp_token
                status_response = requests.get(status_url)
            except Exception as e_log:
                _logger.exception(e_log)
                raise UserError(_('Please add proper whatsapp endpoint or whatsapp token'))
            if status_response.status_code == 200 or status_response.status_code == 201:
                json_response_status = json.loads(status_response.text)
                if active_model == 'res.partner' and json_response_status.get('status') == 'connected' and json_response_status.get('accountStatus') == 'authenticated':
                    for res_partner_id in self.partner_ids:
                        number = str(res_partner_id.country_id.phone_code) + res_partner_id.mobile
                        if res_partner_id.country_id.phone_code and res_partner_id.mobile:
                            whatsapp_number = res_partner_id.mobile
                            whatsapp_msg_number_without_space = whatsapp_number.replace(" ", "")
                            if '+' in whatsapp_msg_number_without_space:
                                whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace('+' + str(res_partner_id.country_id.phone_code), "")
                            else:
                                whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace(str(res_partner_id.country_id.phone_code), "")

                            url = whatsapp_instance_id.whatsapp_endpoint + '/sendMessage?token=' + whatsapp_instance_id.whatsapp_token
                            headers = {"Content-Type": "application/json"}
                            mobile_with_country = str(res_partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code
                            tmp_dict = {
                                "phone": str(res_partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
                                "body": self.message}
                            response = requests.post(url, json.dumps(tmp_dict), headers=headers)
                            if response.status_code == 201 or response.status_code == 200:
                                json_send_message_response = json.loads(response.text)
                                if not json_send_message_response.get('sent') and json_send_message_response.get('error') and json_send_message_response.get('error').get(
                                        'message') == 'Recipient is not a valid WhatsApp user':
                                    no_phone_partners.append(res_partner_id.name)
                                elif json_send_message_response.get('sent'):
                                    _logger.info("\nSend Message successfully")
                                    self.env['whatsapp.msg'].create_whatsapp_message(mobile_with_country, self.message, json_send_message_response.get('id'),
                                                                                     json_send_message_response.get('message'),
                                                                                     "text", whatsapp_instance_id, active_model, res_partner_id)
                                    if self.attachment_ids:
                                        for attachment in self.attachment_ids:
                                            with open("/tmp/" + attachment.name, 'wb') as tmp:
                                                encoded_file = str(attachment.datas)
                                                url_send_file = whatsapp_instance_id.whatsapp_endpoint + '/sendFile?token=' + whatsapp_instance_id.whatsapp_token
                                                headers_send_file = {"Content-Type": "application/json"}
                                                dict_send_file = {
                                                    "phone": str(res_partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
                                                    "body": "data:" + attachment.mimetype + ";base64," + encoded_file[2:-1],
                                                    "caption": attachment.name,
                                                    "filename": attachment.name
                                                }
                                                response_send_file = requests.post(url_send_file, json.dumps(dict_send_file), headers=headers_send_file)
                                                if response_send_file.status_code == 201 or response_send_file.status_code == 200:
                                                    _logger.info("\nSend file attachment successfully11")
                                                    json_send_file_response = json.loads(response_send_file.text)
                                                    if json_send_file_response.get('sent'):
                                                        self.env['whatsapp.msg'].create_whatsapp_message_for_attachment(mobile_with_country, attachment,
                                                                                                                        json_send_file_response.get('id'),
                                                                                                                        json_send_file_response.get('message'), attachment.mimetype,
                                                                                                                        whatsapp_instance_id, active_model, res_partner_id)
                        else:
                            raise UserError(_('Please enter %s mobile number or select country', res_partner_id))
                    if len(no_phone_partners) >= 1:
                        raise UserError(
                            _('Please add valid whatsapp number for %s customer') % ', '.join(no_phone_partners))
            else:
                raise UserError(_('Please authorize your mobile number with chat api'))

        elif whatsapp_instance_id.provider == "gupshup":
            for res_partner_id in self.partner_ids:
                if res_partner_id.country_id.phone_code and res_partner_id.mobile:
                    whatsapp_number = res_partner_id.mobile
                    whatsapp_msg_number_without_space = whatsapp_number.replace(" ", "")
                    whatsapp_msg_number_without_plus = whatsapp_msg_number_without_space.replace('+', '')
                    if '+' in whatsapp_msg_number_without_space:
                        whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace('+' + str(res_partner_id.country_id.phone_code), "")
                    else:
                        whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace(str(res_partner_id.country_id.phone_code), "")
                    whatsapp_msg_source_number = whatsapp_instance_id.gupshup_source_number
                    headers = {"Content-Type": "application/x-www-form-urlencoded", "apikey": whatsapp_instance_id.whatsapp_gupshup_api_key}
                    opt_in_list_url = "https://api.gupshup.io/sm/api/v1/users/" + whatsapp_instance_id.whatsapp_gupshup_app_name
                    opt_in_list_response = requests.get(opt_in_list_url, headers=headers)
                    registered_numbers = [user['phoneCode'] for user in opt_in_list_response.json().get('users')]
                    if whatsapp_msg_number_without_code not in registered_numbers:
                        opt_in_url = "https://api.gupshup.io/sm/api/v1/app/opt/in/" + whatsapp_instance_id.whatsapp_gupshup_app_name
                        opt_in_response = requests.post(opt_in_url, data={'user': whatsapp_msg_number_without_plus}, headers=headers)
                        if opt_in_response.status_code == 202:
                            _logger.info("\nOpt-in partner successfully")
                        data = {
                            'source': whatsapp_msg_source_number,
                            'destination': whatsapp_msg_number_without_plus,
                            'template': json.dumps({
                                'id': 'f186753c-3989-45b0-af9b-f2861dc2d3e3',
                                'params': [res_partner_id.name]
                            })
                        }
                        send_template_url = 'https://api.gupshup.io/sm/api/v1/template/msg'
                        tmpl_response = requests.post(send_template_url, headers=headers, data=data)
                        if tmpl_response.status_code in [200, 201, 202]:
                            _logger.info("\nInitial Template called successfully")

                    temp_data = {
                        'channel': 'whatsapp',
                        'source': whatsapp_msg_source_number,
                        'destination': whatsapp_msg_number_without_plus,
                        'message': json.dumps({
                            'type': 'text',
                            'text': self.message
                        })
                    }
                    url = 'https://api.gupshup.io/sm/api/v1/msg'
                    response = requests.post(url, headers=headers, data=temp_data)
                    if response.status_code in [202, 201, 200]:
                        _logger.info("\nSend Message successfully")
                        whatsapp_msg = self.env['whatsapp.messages']
                        vals = {
                            'message_body': self.message,
                            'senderName': whatsapp_instance_id.whatsapp_gupshup_app_name,
                            'state': 'sent',
                            'to': whatsapp_msg_source_number,
                            'partner_id': res_partner_id.id,
                            'time': fields.Datetime.now()
                        }
                        whatsapp_msg_id = whatsapp_msg.sudo().create(vals)
                        if whatsapp_msg_id:
                            _logger.info("\nWhatsApp message Created")

                        if self.attachment_ids:
                            for attachment in self.attachment_ids:
                                attachment_data = False
                                if attachment.mimetype in ['image/jpeg', 'image/png']:
                                    attachment_data = {
                                        'channel': 'whatsapp',
                                        'source': whatsapp_msg_source_number,
                                        'destination': whatsapp_msg_number_without_plus,
                                        'message': json.dumps({
                                            'type': 'image',
                                            'originalUrl': attachment.public_url,
                                            'caption': attachment.name
                                        })
                                    }
                                elif attachment.mimetype in ['audio/aac', 'audio/mp4', 'audio/amr', 'audio/mpeg']:
                                    attachment_data = {
                                        'channel': 'whatsapp',
                                        'source': whatsapp_msg_source_number,
                                        'destination': whatsapp_msg_number_without_plus,
                                        'message': json.dumps({
                                            'type': 'audio',
                                            'url': attachment.public_url,
                                        })
                                    }
                                elif attachment.mimetype in ['video/mp4', 'video/3gpp']:
                                    attachment_data = {
                                        'channel': 'whatsapp',
                                        'source': whatsapp_msg_source_number,
                                        'destination': whatsapp_msg_number_without_plus,
                                        'message': json.dumps({
                                            'type': 'video',
                                            'url': attachment.public_url,
                                            'caption': attachment.name
                                        })
                                    }
                                else:
                                    attachment_data = {
                                        'channel': 'whatsapp',
                                        'source': whatsapp_msg_source_number,
                                        'destination': whatsapp_msg_number_without_plus,
                                        'message': json.dumps({
                                            'type': 'file',
                                            'url': attachment.public_url,
                                            'filename': attachment.name
                                        })
                                    }
                                attachment_url = 'https://api.gupshup.io/sm/api/v1/msg'
                                response = requests.post(attachment_url, headers=headers, data=attachment_data)
                                if response.status_code in [202, 201, 200]:
                                    _logger.info("\nSend Attachment successfully")
                                    res_update_whatsapp_msg = whatsapp_msg_id.sudo().write({'attachment_id': attachment.id})
                                    if res_update_whatsapp_msg:
                                        _logger.info("\nWhats app message attachment added")
        elif whatsapp_instance_id.provider == "meta":
            whatsapp_instance_id = self.env['whatsapp.instance'].get_whatsapp_instance()
            if whatsapp_instance_id.provider == "meta":
                if whatsapp_instance_id.whatsapp_meta_phone_number_id and whatsapp_instance_id.whatsapp_meta_api_token:
                    for res_partner_id in self.partner_ids:
                        if res_partner_id.country_id.phone_code and res_partner_id.mobile:
                            whatsapp_msg_number = res_partner_id.mobile
                            whatsapp_msg_number_without_space = whatsapp_msg_number.replace(" ", "")
                            whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace(
                                '+' + str(res_partner_id.country_id.phone_code), "")
                            recipient_phone_number = str(res_partner_id.country_id.phone_code) + whatsapp_msg_number_without_code

                            phone_id = whatsapp_instance_id.whatsapp_meta_phone_number_id
                            access_token = whatsapp_instance_id.whatsapp_meta_api_token
                            url = "https://graph.facebook.com/v16.0/{}/messages".format(phone_id)
                            req_headers = CaseInsensitiveDict()
                            req_headers["Authorization"] = "Bearer " + access_token
                            req_headers["Content-Type"] = "application/json"

                            data_json = {
                                "messaging_product": "whatsapp",
                                "recipient_type": "individual",
                                "to": recipient_phone_number,
                                "type": "text",
                                "text": {
                                    "body": self.message,
                                }
                            }
                            response = requests.post(url, headers=req_headers, json=data_json)
                            if response.status_code in [202, 201, 200]:
                                _logger.info("\nSend Message successfully")
                            if self.attachment_ids:
                                for attachment in self.attachment_ids:
                                    attachment_data = False
                                    data_json = {
                                        "messaging_product": "whatsapp",
                                        "recipient_type": "individual",
                                        "to": recipient_phone_number,
                                        "type": "image",
                                        "image": {
                                            "link": attachment.public_url,
                                            "caption": attachment.name
                                        },
                                    }
                                    if attachment.mimetype in ['application/pdf', 'application/zip', 'application/vnd.oasis.opendocument.text',
                                                                 'application/msword']:
                                        data_json = {
                                            "messaging_product": "whatsapp",
                                            "recipient_type": "individual",
                                            "to": recipient_phone_number,
                                            "type": "document",
                                            "document": {
                                                "link": attachment.public_url,
                                                "filename": attachment.name
                                            }
                                        }
                                    elif attachment.mimetype in ['audio/aac', 'audio/mp4', 'audio/amr',
                                                                 'audio/mpeg']:
                                        data_json = {
                                            "messaging_product": "whatsapp",
                                            "recipient_type": "individual",
                                            "to": recipient_phone_number,
                                            "type": "audio",
                                            "audio": {
                                                "link": attachment.public_url,
                                            }
                                        }
                                    elif attachment.mimetype in ['video/mp4', 'video/3gpp', 'video/mpeg']:
                                        data_json = {
                                            "messaging_product": "whatsapp",
                                            "recipient_type": "individual",
                                            "to": recipient_phone_number,
                                            "type": "video",
                                            "video": {
                                                "link": attachment.public_url,
                                            }
                                        }
                                    response = requests.post(url, headers=req_headers, data=json.dumps(data_json))
                                    if response.status_code in [202, 201, 200]:
                                        _logger.info("\nSend attachment successfully")
                        else:
                            raise ValidationError(str(response.status_code)+" Error occured, pls try again")

class SendWAMessage(models.TransientModel):
    _name = 'whatsapp.msg'
    _description = 'Send WhatsApp Message'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _default_unique_user(self):
        IPC = self.env['ir.config_parameter'].sudo()
        dbuuid = IPC.get_param('database.uuid')
        return dbuuid + '_' + str(self.env.uid)

    partner_ids = fields.Many2many('res.partner', 'whatsapp_msg_res_partner_rel', 'wizard_id', 'partner_id', 'Recipients')
    message = fields.Text('Message', required=True)
    attachment_ids = fields.Many2many('ir.attachment', 'whatsapp_msg_ir_attachments_rel', 'wizard_id', 'attachment_id', 'Attachments', tracking=True)
    unique_user = fields.Char(default=_default_unique_user)

    def format_amount(self, amount, currency):
        fmt = "%.{0}f".format(currency.decimal_places)
        lang = self.env['res.lang']._lang_get(self.env.context.get('lang') or 'en_US')
        formatted_amount = lang.format(fmt, currency.round(amount), grouping=True, monetary=True) \
            .replace(r' ', u'\N{NO-BREAK SPACE}').replace(r'-', u'-\N{ZERO WIDTH NO-BREAK SPACE}')
        pre = post = u''
        if currency.position == 'before':
            pre = u'{symbol}\N{NO-BREAK SPACE}'.format(symbol=currency.symbol or '')
        else:
            post = u'\N{NO-BREAK SPACE}{symbol}'.format(symbol=currency.symbol or '')
        return u'{pre}{0}{post}'.format(formatted_amount, pre=pre, post=post)

    def _phone_get_country(self, partner):
        if 'country_id' in partner:
            return partner.country_id
        return self.env.user.company_id.country_id

    def _msg_sanitization(self, partner, field_name):
        number = partner[field_name]
        if number and _sms_phonenumbers_lib_imported:
            country = self._phone_get_country(partner)
            country_code = country.code if country else None
            try:
                phone_nbr = phonenumbers.parse(number, region=country_code, keep_raw_input=True)
            except phonenumbers.phonenumberutil.NumberParseException:
                return number
            if not phonenumbers.is_possible_number(phone_nbr) or not phonenumbers.is_valid_number(phone_nbr):
                return number
            phone_fmt = phonenumbers.PhoneNumberFormat.E164
            return phonenumbers.format_number(phone_nbr, phone_fmt)
        else:
            return number

    def _get_records(self, model):
        if self.env.context.get('active_domain'):
            records = model.search(self.env.context.get('active_domain'))
        elif self.env.context.get('active_ids'):
            records = model.browse(self.env.context.get('active_ids', []))
        else:
            records = model.browse(self.env.context.get('active_id', []))
        return records

    def cleanhtml(self, raw_html):
        cleanr = re.compile('<.*?>')
        cleantext = re.sub(cleanr, '', raw_html)
        return cleantext

    @api.model
    def default_get(self, fields):
        result = super(SendWAMessage, self).default_get(fields)
        active_model = self.env.context.get('active_model')
        res_id = self.env.context.get('active_id')
        rec = self.env[active_model].browse(res_id)
        rec = rec.with_context(lang=rec.partner_id.lang)
        self = self.with_context(lang=rec.partner_id.lang)
        Attachment = self.env['ir.attachment']
        res_name = ''
        if active_model == 'account.move':
            if rec.name:
                res_name = 'Invoice_' + rec.name.replace('/', '_') if active_model == 'account.move' else rec.name.replace('/', '_')
        msg = result.get('message', '')
        result['message'] = msg
        res_user_id = self.env['res.users'].search([('partner_id', '=', rec.partner_id.id)])
        if not self.env.context.get('default_recipients') and active_model:
            model = self.env[active_model]
            records = self._get_records(model)
            phone_numbers = []
            no_phone_partners = []
            self = self.with_context(lang=rec.partner_id.lang)
            whatsapp_instance_id = self.env['whatsapp.instance'].get_whatsapp_instance()
            if active_model == 'sale.order':
                if rec.partner_id.mobile and rec.partner_id.country_id.phone_code:
                    # doc_name = 'quotation' if rec.state in ('approved', 'to_confirm') else 'order'
                    doc_name = _("order")
                    res_user_id = self.env['res.users'].search([('id', '=', self.env.user.id)])
                    msg = _("Hello") + " " + rec.partner_id.name
                    if rec.partner_id.parent_id:
                        msg += "(" + rec.partner_id.parent_id.name + ")"
                    if whatsapp_instance_id.sale_order_add_order_info_msg:
                        msg += "\n\n " + _("Your") + " "
                        if self.env.context.get('proforma'):
                            msg += _("in attachment your pro-forma invoice")
                        else:
                            msg += doc_name + " *" + rec.name + "* "
                        if rec.origin:
                            msg += _("(with reference") + " : " + rec.origin + ")"
                        msg += _(" is placed")
                        msg += "\n" + _("Total Amount") + ": " + self.format_amount(rec.amount_total, rec.pricelist_id.currency_id)
                    if whatsapp_instance_id.sale_order_add_order_product_details:
                        msg += "\n\n" + _("Following is your order details.")
                        for line_id in rec.order_line:
                            if line_id:
                                if line_id.product_id:
                                    msg += "\n\n*" + _("Product") + ":* " + line_id.product_id.display_name
                                if line_id.product_uom_qty and line_id.product_uom.name:
                                    msg += "\n*" + _("Qty") + ":* " + str(line_id.product_uom_qty) + " " + str(line_id.product_uom.name)
                                if line_id.price_unit:
                                    msg += "\n*" + _("Unit Price") + ":* " + str(line_id.price_unit)
                                if line_id.price_subtotal:
                                    msg += "\n*" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                            msg += "\n------------------"
                    msg += "\n" + _("Please find attached sale order which will help you to get detailed information.")
                    # if rec
                    if whatsapp_instance_id.sale_order_add_signature:
                        if whatsapp_instance_id.signature:
                            msg += "\n\n" + whatsapp_instance_id.signature
                        else:
                            msg += "\n\n" + self.env.user.company_id.name

                    report_obj = self.env.ref('sale.action_report_saleorder')
                    pdf = report_obj.sudo()._render_qweb_pdf(report_obj, rec.id)
                    extension = 'pdf'
                    report_name = safe_eval(report_obj.print_report_name, {'object': rec, 'time': time})
                    filename = "%s.%s" % (report_name, extension)
                    res = base64.b64encode(pdf[0])
                    attachments = []
                    attachments.append((filename, pdf))
                    attachment_ids = []

                    attachment_data = {
                        'name': filename,
                        'datas': res,
                        'type': 'binary',
                        'res_model': 'sale.order',
                        'res_id': rec.id,
                    }
                    attachment_ids.append(Attachment.create(attachment_data).id)
                    if attachment_ids:
                        result['attachment_ids'] = [(6, 0, attachment_ids)]
                else:
                    raise UserError(_('Please enter mobile number or select country'))

            if active_model == 'account.move':
                if rec.partner_id.mobile and rec.partner_id.country_id.phone_code:
                    doc_name = _("invoice")
                    res_user_id = self.env['res.users'].search([('id', '=', self.env.user.id)])
                    msg = _("Hello") + " " + rec.partner_id.name
                    if rec.partner_id.parent_id:
                        msg += "(" + rec.partner_id.parent_id.name + ")"
                    if whatsapp_instance_id.account_invoice_add_invoice_info_msg:
                        msg += "\n\n" + _("Here is your ")
                        if rec.state == 'draft':
                            msg += doc_name + " *" + _("draft invoice") + "* "
                        else:
                            msg += doc_name + " *" + rec.name + "* "
                        msg += "\n" + _("Total Amount") + ": " + self.format_amount(rec.amount_total, rec.currency_id)
                    if whatsapp_instance_id.account_invoice_add_invoice_product_details:
                        msg += "\n\n" + _("Following is your order details.")
                        for line_id in rec.invoice_line_ids:
                            if line_id:
                                if line_id.product_id:
                                    msg += "\n\n*" + _("Product") + ":* " + line_id.product_id.display_name
                                if line_id.quantity:
                                    msg += "\n*" + _("Qty") + ":* " + str(line_id.quantity)
                                if line_id.price_unit:
                                    msg += "\n*" + _("Unit Price") + ":* " + str(line_id.price_unit)
                                if line_id.price_subtotal:
                                    msg += "\n*" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                            msg += "\n------------------"

                    msg += "\n" + _("Please find attached invoice which will help you to get detailed information.")
                    if whatsapp_instance_id.account_invoice_add_signature:
                        if whatsapp_instance_id.signature:
                            msg += "\n\n" + whatsapp_instance_id.signature
                        else:
                            msg += "\n\n" + self.env.user.company_id.name
                    report_obj = self.env.ref('account.account_invoices_without_payment')
                    pdf = report_obj.sudo()._render_qweb_pdf(report_obj, rec.id)
                    extension = 'pdf'
                    report_name = safe_eval(report_obj.print_report_name, {'object': rec, 'time': time})
                    filename = "%s.%s" % (report_name, extension)
                    res = base64.b64encode(pdf[0])
                    attachments = []
                    attachments.append((filename, pdf))
                    attachment_ids = []

                    attachment_data = {
                        'name': filename,
                        'datas': res,
                        'type': 'binary',
                        'res_model': 'account.move',
                        'res_id': rec.id,
                    }
                    attachment_ids.append(Attachment.create(attachment_data).id)
                    if attachment_ids:
                        result['attachment_ids'] = [(6, 0, attachment_ids)]
                else:
                    raise UserError(_('Please enter mobile number or select country'))

            if active_model == 'stock.picking':
                if rec.partner_id.mobile and rec.partner_id.country_id.phone_code:
                    # doc_name = 'stock picking' if rec.state in ('assigned', 'done') else 'picking'
                    doc_name = _("Delivery order")
                    res_user_id = self.env['res.users'].search([('id', '=', self.env.user.id)])
                    msg = _("Hello") + " " + rec.partner_id.name
                    if rec.partner_id.parent_id:
                        msg += "(" + rec.partner_id.parent_id.name + ")"
                    if whatsapp_instance_id.delivery_order_add_order_info_msg:
                        msg += "\n\n" + _("Here is your") + " "
                        msg += doc_name + " *" + rec.name + "* "
                        if rec.origin:
                            msg += "(" + _("with reference") + ": " + rec.origin + ")"
                    if whatsapp_instance_id.delivery_order_add_order_product_details:
                        msg += "\n\n" + _("Following is your delivery order details.")
                        for line_id in rec.move_ids_without_package:
                            if line_id:
                                if line_id.product_id:
                                    msg += "\n\n*" + _("Product") + ":* " + line_id.product_id.display_name
                                if line_id.product_uom_qty and line_id.product_uom:
                                    msg += "\n*" + _("Qty") + ":* " + str(line_id.product_uom_qty) + " " + str(line_id.product_uom.name)
                                # if line_id.quantity_done:
                                #     msg += "\n*" + _("Done") + ":* "+str(line_id.quantity_done)
                            msg += "\n------------------"
                    msg += "\n" + _("Please find attached delivery order which will help you to get detailed information.")
                    if whatsapp_instance_id.delivery_order_add_signature:
                        if whatsapp_instance_id.signature:
                            msg += "\n\n" + whatsapp_instance_id.signature
                        else:
                            msg += "\n\n" + self.env.user.company_id.name

                    report_obj = self.env.ref('stock.action_report_picking')
                    pdf = report_obj.sudo()._render_qweb_pdf(report_obj, rec.id)
                    extension = 'pdf'
                    report_name = safe_eval(report_obj.print_report_name, {'object': rec, 'time': time})
                    filename = "%s.%s" % (report_name, extension)
                    res = base64.b64encode(pdf[0])
                    attachments = []
                    attachments.append((filename, pdf))
                    attachment_ids = []

                    attachment_data = {
                        'name': filename,
                        'datas': res,
                        'type': 'binary',
                        'res_model': 'stock.picking',
                        'res_id': rec.id,
                    }
                    attachment_ids.append(Attachment.create(attachment_data).id)
                    if attachment_ids:
                        result['attachment_ids'] = [(6, 0, attachment_ids)]
                else:
                    raise UserError(_('Please enter mobile number or select country'))

            if active_model == 'purchase.order':
                if rec.partner_id.mobile and rec.partner_id.country_id.phone_code:
                    doc_name = _("Purchase order")
                    res_user_id = self.env['res.users'].search([('id', '=', self.env.user.id)])
                    msg = _("Hello") + " " + rec.partner_id.name
                    if rec.partner_id.parent_id:
                        msg += "(" + rec.partner_id.parent_id.name + ")"
                    if whatsapp_instance_id.purchase_order_add_order_info_msg:
                        msg += "\n\n" + _("Here is your") + " "
                        msg += doc_name + " *" + rec.name + "* "
                        if rec.origin:
                            msg += "(" + _("with reference") + ": " + rec.origin + ")"
                        msg += "\n" + _("Total Amount") + ": " + self.format_amount(rec.amount_total, rec.currency_id) + "."
                    if whatsapp_instance_id.purchase_order_add_order_product_details:
                        msg += "\n\n" + _("Following is your order details.")
                        for line_id in rec.order_line:
                            if line_id:
                                if line_id.product_id:
                                    msg += "\n\n*" + _("Product") + ":* " + line_id.product_id.display_name
                                if line_id.product_qty and line_id.product_uom:
                                    msg += "\n*" + _("Qty") + ":* " + str(line_id.product_qty) + " " + str(line_id.product_uom.name)
                                if line_id.price_unit:
                                    msg += "\n*" + _("Unit Price") + ":* " + str(line_id.price_unit)
                                if line_id.price_subtotal:
                                    msg += "\n*" + _("Subtotal") + ":* " + str(line_id.price_subtotal)

                            msg += "\n------------------"
                    msg += "\n " + _("Please find attached purchase order which will help you to get detailed information.")
                    if whatsapp_instance_id.purchase_order_add_signature:
                        if whatsapp_instance_id.signature:
                            msg += "\n\n" + whatsapp_instance_id.signature
                        else:
                            msg += "\n\n" + self.env.user.company_id.name

                    report_obj = self.env.ref('purchase.action_report_purchase_order')
                    pdf = report_obj.sudo()._render_qweb_pdf(report_obj, rec.id)
                    extension = 'pdf'
                    report_name = safe_eval(report_obj.print_report_name, {'object': rec, 'time': time})
                    filename = "%s.%s" % (report_name, extension)
                    res = base64.b64encode(pdf[0])
                    attachments = []
                    attachments.append((filename, pdf))
                    attachment_ids = []

                    attachment_data = {
                        'name': filename,
                        'datas': res,
                        'type': 'binary',
                        'res_model': 'purchase.order',
                        'res_id': rec.id,
                    }
                    attachment_ids.append(Attachment.create(attachment_data).id)
                    if attachment_ids:
                        result['attachment_ids'] = [(6, 0, attachment_ids)]
                else:
                    raise UserError(_('Please enter mobile number or select country'))

            if active_model == 'account.payment':
                if rec.partner_id.mobile and rec.partner_id.country_id.phone_code:
                    doc_name = _("account payment")
                    res_user_id = self.env['res.users'].search([('id', '=', self.env.user.id)])
                    msg = _("Hello") + " " + rec.partner_id.name
                    if rec.partner_id.parent_id:
                        msg += "(" + rec.partner_id.parent_id.name + ")"
                    if whatsapp_instance_id.account_payment_details:
                        msg += "\n\n" + _("Your") + " "
                        if rec.name:
                            msg += doc_name + " *" + rec.name + "* "
                        else:
                            msg += doc_name + " *" + _("Draft Payment") + "* "
                        msg += " " + _("with Total Amount") + " " + self.format_amount(rec.amount, rec.currency_id) + "."
                        msg += "\n\n" + _("Following is your payment details.")
                        if rec:
                            if rec.payment_type:
                                msg += "\n\n*" + _("Payment Type") + ":* " + rec.payment_type
                            if rec.journal_id:
                                msg += "\n*" + _("Payment Journal") + ":* " + rec.journal_id.name
                            if rec.date:
                                msg += "\n*" + _("Payment date") + ":* " + str(rec.date)
                            if rec.ref:
                                msg += "\n*" + _("Memo") + ":* " + str(rec.ref)
                    msg += "\n " + _("Please find attached account payment which will help you to get detailed information.")
                    if whatsapp_instance_id.account_invoice_add_signature:
                        if whatsapp_instance_id.signature:
                            msg += "\n\n" + whatsapp_instance_id.signature
                        else:
                            msg += "\n\n" + self.env.user.company_id.name

                    report_obj = self.env.ref('account.action_report_payment_receipt')
                    pdf = report_obj.sudo()._render_qweb_pdf(report_obj, rec.id)
                    extension = 'pdf'
                    if report_obj.print_report_name:
                        report_name = safe_eval(report_obj.print_report_name, {'object': rec, 'time': time})
                        filename = "%s.%s" % (report_name, extension)
                        res = base64.b64encode(pdf[0])
                        attachments = []
                        attachments.append((filename, pdf))
                        attachment_ids = []

                        attachment_data = {
                            'name': filename,
                            'datas': res,
                            'type': 'binary',
                            'res_model': 'account.payment',
                            'res_id': rec.id,
                        }
                    else:
                        report_obj = self.env.ref('account.action_report_payment_receipt')
                        pdf = report_obj.sudo()._render_qweb_pdf(report_obj, rec.id)
                        res = base64.b64encode(pdf[0])
                        res_name = 'account.action_report_payment_receipt'
                        attachments = []
                        attachments.append((res_name, pdf))
                        attachment_ids = []
                        attachment_data = {
                            'name': 'Payment Receipt.pdf',
                            'datas': res,
                            'type': 'binary',
                            'res_model': 'account.payment',
                            'res_id': rec.id,
                        }
                    attachment_ids.append(Attachment.create(attachment_data).id)
                    if attachment_ids:
                        result['attachment_ids'] = [(6, 0, attachment_ids)]
                else:
                    raise UserError(_('Please enter mobile number or select country'))
            result['message'] = msg
            number = self._msg_sanitization(rec.partner_id, self.env.context.get('field_name') or 'mobile')
            if number:
                phone_numbers.append(number)
            else:
                no_phone_partners.append(rec.partner_id.name)
            if no_phone_partners:
                raise UserError(_('Missing mobile number for %s.') % ', '.join(no_phone_partners))
            result['partner_ids'] = [(6, 0, [rec.partner_id.id])]
            result['message'] = msg
        return result

    def convert_to_html(self, message):
        for data in re.findall(r'\*.*?\*', message):
            message = message.replace(data, "<strong>" + data.strip('*') + "</strong>")
        return message

    def create_whatsapp_message(self, mobile_with_country, message, message_id, chatId_message, type, whatsapp_instance_id, model, record):
        whatsapp_messages_dict = {
            'message_id': message_id,
            'name': message,
            'message_body': message,
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
            'res_id': record.id
        }

        if model == 'res.partner':
            whatsapp_messages_dict['partner_id'] = record.id
        else:
            if self._context.get('partner_id'):
                whatsapp_messages_dict['partner_id'] = self._context.get('partner_id')
            elif not model == 'mail.channel' and not model == 'odoo.group' and not model == 'whatsapp.marketing' and not self.env.context.get('skip_partner'):
                if record.partner_id:
                    whatsapp_messages_dict['partner_id'] = record.partner_id.id
        whatsapp_messages_id = self.env['whatsapp.messages'].sudo().create(whatsapp_messages_dict)
        _logger.info("Whatsapp message created in odoo %s: ", str(whatsapp_messages_id.id))

    def create_whatsapp_message_for_attachment(self, mobile_with_country, attachment_id, message_id, chatId_message, type, whatsapp_instance_id, model, record):
        whatsapp_messages_dict = {
            'message_id': message_id,
            'name': attachment_id.name,
            'message_body': attachment_id.name,
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
            elif not model == 'mail.channel' and not model == 'odoo.group' and not model == 'whatsapp.marketing' and not self.env.context.get('skip_partner'):
                if record.partner_id:
                    whatsapp_messages_dict['partner_id'] = record.partner_id.id
        whatsapp_messages_id = self.env['whatsapp.messages'].sudo().create(whatsapp_messages_dict)
        _logger.info("Whatsapp message created in odoo %s: ", str(whatsapp_messages_id.id))

    def action_send_msg(self):
        whatsapp_instance_id = self.env['whatsapp.instance'].get_whatsapp_instance()

        if whatsapp_instance_id.provider == 'whatsapp_chat_api':
            self.send_message_from_chat_api(whatsapp_instance_id)
        elif whatsapp_instance_id.provider == 'gupshup':
            self.send_message_from_gupshup(whatsapp_instance_id)

    def send_message_from_chat_api(self, whatsapp_instance_id):
        if whatsapp_instance_id.send_whatsapp_through_template:
            self.send_message_from_chat_api_through_template(whatsapp_instance_id)
        else:
            self.send_message_from_chat_api_without_template(whatsapp_instance_id)

    def send_message_from_chat_api_without_template(self, whatsapp_instance_id):
        param = self.env['res.config.settings'].sudo().get_values()
        active_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')
        try:
            status_url = whatsapp_instance_id.whatsapp_endpoint + '/status?token=' + whatsapp_instance_id.whatsapp_token
            status_response = requests.get(status_url)
        except Exception as e_log:
            _logger.exception(e_log)
            raise UserError(_('Please add proper whatsapp endpoint or whatsapp token'))
        if status_response.status_code == 200 or status_response.status_code == 201:
            json_response_status = json.loads(status_response.text)
            if active_model == 'sale.order' or active_model == 'account.move' or active_model == 'purchase.order' or active_model == 'stock.picking' or active_model == \
                    'account.payment':
                rec = self.env[active_model].browse(active_id)
                number = str(rec.partner_id.country_id.phone_code) + rec.partner_id.mobile
                comment = "fa fa-whatsapp"
                dict_send_file = {}
                # body_html = tools.append_content_to_html(
                #     '<div class = "%s"></div>' % tools.ustr(comment), self.message)
                mail_message_body = ''
                mail_message_body = """<p style='margin:0px; font-size:13px; font-family:"Lucida Grande", Helvetica, Verdana, Arial, sans-serif'><img src="/web_editor/font_to_img/62002/rgb(73,80,87)/13" data-class="fa fa-whatsapp" style="border-style:none; vertical-align:middle; height:auto; width:auto" width="0" height="0"></p>"""
                mail_message_body += self.message
                update_msg = self.convert_to_html(mail_message_body)
                body_mail_msg = "<br />".join(update_msg.split("\n"))
                whatsapp_msg_number = rec.partner_id.mobile
                whatsapp_msg_number_without_space = whatsapp_msg_number.replace(" ", "")
                if '+' in whatsapp_msg_number_without_space:
                    whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace(
                        '+' + str(rec.partner_id.country_id.phone_code), "")
                else:
                    whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace(str(rec.partner_id.country_id.phone_code), "")
                if rec.partner_id.country_id.phone_code and rec.partner_id.mobile:
                    url = whatsapp_instance_id.whatsapp_endpoint + '/sendMessage?token=' + whatsapp_instance_id.whatsapp_token
                    headers = {"Content-Type": "application/json"}
                    mobile_with_country = str(rec.partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code
                    tmp_dict = {
                        "phone": mobile_with_country,
                        "body": self.message}
                    response = requests.post(url, json.dumps(tmp_dict), headers=headers)
                    if response.status_code == 201 or response.status_code == 200:
                        json_send_message_response = json.loads(response.text)
                        if not json_send_message_response.get('sent') and json_send_message_response.get('error') and json_send_message_response.get(
                                'error').get('message') == 'Recipient is not a valid WhatsApp user':
                            raise UserError(_('Please add valid whatsapp number for %s customer') % rec.partner_id.name)
                        elif json_send_message_response.get('sent'):
                            _logger.info("\nSend Message successfully")
                            self.create_whatsapp_message(mobile_with_country, self.message, json_send_message_response.get('id'), json_send_message_response.get('message'), "text",
                                                         whatsapp_instance_id, active_model, rec)
                            if self.attachment_ids:
                                url_send_file = whatsapp_instance_id.whatsapp_endpoint + '/sendFile?token=' + whatsapp_instance_id.whatsapp_token
                                headers_send_file = {"Content-Type": "application/json"}
                                whatsapp_msg_number = rec.partner_id.mobile
                                whatsapp_msg_number_without_space = whatsapp_msg_number.replace(" ", "")
                                if '+' in whatsapp_msg_number_without_space:
                                    whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace('+' + str(rec.partner_id.country_id.phone_code), "")
                                else:
                                    whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace(str(rec.partner_id.country_id.phone_code), "")

                                for attachment in self.attachment_ids:
                                    encoded_file = str(attachment.datas)
                                    if attachment.mimetype:
                                        dict_send_file = {
                                            "phone": mobile_with_country,
                                            "body": "data:" + attachment.mimetype + ";base64," + encoded_file[2:-1],
                                            "filename": attachment.name,
                                            "caption": attachment.name
                                        }
                                        response_send_file = requests.post(url_send_file, json.dumps(dict_send_file), headers=headers_send_file)
                                        if response_send_file.status_code == 201 or response_send_file.status_code == 200:
                                            _logger.info("\nSend file attachment successfully")
                                            json_send_file_response = json.loads(response_send_file.text)

                                            self.create_whatsapp_message_for_attachment(mobile_with_country, attachment, json_send_file_response.get('id'),
                                                                                        json_send_file_response.get('message'), "document",
                                                                                        whatsapp_instance_id, active_model, rec)
                                mail_message_obj = self.env['mail.message']
                                if active_model == 'sale.order' and whatsapp_instance_id.sale_order_add_message_in_chatter:
                                    # rec.access_token = str(uuid.uuid4())
                                    mail_message_id = mail_message_obj.sudo().create({
                                        'res_id': rec.id,
                                        'model': active_model,
                                        'body': body_mail_msg,
                                        'attachment_ids': [(4, attachment.id) for attachment in self.attachment_ids],
                                    })
                                    mail_message_id.message_format()
                                if active_model == 'purchase.order' and whatsapp_instance_id.purchase_order_add_message_in_chatter:
                                    # rec.access_token = str(uuid.uuid4())
                                    mail_message_id = mail_message_obj.sudo().create({
                                        'res_id': rec.id,
                                        'model': active_model,
                                        'body': body_mail_msg,
                                        'attachment_ids': [(4, attachment.id) for attachment in
                                                           self.attachment_ids],

                                    })
                                    mail_message_id.message_format()
                                if active_model == 'stock.picking' and whatsapp_instance_id.delivery_order_add_message_in_chatter:
                                    # rec.access_token = str(uuid.uuid4())
                                    mail_message_id = mail_message_obj.sudo().create({
                                        'res_id': rec.id,
                                        'model': active_model,
                                        'body': body_mail_msg,
                                        'attachment_ids': [(4, attachment.id) for attachment in
                                                           self.attachment_ids],
                                    })
                                    mail_message_id.message_format()
                                if (active_model == 'account.move' or active_model == 'account.payment') and whatsapp_instance_id.account_invoice_add_message_in_chatter:
                                    # rec.access_token = str(uuid.uuid4())
                                    mail_message_id = mail_message_obj.sudo().create({
                                        'res_id': rec.id,
                                        'model': active_model,
                                        'body': body_mail_msg,
                                        'attachment_ids': [(4, attachment.id) for attachment in
                                                           self.attachment_ids],

                                    })
                                    mail_message_id.message_format()

                            elif not self.attachment_ids and response.status_code == 201 or response.status_code == 200:
                                if active_model == 'sale.order' and whatsapp_instance_id.sale_order_add_message_in_chatter:
                                    mail_message_id = self.env['mail.message'].sudo().create({
                                        'res_id': rec.id,
                                        'model': active_model,
                                        'body': body_mail_msg
                                    })
                                    mail_message_id.message_format()

                                if active_model == 'purchase.order' and whatsapp_instance_id.purchase_order_add_message_in_chatter:
                                    mail_message_id = self.env['mail.message'].sudo().create({
                                        'res_id': rec.id,
                                        'model': active_model,
                                        'body': body_mail_msg
                                    })
                                    mail_message_id.message_format()

                                if active_model == 'stock.picking' and whatsapp_instance_id.delivery_order_add_message_in_chatter:
                                    mail_message_id = self.env['mail.message'].sudo().create({
                                        'res_id': rec.id,
                                        'model': active_model,
                                        'body': body_mail_msg
                                    })
                                    mail_message_id.message_format()

                                if (active_model == 'account.move' or active_model == 'account.payment') and whatsapp_instance_id.account_invoice_add_message_in_chatter:
                                    mail_message_id = self.env['mail.message'].sudo().create({
                                        'res_id': rec.id,
                                        'model': active_model,
                                        'body': body_mail_msg
                                    })
                                    mail_message_id.message_format()
                    # else:
                    #     raise UserError(_('Please add valid whatsapp number for %s customer') % rec.partner_id.name)
                else:
                    raise UserError(_('Please enter %s mobile number or select country', rec.partner_id))
        else:
            raise UserError(_('Please authorize your mobile number with chat api'))

    def send_message_from_chat_api_through_template(self, whatsapp_instance_id):
        active_model = self.env.context.get('active_model')
        if active_model == 'sale.order':
            self.chat_api_template_sale_order_send_template_message(whatsapp_instance_id)
        elif active_model == 'account.move':
            self.chat_api_template_account_invoice_send_template_message(whatsapp_instance_id)
        elif active_model == 'stock.picking':
            self.chat_api_template_delivery_order_send_template_message(whatsapp_instance_id)
        elif active_model == 'account.payment':
            self.chat_api_template_account_payment_send_template_message(whatsapp_instance_id)
        elif active_model == 'purchase.order':
            self.chat_api_template_purchase_order_send_template_message(whatsapp_instance_id)

    def chat_api_template_sale_order_send_template_message(self, whatsapp_instance_id):
        url = whatsapp_instance_id.whatsapp_endpoint + '/sendTemplate?token=' + whatsapp_instance_id.whatsapp_token
        headers = {"Content-Type": "application/json"}
        active_model = self.env.context.get('active_model')
        record = self.env[active_model].browse(self.env.context.get('active_id'))
        number_without_code = ''
        if record.partner_id.mobile and record.partner_id.country_id:
            whatsapp_number = record.partner_id.mobile
            whatsapp_msg_number_without_space = whatsapp_number.replace(" ", "")
            if '+' in whatsapp_msg_number_without_space:
                number_without_code = whatsapp_msg_number_without_space.replace('+' + str(record.partner_id.country_id.phone_code), "")
            else:
                number_without_code = whatsapp_msg_number_without_space.replace(str(record.partner_id.country_id.phone_code), "")

        media_id = None
        if self.attachment_ids:
            media_id = self.get_media_id(self.attachment_ids[0], whatsapp_instance_id)
        if not whatsapp_instance_id.sale_order_add_signature and not whatsapp_instance_id.sale_order_add_order_product_details and not whatsapp_instance_id.sale_order_add_order_info_msg:
            response = self.chat_api_template_sale_order_without_order_details_lines_signature(url, headers, record, media_id, number_without_code, whatsapp_instance_id)
        elif whatsapp_instance_id.sale_order_add_signature and not whatsapp_instance_id.sale_order_add_order_product_details and not whatsapp_instance_id.sale_order_add_order_info_msg:
            response = self.chat_api_template_sale_order_without_order_details_lines_with_signature(url, headers, record, media_id, number_without_code, whatsapp_instance_id)
        elif not whatsapp_instance_id.sale_order_add_signature and not whatsapp_instance_id.sale_order_add_order_product_details and whatsapp_instance_id.sale_order_add_order_info_msg:
            response = self.chat_api_template_sale_order_without_lines_signature_with_order_details(url, headers, record, media_id, number_without_code, whatsapp_instance_id)
        elif not whatsapp_instance_id.sale_order_add_signature and whatsapp_instance_id.sale_order_add_order_product_details and not whatsapp_instance_id.sale_order_add_order_info_msg:
            response = self.chat_api_template_sale_order_without_order_details_signature_with_lines(url, headers, record, media_id, number_without_code, whatsapp_instance_id)
        elif whatsapp_instance_id.sale_order_add_signature and not whatsapp_instance_id.sale_order_add_order_product_details and whatsapp_instance_id.sale_order_add_order_info_msg:
            response = self.chat_api_template_sale_order_without_lines_with_signature_order_details(url, headers, record, media_id, number_without_code, whatsapp_instance_id)
        elif whatsapp_instance_id.sale_order_add_signature and whatsapp_instance_id.sale_order_add_order_product_details and not whatsapp_instance_id.sale_order_add_order_info_msg:
            response = self.chat_api_template_sale_order_without_order_details_with_signature_lines(url, headers, record, media_id, number_without_code, whatsapp_instance_id)
        elif not whatsapp_instance_id.sale_order_add_signature and whatsapp_instance_id.sale_order_add_order_product_details and whatsapp_instance_id.sale_order_add_order_info_msg:
            response = self.chat_api_template_sale_order_without_signature_with_order_details_lines(url, headers, record, media_id, number_without_code, whatsapp_instance_id)
        elif whatsapp_instance_id.sale_order_add_signature and whatsapp_instance_id.sale_order_add_order_product_details and whatsapp_instance_id.sale_order_add_order_info_msg:
            response = self.chat_api_template_sale_order_with_signature_order_details_lines(url, headers, record, media_id, number_without_code, whatsapp_instance_id)
        if response.status_code == 201 or response.status_code == 200:
            json_response = json.loads(response.text)
            if json_response.get('sent') and json_response.get('description') == 'Message has been sent to the provider':
                _logger.info("\nSend Message successfully")
                mobile_with_country = str(record.partner_id.country_id.phone_code) + number_without_code
                self.create_whatsapp_message_for_template(mobile_with_country, self.message, json_response.get('id'), json_response.get('message'), whatsapp_instance_id,
                                                          active_model, record, self.attachment_ids[0])
                if active_model == 'sale.order' and whatsapp_instance_id.sale_order_add_message_in_chatter:
                    self.add_message_in_chatter(record, active_model, self.attachment_ids[0])

            elif not json_response.get('sent') and json_response.get('error').get('message') == 'Recipient is not a valid WhatsApp user':
                raise UserError(_('Please add valid whatsapp number for %s customer') % record.partner_id.name)
            elif not json_response.get('sent') and json_response.get('message'):
                raise UserError(_('%s') % json_response.get('message'))
        return True

    def chat_api_template_account_invoice_send_template_message(self, whatsapp_instance_id):
        url = whatsapp_instance_id.whatsapp_endpoint + '/sendTemplate?token=' + whatsapp_instance_id.whatsapp_token
        headers = {"Content-Type": "application/json"}
        active_model = self.env.context.get('active_model')
        record = self.env[active_model].browse(self.env.context.get('active_id'))
        number_without_code = ''
        if record.partner_id.mobile and record.partner_id.country_id:
            whatsapp_number = record.partner_id.mobile
            whatsapp_msg_number_without_space = whatsapp_number.replace(" ", "")
            if '+' in whatsapp_msg_number_without_space:
                number_without_code = whatsapp_msg_number_without_space.replace('+' + str(record.partner_id.country_id.phone_code), "")
            else:
                number_without_code = whatsapp_msg_number_without_space.replace(str(record.partner_id.country_id.phone_code), "")

        media_id = None
        if self.attachment_ids:
            media_id = self.get_media_id(self.attachment_ids[0], whatsapp_instance_id)
        if not whatsapp_instance_id.account_invoice_add_signature and not whatsapp_instance_id.account_invoice_add_invoice_product_details and not whatsapp_instance_id.account_invoice_add_invoice_info_msg:
            response = self.chat_api_template_account_invoice_without_invoice_details_lines_signature(url, headers, record, media_id, number_without_code, whatsapp_instance_id)
        elif whatsapp_instance_id.account_invoice_add_signature and not whatsapp_instance_id.account_invoice_add_invoice_product_details and not whatsapp_instance_id.account_invoice_add_invoice_info_msg:
            response = self.chat_api_template_account_invoice_without_invoice_details_lines_with_signature(url, headers, record, media_id, number_without_code,
                                                                                                           whatsapp_instance_id)
        elif not whatsapp_instance_id.account_invoice_add_signature and not whatsapp_instance_id.account_invoice_add_invoice_product_details and whatsapp_instance_id.account_invoice_add_invoice_info_msg:
            response = self.chat_api_template_account_invoice_without_lines_signature_with_invoice_details(url, headers, record, media_id, number_without_code,
                                                                                                           whatsapp_instance_id)
        elif not whatsapp_instance_id.account_invoice_add_signature and whatsapp_instance_id.account_invoice_add_invoice_product_details and not whatsapp_instance_id.account_invoice_add_invoice_info_msg:
            response = self.chat_api_template_account_invoice_without_invoice_details_signature_with_lines(url, headers, record, media_id, number_without_code,
                                                                                                           whatsapp_instance_id)
        elif whatsapp_instance_id.account_invoice_add_signature and not whatsapp_instance_id.account_invoice_add_invoice_product_details and whatsapp_instance_id.account_invoice_add_invoice_info_msg:
            response = self.chat_api_template_account_invoice_without_lines_with_signature_invoice_details(url, headers, record, media_id, number_without_code,
                                                                                                           whatsapp_instance_id)
        elif whatsapp_instance_id.account_invoice_add_signature and whatsapp_instance_id.account_invoice_add_invoice_product_details and not whatsapp_instance_id.account_invoice_add_invoice_info_msg:
            response = self.chat_api_template_account_invoice_without_invoice_details_with_signature_lines(url, headers, record, media_id, number_without_code,
                                                                                                           whatsapp_instance_id)
        elif not whatsapp_instance_id.account_invoice_add_signature and whatsapp_instance_id.account_invoice_add_invoice_product_details and whatsapp_instance_id.account_invoice_add_invoice_info_msg:
            response = self.chat_api_template_account_invoice_without_signature_with_invoice_details_lines(url, headers, record, media_id, number_without_code,
                                                                                                           whatsapp_instance_id)
        elif whatsapp_instance_id.account_invoice_add_signature and whatsapp_instance_id.account_invoice_add_invoice_product_details and whatsapp_instance_id.account_invoice_add_invoice_info_msg:
            response = self.chat_api_template_account_invoice_with_signature_invoice_details_lines(url, headers, record, media_id, number_without_code, whatsapp_instance_id)

        if response.status_code == 201 or response.status_code == 200:
            json_response = json.loads(response.text)
            if json_response.get('sent') and json_response.get('description') == 'Message has been sent to the provider':
                _logger.info("\nSend Message successfully")
                mobile_with_country = str(record.partner_id.country_id.phone_code) + number_without_code
                self.create_whatsapp_message_for_template(mobile_with_country, self.message, json_response.get('id'), json_response.get('message'), whatsapp_instance_id,
                                                          active_model, record, self.attachment_ids[0])
                if active_model == 'account.move' and whatsapp_instance_id.account_invoice_add_message_in_chatter:
                    self.add_message_in_chatter(record, active_model, self.attachment_ids[0])

            elif not json_response.get('sent') and json_response.get('error').get('message') == 'Recipient is not a valid WhatsApp user':
                raise UserError(_('Please add valid whatsapp number for %s customer') % record.partner_id.name)
            elif not json_response.get('sent') and json_response.get('message'):
                raise UserError(_('%s') % json_response.get('message'))
        return True

    def chat_api_template_delivery_order_send_template_message(self, whatsapp_instance_id):
        url = whatsapp_instance_id.whatsapp_endpoint + '/sendTemplate?token=' + whatsapp_instance_id.whatsapp_token
        headers = {"Content-Type": "application/json"}
        active_model = self.env.context.get('active_model')
        record = self.env[active_model].browse(self.env.context.get('active_id'))
        number_without_code = ''
        if record.partner_id.mobile and record.partner_id.country_id:
            whatsapp_number = record.partner_id.mobile
            whatsapp_msg_number_without_space = whatsapp_number.replace(" ", "")
            if '+' in whatsapp_msg_number_without_space:
                number_without_code = whatsapp_msg_number_without_space.replace('+' + str(record.partner_id.country_id.phone_code), "")
            else:
                number_without_code = whatsapp_msg_number_without_space.replace(str(record.partner_id.country_id.phone_code), "")

        media_id = None
        if self.attachment_ids:
            media_id = self.get_media_id(self.attachment_ids[0], whatsapp_instance_id)
        if not whatsapp_instance_id.delivery_order_add_signature and not whatsapp_instance_id.delivery_order_add_order_product_details and not whatsapp_instance_id.delivery_order_add_order_info_msg:
            response = self.chat_api_template_delivery_order_without_order_details_lines_signature(url, headers, record, media_id, number_without_code, whatsapp_instance_id)
        elif whatsapp_instance_id.delivery_order_add_signature and not whatsapp_instance_id.delivery_order_add_order_product_details and not whatsapp_instance_id.delivery_order_add_order_info_msg:
            response = self.chat_api_template_delivery_order_without_order_details_lines_with_signature(url, headers, record, media_id, number_without_code, whatsapp_instance_id)
        elif not whatsapp_instance_id.delivery_order_add_signature and not whatsapp_instance_id.delivery_order_add_order_product_details and whatsapp_instance_id.delivery_order_add_order_info_msg:
            response = self.chat_api_template_delivery_order_without_lines_signature_with_order_details(url, headers, record, media_id, number_without_code, whatsapp_instance_id)
        elif not whatsapp_instance_id.delivery_order_add_signature and whatsapp_instance_id.delivery_order_add_order_product_details and not whatsapp_instance_id.delivery_order_add_order_info_msg:
            response = self.chat_api_template_delivery_order_without_order_details_signature_with_lines(url, headers, record, media_id, number_without_code, whatsapp_instance_id)
        elif whatsapp_instance_id.delivery_order_add_signature and not whatsapp_instance_id.delivery_order_add_order_product_details and whatsapp_instance_id.delivery_order_add_order_info_msg:
            response = self.chat_api_template_delivery_order_without_lines_with_signature_order_details(url, headers, record, media_id, number_without_code, whatsapp_instance_id)
        elif whatsapp_instance_id.delivery_order_add_signature and whatsapp_instance_id.delivery_order_add_order_product_details and not whatsapp_instance_id.delivery_order_add_order_info_msg:
            response = self.chat_api_template_delivery_order_without_order_details_with_signature_lines(url, headers, record, media_id, number_without_code, whatsapp_instance_id)
        elif not whatsapp_instance_id.delivery_order_add_signature and whatsapp_instance_id.delivery_order_add_order_product_details and whatsapp_instance_id.delivery_order_add_order_info_msg:
            response = self.chat_api_template_delivery_order_without_signature_with_order_details_lines(url, headers, record, media_id, number_without_code, whatsapp_instance_id)
        elif whatsapp_instance_id.delivery_order_add_signature and whatsapp_instance_id.delivery_order_add_order_product_details and whatsapp_instance_id.delivery_order_add_order_info_msg:
            response = self.chat_api_template_delivery_order_with_signature_order_details_lines(url, headers, record, media_id, number_without_code, whatsapp_instance_id)

        if response.status_code == 201 or response.status_code == 200:
            json_response = json.loads(response.text)
            if json_response.get('sent') and json_response.get('description') == 'Message has been sent to the provider':
                _logger.info("\nSend Message successfully")
                mobile_with_country = str(record.partner_id.country_id.phone_code) + number_without_code
                self.create_whatsapp_message_for_template(mobile_with_country, self.message, json_response.get('id'), json_response.get('message'), whatsapp_instance_id,
                                                          active_model, record, self.attachment_ids[0])
                if active_model == 'stock.picking' and whatsapp_instance_id.delivery_order_add_message_in_chatter:
                    self.add_message_in_chatter(record, active_model, self.attachment_ids[0])

            elif not json_response.get('sent') and json_response.get('error').get('message') == 'Recipient is not a valid WhatsApp user':
                raise UserError(_('Please add valid whatsapp number for %s customer') % record.partner_id.name)
            elif not json_response.get('sent') and json_response.get('message'):
                raise UserError(_('%s') % json_response.get('message'))
        return True

    def chat_api_template_account_payment_send_template_message(self, whatsapp_instance_id):
        param = self.env['res.config.settings'].sudo().get_values()
        url = whatsapp_instance_id.whatsapp_endpoint + '/sendTemplate?token=' + whatsapp_instance_id.whatsapp_token
        headers = {"Content-Type": "application/json"}
        active_model = self.env.context.get('active_model')
        record = self.env[active_model].browse(self.env.context.get('active_id'))
        number_without_code = ''
        if record.partner_id.mobile and record.partner_id.country_id:
            whatsapp_number = record.partner_id.mobile
            whatsapp_msg_number_without_space = whatsapp_number.replace(" ", "")
            if '+' in whatsapp_msg_number_without_space:
                number_without_code = whatsapp_msg_number_without_space.replace('+' + str(record.partner_id.country_id.phone_code), "")
            else:
                number_without_code = whatsapp_msg_number_without_space.replace(str(record.partner_id.country_id.phone_code), "")

        media_id = None
        if self.attachment_ids:
            media_id = self.get_media_id(self.attachment_ids[0], whatsapp_instance_id)
        if not whatsapp_instance_id.account_invoice_add_signature and not whatsapp_instance_id.account_payment_details:
            response = self.chat_api_template_account_payment_without_payment_details_signature(url, headers, record, media_id, number_without_code, whatsapp_instance_id)
        elif whatsapp_instance_id.account_invoice_add_signature and not whatsapp_instance_id.account_payment_details:
            response = self.chat_api_template_account_payment_without_payment_details_with_signature(url, headers, record, media_id, number_without_code, whatsapp_instance_id)
        elif not whatsapp_instance_id.account_invoice_add_signature and whatsapp_instance_id.account_payment_details:
            response = self.chat_api_template_account_payment_without_signature_with_payment_details(url, headers, record, media_id, number_without_code, whatsapp_instance_id)
        elif whatsapp_instance_id.account_invoice_add_signature and whatsapp_instance_id.account_payment_details:
            response = self.chat_api_template_account_payment_with_signature_payment_details(url, headers, record, media_id, number_without_code, whatsapp_instance_id)

        if response.status_code == 201 or response.status_code == 200:
            json_response = json.loads(response.text)
            if json_response.get('sent') and json_response.get('description') == 'Message has been sent to the provider':
                _logger.info("\nSend Message successfully")
                mobile_with_country = str(record.partner_id.country_id.phone_code) + number_without_code
                self.create_whatsapp_message_for_template(mobile_with_country, self.message, json_response.get('id'), json_response.get('message'), whatsapp_instance_id,
                                                          active_model, record, self.attachment_ids[0])
                if active_model == 'account.payment' and whatsapp_instance_id.account_invoice_add_message_in_chatter:
                    self.add_message_in_chatter(record, active_model, self.attachment_ids[0])

            elif not json_response.get('sent') and json_response.get('error').get('message') == 'Recipient is not a valid WhatsApp user':
                raise UserError(_('Please add valid whatsapp number for %s customer') % record.partner_id.name)
            elif not json_response.get('sent') and json_response.get('message'):
                raise UserError(_('%s') % json_response.get('message'))
        return True

    def chat_api_template_purchase_order_send_template_message(self, whatsapp_instance_id):
        param = self.env['res.config.settings'].sudo().get_values()
        url = whatsapp_instance_id.whatsapp_endpoint + '/sendTemplate?token=' + whatsapp_instance_id.whatsapp_token
        headers = {"Content-Type": "application/json"}
        active_model = self.env.context.get('active_model')
        record = self.env[active_model].browse(self.env.context.get('active_id'))
        number_without_code = ''
        if record.partner_id.mobile and record.partner_id.country_id:
            whatsapp_number = record.partner_id.mobile
            whatsapp_msg_number_without_space = whatsapp_number.replace(" ", "")
            if '+' in whatsapp_msg_number_without_space:
                number_without_code = whatsapp_msg_number_without_space.replace('+' + str(record.partner_id.country_id.phone_code), "")
            else:
                number_without_code = whatsapp_msg_number_without_space.replace(str(record.partner_id.country_id.phone_code), "")

        media_id = None
        if self.attachment_ids:
            media_id = self.get_media_id(self.attachment_ids[0], whatsapp_instance_id)
        if not whatsapp_instance_id.purchase_order_add_signature and not whatsapp_instance_id.purchase_order_add_order_product_details and not whatsapp_instance_id.purchase_order_add_order_info_msg:
            response = self.chat_api_template_purchase_order_without_order_details_lines_signature(url, headers, record, media_id, number_without_code, whatsapp_instance_id)
        elif whatsapp_instance_id.purchase_order_add_signature and not whatsapp_instance_id.purchase_order_add_order_product_details and not whatsapp_instance_id.purchase_order_add_order_info_msg:
            response = self.chat_api_template_purchase_order_without_order_details_lines_with_signature(url, headers, record, media_id, number_without_code, whatsapp_instance_id)
        elif not whatsapp_instance_id.purchase_order_add_signature and not whatsapp_instance_id.purchase_order_add_order_product_details and whatsapp_instance_id.purchase_order_add_order_info_msg:
            response = self.chat_api_template_purchase_order_without_lines_signature_with_order_details(url, headers, record, media_id, number_without_code, whatsapp_instance_id)
        elif not whatsapp_instance_id.purchase_order_add_signature and whatsapp_instance_id.purchase_order_add_order_product_details and not whatsapp_instance_id.purchase_order_add_order_info_msg:
            response = self.chat_api_template_purchase_order_without_order_details_signature_with_lines(url, headers, record, media_id, number_without_code, whatsapp_instance_id)
        elif whatsapp_instance_id.purchase_order_add_signature and not whatsapp_instance_id.purchase_order_add_order_product_details and whatsapp_instance_id.purchase_order_add_order_info_msg:
            response = self.chat_api_template_purchase_order_without_lines_with_signature_order_details(url, headers, record, media_id, number_without_code, whatsapp_instance_id)
        elif whatsapp_instance_id.purchase_order_add_signature and whatsapp_instance_id.purchase_order_add_order_product_details and not whatsapp_instance_id.purchase_order_add_order_info_msg:
            response = self.chat_api_template_purchase_order_without_order_details_with_signature_lines(url, headers, record, media_id, number_without_code, whatsapp_instance_id)
        elif not whatsapp_instance_id.purchase_order_add_signature and whatsapp_instance_id.purchase_order_add_order_product_details and whatsapp_instance_id.purchase_order_add_order_info_msg:
            response = self.chat_api_template_purchase_order_without_signature_with_order_details_lines(url, headers, record, media_id, number_without_code, whatsapp_instance_id)
        elif whatsapp_instance_id.purchase_order_add_signature and whatsapp_instance_id.purchase_order_add_order_product_details and whatsapp_instance_id.purchase_order_add_order_info_msg:
            response = self.chat_api_template_purchase_order_with_signature_order_details_lines(url, headers, record, media_id, number_without_code, whatsapp_instance_id)

        if response.status_code == 201 or response.status_code == 200:
            json_response = json.loads(response.text)
            if json_response.get('sent') and json_response.get('description') == 'Message has been sent to the provider':
                _logger.info("\nSend Message successfully")
                mobile_with_country = str(record.partner_id.country_id.phone_code) + number_without_code
                self.create_whatsapp_message_for_template(mobile_with_country, self.message, json_response.get('id'), json_response.get('message'), whatsapp_instance_id,
                                                          active_model, record, self.attachment_ids[0])

                if active_model == 'purchase.order' and self.env['ir.config_parameter'].sudo().get_param(
                        'pragmatic_odoo_whatsapp_integration.group_purchase_display_chatter_message'):
                    self.add_message_in_chatter(record, active_model, self.attachment_ids[0])

            elif not json_response.get('sent') and json_response.get('error').get('message') == 'Recipient is not a valid WhatsApp user':
                raise UserError(_('Please add valid whatsapp number for %s customer') % record.partner_id.name)
            elif not json_response.get('sent') and json_response.get('message'):
                raise UserError(_('%s') % json_response.get('message'))
        return True

    def chat_api_template_sale_order_without_order_details_lines_signature(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'sale_order_without_order_details_lines_signature_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)],
            limit=1)
        if whatsapp_template_id.approval_state == 'approved' and media_id:
            payload = {
                "template": whatsapp_template_id.name,
                "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                "namespace": whatsapp_template_id.namespace,
                "params": [
                    {
                        "type": "header",
                        "parameters": [{
                            "type": "document",
                            "document": {"id": media_id, "filename": self.attachment_ids[0].name}
                        }]
                    },
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": record.partner_id.name}]
                    }
                ],
                "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
            }
            return requests.post(url, data=json.dumps(payload), headers=headers)

        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_sale_order_without_order_details_lines_with_signature(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'sale_order_without_order_details_lines_with_signature_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'approved' and media_id:
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [{
                                   "type": "document",
                                   "document": {"id": media_id, "filename": self.attachment_ids[0].name}
                               }]
                           },
                           {
                               "type": "body",
                               "parameters": [{"type": "text", "text": record.partner_id.name}]
                           },
                           {
                               "type": "footer",
                               "parameters": [{"type": "footer", "text": whatsapp_template_id.footer}]
                           },
                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_sale_order_without_lines_signature_with_order_details(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'sale_order_without_lines_signature_with_order_details_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id), ('default_template', '=', True)],
            limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [
                                   {
                                       "type": "document",
                                       "document":
                                           {"id": media_id, "filename": self.attachment_ids[0].name}
                                   }
                               ]
                           },
                           {
                               "type": "body",
                               "parameters": [
                                   {"type": "text", "text": record.partner_id.name},
                                   {"type": "text", "text": "*" + record.name + "*"},
                                   {"type": "text", "text": self.format_amount(record.amount_total, record.pricelist_id.currency_id)},

                               ]
                           },
                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_sale_order_without_order_details_signature_with_lines(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'sale_order_without_order_details_signature_with_lines_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id), ('default_template', '=', True)],
            limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            msg = ''
            line_count = 1
            for line_id in record.order_line:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.product_uom_qty and line_id.product_uom.name:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.product_uom_qty) + " " + str(line_id.product_uom.name)
                    if line_id.price_unit:
                        msg += "  *" + _("Unit Price") + ":* " + str(line_id.price_unit)
                    if line_id.price_subtotal:
                        msg += "  *" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                    line_count += 1
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [
                                   {
                                       "type": "document",
                                       "document":
                                           {"id": media_id, "filename": self.attachment_ids[0].name}
                                   }
                               ]
                           },
                           {
                               "type": "body",
                               "parameters": [{"type": "text", "text": record.partner_id.name}, {"type": "text", "text": msg}
                                              ]
                           },
                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_sale_order_without_lines_with_signature_order_details(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'sale_order_without_lines_with_signature_order_details_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [
                                   {
                                       "type": "document",
                                       "document":
                                           {"id": media_id, "filename": self.attachment_ids[0].name}
                                   }
                               ]
                           },
                           {
                               "type": "body",
                               "parameters": [
                                   {"type": "text", "text": record.partner_id.name},
                                   {"type": "text", "text": "*" + record.name + "*"},
                                   {"type": "text", "text": self.format_amount(record.amount_total, record.pricelist_id.currency_id)},
                               ]
                           },
                           {
                               "type": "footer",
                               "parameters": [{"type": "footer", "text": whatsapp_template_id.footer}]
                           },
                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_sale_order_without_order_details_with_signature_lines(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'sale_order_without_order_details_with_signature_lines_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id), ('default_template', '=', True)],
            limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            msg = ''
            line_count = 1
            for line_id in record.order_line:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.product_uom_qty and line_id.product_uom.name:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.product_uom_qty) + " " + str(line_id.product_uom.name)
                    if line_id.price_unit:
                        msg += "  *" + _("Unit Price") + ":* " + str(line_id.price_unit)
                    if line_id.price_subtotal:
                        msg += "  *" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                    line_count += 1
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [
                                   {
                                       "type": "document",
                                       "document":
                                           {"id": media_id, "filename": self.attachment_ids[0].name}
                                   }
                               ]
                           },
                           {
                               "type": "body",
                               "parameters": [
                                   {"type": "text", "text": record.partner_id.name}, {"type": "text", "text": msg}
                               ]
                           },
                           {
                               "type": "footer",
                               "parameters": [{"type": "footer", "text": whatsapp_template_id.footer}]
                           },
                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_sale_order_without_signature_with_order_details_lines(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'sale_order_without_signature_with_order_details_lines_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id), ('default_template', '=', True)],
            limit=1)
        if whatsapp_template_id.approval_state == 'approved' and media_id:
            msg = ''
            line_count = 1
            for line_id in record.order_line:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.product_uom_qty and line_id.product_uom.name:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.product_uom_qty) + " " + str(line_id.product_uom.name)
                    if line_id.price_unit:
                        msg += "  *" + _("Unit Price") + ":* " + str(line_id.price_unit)
                    if line_id.price_subtotal:
                        msg += "  *" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                    line_count += 1
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [
                                   {
                                       "type": "document",
                                       "document":
                                           {"id": media_id, "filename": self.attachment_ids[0].name}
                                   }
                               ]
                           },
                           {
                               "type": "body",
                               "parameters": [
                                   {"type": "text", "text": record.partner_id.name},
                                   {"type": "text", "text": "*" + record.name + "*"},
                                   {"type": "text", "text": self.format_amount(record.amount_total, record.pricelist_id.currency_id)},
                                   {"type": "text", "text": msg}
                               ]
                           },

                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_sale_order_with_signature_order_details_lines(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'sale_order_with_signature_order_details_lines_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)],
            limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            line_count = 1
            msg = ''
            for line_id in record.order_line:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.product_uom_qty and line_id.product_uom.name:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.product_uom_qty) + " " + str(line_id.product_uom.name)
                    if line_id.price_unit:
                        msg += "  *" + _("Unit Price") + ":* " + str(line_id.price_unit)
                    if line_id.price_subtotal:
                        msg += "  *" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                    line_count += 1
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [
                                   {
                                       "type": "document",
                                       "document":
                                           {"id": media_id, "filename": self.attachment_ids[0].name}
                                   }
                               ]
                           },
                           {
                               "type": "body",
                               "parameters": [
                                   {"type": "text", "text": record.partner_id.name},
                                   {"type": "text", "text": "*" + record.name + "*"},
                                   {"type": "text", "text": self.format_amount(record.amount_total, record.pricelist_id.currency_id)},
                                   {"type": "text", "text": msg}
                               ]
                           },
                           {
                               "type": "footer",
                               "parameters": [{"type": "footer", "text": self.cleanhtml(self.env.user.signature)}]
                           },

                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_account_invoice_without_invoice_details_lines_signature(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'account_invoice_without_invoice_details_lines_signature_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            payload = {
                "template": whatsapp_template_id.name,
                "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                "namespace": whatsapp_template_id.namespace,
                "params": [
                    {
                        "type": "header",
                        "parameters": [{
                            "type": "document",
                            "document": {"id": media_id, "filename": self.attachment_ids[0].name}
                        }]
                    },
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": record.partner_id.name}]
                    }
                ],
                "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
            }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_account_invoice_without_invoice_details_lines_with_signature(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'account_invoice_without_invoice_details_lines_with_signature_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [{
                                   "type": "document",
                                   "document": {"id": media_id, "filename": self.attachment_ids[0].name}
                               }]
                           },
                           {
                               "type": "body",
                               "parameters": [{"type": "text", "text": record.partner_id.name}]
                           },
                           {
                               "type": "footer",
                               "parameters": [{"type": "footer", "text": whatsapp_template_id.footer}]
                           },
                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_account_invoice_without_lines_signature_with_invoice_details(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'account_invoice_without_lines_signature_with_invoice_details_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [
                                   {
                                       "type": "document",
                                       "document":
                                           {"id": media_id, "filename": self.attachment_ids[0].name}
                                   }
                               ]
                           },
                           {
                               "type": "body",
                               "parameters": [
                                   {"type": "text", "text": record.partner_id.name},
                                   {"type": "text", "text": "*" + record.name + "*"},
                                   {"type": "text", "text": self.format_amount(record.amount_total, record.currency_id)},

                               ]
                           },
                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_account_invoice_without_invoice_details_signature_with_lines(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'account_invoice_without_invoice_details_signature_with_lines_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            msg = ''
            line_count = 1
            for line_id in record.invoice_line_ids:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.quantity:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.quantity)
                    if line_id.price_unit:
                        msg += "  *" + _("Unit Price") + ":* " + str(line_id.price_unit)
                    if line_id.price_subtotal:
                        msg += "  *" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                    line_count += 1
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [
                                   {
                                       "type": "document",
                                       "document":
                                           {"id": media_id, "filename": self.attachment_ids[0].name}
                                   }
                               ]
                           },
                           {
                               "type": "body",
                               "parameters": [{"type": "text", "text": record.partner_id.name}, {"type": "text", "text": msg}
                                              ]
                           },
                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_account_invoice_without_lines_with_signature_invoice_details(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'account_invoice_without_lines_with_signature_invoice_details_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [
                                   {
                                       "type": "document",
                                       "document":
                                           {"id": media_id, "filename": self.attachment_ids[0].name}
                                   }
                               ]
                           },
                           {
                               "type": "body",
                               "parameters": [
                                   {"type": "text", "text": record.partner_id.name},
                                   {"type": "text", "text": "*" + record.name + "*"},
                                   {"type": "text", "text": self.format_amount(record.amount_total, record.currency_id)},
                               ]
                           },
                           {
                               "type": "footer",
                               "parameters": [{"type": "footer", "text": whatsapp_template_id.footer}]
                           },
                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_account_invoice_without_invoice_details_with_signature_lines(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'account_invoice_without_invoice_details_with_signature_lines_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            msg = ''
            line_count = 1
            for line_id in record.invoice_line_ids:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.quantity:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.quantity)
                    if line_id.price_unit:
                        msg += "  *" + _("Unit Price") + ":* " + str(line_id.price_unit)
                    if line_id.price_subtotal:
                        msg += "  *" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                    line_count += 1
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [
                                   {
                                       "type": "document",
                                       "document":
                                           {"id": media_id, "filename": self.attachment_ids[0].name}
                                   }
                               ]
                           },
                           {
                               "type": "body",
                               "parameters": [
                                   {"type": "text", "text": record.partner_id.name}, {"type": "text", "text": msg}
                               ]
                           },
                           {
                               "type": "footer",
                               "parameters": [{"type": "footer", "text": whatsapp_template_id.footer}]
                           },
                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_account_invoice_without_signature_with_invoice_details_lines(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'account_invoice_without_signature_with_invoice_details_lines_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            msg = ''
            line_count = 1
            for line_id in record.invoice_line_ids:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.quantity:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.quantity)
                    if line_id.price_unit:
                        msg += "  *" + _("Unit Price") + ":* " + str(line_id.price_unit)
                    if line_id.price_subtotal:
                        msg += "  *" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                    line_count += 1
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [
                                   {
                                       "type": "document",
                                       "document":
                                           {"id": media_id, "filename": self.attachment_ids[0].name}
                                   }
                               ]
                           },
                           {
                               "type": "body",
                               "parameters": [
                                   {"type": "text", "text": record.partner_id.name},
                                   {"type": "text", "text": "*" + record.name + "*"},
                                   {"type": "text", "text": self.format_amount(record.amount_total, record.currency_id)},
                                   {"type": "text", "text": msg}
                               ]
                           },

                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_account_invoice_with_signature_invoice_details_lines(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'account_invoice_with_signature_invoice_details_lines_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            line_count = 1
            msg = ''
            for line_id in record.invoice_line_ids:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.quantity:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.quantity)
                    if line_id.price_unit:
                        msg += "  *" + _("Unit Price") + ":* " + str(line_id.price_unit)
                    if line_id.price_subtotal:
                        msg += "  *" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                    line_count += 1
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [
                                   {
                                       "type": "document",
                                       "document":
                                           {"id": media_id, "filename": self.attachment_ids[0].name}
                                   }
                               ]
                           },
                           {
                               "type": "body",
                               "parameters": [
                                   {"type": "text", "text": record.partner_id.name},
                                   {"type": "text", "text": "*" + record.name + "*"},
                                   {"type": "text", "text": self.format_amount(record.amount_total, record.currency_id)},
                                   {"type": "text", "text": msg}
                               ]
                           },
                           {
                               "type": "footer",
                               "parameters": [{"type": "footer", "text": self.cleanhtml(self.env.user.signature)}]
                           },

                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_delivery_order_without_order_details_lines_signature(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'delivery_order_without_order_details_lines_signature_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            payload = {
                "template": whatsapp_template_id.name,
                "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                "namespace": whatsapp_template_id.namespace,
                "params": [
                    {
                        "type": "header",
                        "parameters": [{
                            "type": "document",
                            "document": {"id": media_id, "filename": self.attachment_ids[0].name}
                        }]
                    },
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": record.partner_id.name}]
                    }
                ],
                "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
            }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_delivery_order_without_order_details_lines_with_signature(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'delivery_order_without_order_details_lines_with_signature_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [{
                                   "type": "document",
                                   "document": {"id": media_id, "filename": self.attachment_ids[0].name}
                               }]
                           },
                           {
                               "type": "body",
                               "parameters": [{"type": "text", "text": record.partner_id.name}]
                           },
                           {
                               "type": "footer",
                               "parameters": [{"type": "footer", "text": whatsapp_template_id.footer}]
                           },
                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_delivery_order_without_lines_signature_with_order_details(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'delivery_order_without_lines_signature_with_order_details_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [
                                   {
                                       "type": "document",
                                       "document":
                                           {"id": media_id, "filename": self.attachment_ids[0].name}
                                   }
                               ]
                           },
                           {
                               "type": "body",
                               "parameters": [
                                   {"type": "text", "text": record.partner_id.name},
                                   {"type": "text", "text": "*" + record.name + "*"},
                                   {"type": "text", "text": record.origin},

                               ]
                           },
                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_delivery_order_without_order_details_signature_with_lines(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'delivery_order_without_order_details_signature_with_lines_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            msg = ''
            line_count = 1
            for line_id in record.move_ids_without_package:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.product_uom_qty and line_id.product_uom:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.product_uom_qty) + " " + str(line_id.product_uom.name)
                    if line_id.quantity_done:
                        msg += "  *" + _("Done") + ":* " + str(line_id.quantity_done)
                    line_count += 1
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [
                                   {
                                       "type": "document",
                                       "document":
                                           {"id": media_id, "filename": self.attachment_ids[0].name}
                                   }
                               ]
                           },
                           {
                               "type": "body",
                               "parameters": [{"type": "text", "text": record.partner_id.name}, {"type": "text", "text": msg}
                                              ]
                           },
                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_delivery_order_without_lines_with_signature_order_details(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'delivery_order_without_lines_with_signature_order_details_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'approved' and media_id:
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [
                                   {
                                       "type": "document",
                                       "document":
                                           {"id": media_id, "filename": self.attachment_ids[0].name}
                                   }
                               ]
                           },
                           {
                               "type": "body",
                               "parameters": [
                                   {"type": "text", "text": record.partner_id.name},
                                   {"type": "text", "text": "*" + record.name + "*"},
                                   {"type": "text", "text": record.origin},
                               ]
                           },
                           {
                               "type": "footer",
                               "parameters": [{"type": "footer", "text": whatsapp_template_id.footer}]
                           },
                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_delivery_order_without_order_details_with_signature_lines(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'delivery_order_without_order_details_with_signature_lines_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            msg = ''
            line_count = 1
            for line_id in record.move_ids_without_package:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.product_uom_qty and line_id.product_uom:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.product_uom_qty) + " " + str(line_id.product_uom.name)
                    if line_id.quantity_done:
                        msg += "  *" + _("Done") + ":* " + str(line_id.quantity_done)
                    line_count += 1
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [
                                   {
                                       "type": "document",
                                       "document":
                                           {"id": media_id, "filename": self.attachment_ids[0].name}
                                   }
                               ]
                           },
                           {
                               "type": "body",
                               "parameters": [
                                   {"type": "text", "text": record.partner_id.name}, {"type": "text", "text": msg}
                               ]
                           },
                           {
                               "type": "footer",
                               "parameters": [{"type": "footer", "text": whatsapp_template_id.footer}]
                           },
                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_delivery_order_without_signature_with_order_details_lines(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'delivery_order_without_signature_with_order_details_lines_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            msg = ''
            line_count = 1
            for line_id in record.move_ids_without_package:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.product_uom_qty and line_id.product_uom:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.product_uom_qty) + " " + str(line_id.product_uom.name)
                    if line_id.quantity_done:
                        msg += "  *" + _("Done") + ":* " + str(line_id.quantity_done)
                    line_count += 1
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [
                                   {
                                       "type": "document",
                                       "document":
                                           {"id": media_id, "filename": self.attachment_ids[0].name}
                                   }
                               ]
                           },
                           {
                               "type": "body",
                               "parameters": [
                                   {"type": "text", "text": record.partner_id.name},
                                   {"type": "text", "text": "*" + record.name + "*"},
                                   {"type": "text", "text": record.origin},
                                   {"type": "text", "text": msg}
                               ]
                           },

                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_delivery_order_with_signature_order_details_lines(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'delivery_order_with_signature_order_details_lines_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)],
            limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            line_count = 1
            msg = ''
            for line_id in record.move_ids_without_package:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.product_uom_qty and line_id.product_uom:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.product_uom_qty) + " " + str(line_id.product_uom.name)
                    if line_id.quantity_done:
                        msg += "  *" + _("Done") + ":* " + str(line_id.quantity_done)
                    line_count += 1
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [
                                   {
                                       "type": "document",
                                       "document":
                                           {"id": media_id, "filename": self.attachment_ids[0].name}
                                   }
                               ]
                           },
                           {
                               "type": "body",
                               "parameters": [
                                   {"type": "text", "text": record.partner_id.name},
                                   {"type": "text", "text": "*" + record.name + "*"},
                                   {"type": "text", "text": record.origin},
                                   {"type": "text", "text": msg}
                               ]
                           },
                           {
                               "type": "footer",
                               "parameters": [{"type": "footer", "text": self.cleanhtml(self.env.user.signature)}]
                           },

                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_account_payment_without_payment_details_signature(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'account_payment_without_payment_details_signature_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)],
            limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            payload = {
                "template": whatsapp_template_id.name,
                "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                "namespace": whatsapp_template_id.namespace,
                "params": [
                    {
                        "type": "header",
                        "parameters": [{
                            "type": "document",
                            "document": {"id": media_id, "filename": self.attachment_ids[0].name}
                        }]
                    },
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": record.partner_id.name}]
                    }
                ],
                "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
            }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_account_payment_without_payment_details_with_signature(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'account_payment_without_payment_details_with_signature_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [{
                                   "type": "document",
                                   "document": {"id": media_id, "filename": self.attachment_ids[0].name}
                               }]
                           },
                           {
                               "type": "body",
                               "parameters": [{"type": "text", "text": record.partner_id.name}]
                           },
                           {
                               "type": "footer",
                               "parameters": [{"type": "footer", "text": whatsapp_template_id.footer}]
                           },
                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_account_payment_without_signature_with_payment_details(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'account_payment_without_signature_with_payment_details_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            record_ref = ''
            line_count = 1
            if record.ref:
                record_ref += record.ref
            else:
                record_ref += ''

            line_count += 1
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [
                                   {
                                       "type": "document",
                                       "document":
                                           {"id": media_id, "filename": self.attachment_ids[0].name}
                                   }
                               ]
                           },
                           {
                               "type": "body",
                               "parameters": [
                                   {"type": "text", "text": record.partner_id.name},
                                   {"type": "text", "text": "*" + record.name + "*"},
                                   {"type": "text", "text": self.format_amount(record.amount_total, record.currency_id)},
                                   {"type": "text", "text": record.payment_type},
                                   {"type": "text", "text": record.journal_id.name},
                                   {"type": "text", "text": str(record.date)},
                                   {"type": "text", "text": record_ref},
                               ]
                           },

                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_account_payment_with_signature_payment_details(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'account_payment_with_signature_payment_details_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)],
            limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            record_ref = ''
            line_count = 1
            if record.ref:
                record_ref += record.ref
            else:
                record_ref += ''

            line_count += 1
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [
                                   {
                                       "type": "document",
                                       "document":
                                           {"id": media_id, "filename": self.attachment_ids[0].name}
                                   }
                               ]
                           },
                           {
                               "type": "body",
                               "parameters": [
                                   {"type": "text", "text": record.partner_id.name},
                                   {"type": "text", "text": "*" + record.name + "*"},
                                   {"type": "text", "text": self.format_amount(record.amount_total, record.currency_id)},
                                   {"type": "text", "text": record.payment_type},
                                   {"type": "text", "text": record.journal_id.name},
                                   {"type": "text", "text": str(record.date)},
                                   {"type": "text", "text": record_ref},
                               ]
                           },
                           {
                               "type": "footer",
                               "parameters": [{"type": "footer", "text": whatsapp_template_id.footer}]
                           }
                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_purchase_order_without_order_details_lines_signature(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'purchase_order_without_order_details_lines_signature_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            payload = {
                "template": whatsapp_template_id.name,
                "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                "namespace": whatsapp_template_id.namespace,
                "params": [
                    {
                        "type": "header",
                        "parameters": [{
                            "type": "document",
                            "document": {"id": media_id, "filename": self.attachment_ids[0].name}
                        }]
                    },
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": record.partner_id.name}]
                    }
                ],
                "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
            }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_purchase_order_without_order_details_lines_with_signature(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'purchase_order_without_order_details_lines_with_signature_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [{
                                   "type": "document",
                                   "document": {"id": media_id, "filename": self.attachment_ids[0].name}
                               }]
                           },
                           {
                               "type": "body",
                               "parameters": [{"type": "text", "text": record.partner_id.name}]
                           },
                           {
                               "type": "footer",
                               "parameters": [{"type": "footer", "text": whatsapp_template_id.footer}]
                           },
                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_purchase_order_without_lines_signature_with_order_details(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'purchase_order_without_lines_signature_with_order_details_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [
                                   {
                                       "type": "document",
                                       "document":
                                           {"id": media_id, "filename": self.attachment_ids[0].name}
                                   }
                               ]
                           },
                           {
                               "type": "body",
                               "parameters": [
                                   {"type": "text", "text": record.partner_id.name},
                                   {"type": "text", "text": "*" + record.name + "*"},
                                   {"type": "text", "text": self.format_amount(record.amount_total, record.currency_id)},

                               ]
                           },
                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_purchase_order_without_order_details_signature_with_lines(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'purchase_order_without_order_details_signature_with_lines_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            msg = ''
            line_count = 1
            for line_id in record.order_line:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.product_qty and line_id.product_uom:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.product_qty) + " " + str(line_id.product_uom.name)
                    if line_id.price_unit:
                        msg += "  *" + _("Unit Price") + ":* " + str(line_id.price_unit)
                    if line_id.price_subtotal:
                        msg += "  *" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                    line_count += 1
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [
                                   {
                                       "type": "document",
                                       "document":
                                           {"id": media_id, "filename": self.attachment_ids[0].name}
                                   }
                               ]
                           },
                           {
                               "type": "body",
                               "parameters": [{"type": "text", "text": record.partner_id.name}, {"type": "text", "text": msg}
                                              ]
                           },
                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_purchase_order_without_lines_with_signature_order_details(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'purchase_order_without_lines_with_signature_order_details_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [
                                   {
                                       "type": "document",
                                       "document":
                                           {"id": media_id, "filename": self.attachment_ids[0].name}
                                   }
                               ]
                           },
                           {
                               "type": "body",
                               "parameters": [
                                   {"type": "text", "text": record.partner_id.name},
                                   {"type": "text", "text": "*" + record.name + "*"},
                                   {"type": "text", "text": self.format_amount(record.amount_total, record.currency_id)},
                               ]
                           },
                           {
                               "type": "footer",
                               "parameters": [{"type": "footer", "text": whatsapp_template_id.footer}]
                           },
                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_purchase_order_without_order_details_with_signature_lines(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'purchase_order_without_order_details_with_signature_lines_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            msg = ''
            line_count = 1
            for line_id in record.order_line:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.product_qty and line_id.product_uom:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.product_uom_qty) + " " + str(line_id.product_uom.name)
                    if line_id.price_unit:
                        msg += "  *" + _("Unit Price") + ":* " + str(line_id.price_unit)
                    if line_id.price_subtotal:
                        msg += "  *" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                    line_count += 1
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [
                                   {
                                       "type": "document",
                                       "document":
                                           {"id": media_id, "filename": self.attachment_ids[0].name}
                                   }
                               ]
                           },
                           {
                               "type": "body",
                               "parameters": [
                                   {"type": "text", "text": record.partner_id.name}, {"type": "text", "text": msg}
                               ]
                           },
                           {
                               "type": "footer",
                               "parameters": [{"type": "footer", "text": whatsapp_template_id.footer}]
                           },
                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_purchase_order_without_signature_with_order_details_lines(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'purchase_order_without_signature_with_order_details_lines_' + whatsapp_instance_id.sequence),
             ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)

        if whatsapp_template_id.approval_state == 'approved' and media_id:
            msg = ''
            line_count = 1
            for line_id in record.order_line:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.product_qty and line_id.product_uom:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.product_qty) + " " + str(line_id.product_uom.name)
                    if line_id.price_unit:
                        msg += "  *" + _("Unit Price") + ":* " + str(line_id.price_unit)
                    if line_id.price_subtotal:
                        msg += "  *" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                    line_count += 1
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [
                                   {
                                       "type": "document",
                                       "document":
                                           {"id": media_id, "filename": self.attachment_ids[0].name}
                                   }
                               ]
                           },
                           {
                               "type": "body",
                               "parameters": [
                                   {"type": "text", "text": record.partner_id.name},
                                   {"type": "text", "text": "*" + record.name + "*"},
                                   {"type": "text", "text": self.format_amount(record.amount_total, record.currency_id)},
                                   {"type": "text", "text": msg}
                               ]
                           },

                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def chat_api_template_purchase_order_with_signature_order_details_lines(self, url, headers, record, media_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'purchase_order_with_signature_order_details_lines_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)],
            limit=1)
        if whatsapp_template_id.approval_state == 'approved' and media_id:
            line_count = 1
            msg = ''
            for line_id in record.order_line:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.product_qty and line_id.product_uom:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.product_qty) + " " + str(line_id.product_uom.name)
                    if line_id.price_unit:
                        msg += "  *" + _("Unit Price") + ":* " + str(line_id.price_unit)
                    if line_id.price_subtotal:
                        msg += "  *" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                    line_count += 1
            payload = {"template": whatsapp_template_id.name,
                       "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                       "namespace": whatsapp_template_id.namespace,
                       "params": [
                           {
                               "type": "header",
                               "parameters": [
                                   {
                                       "type": "document",
                                       "document":
                                           {"id": media_id, "filename": self.attachment_ids[0].name}
                                   }
                               ]
                           },
                           {
                               "type": "body",
                               "parameters": [
                                   {"type": "text", "text": record.partner_id.name},
                                   {"type": "text", "text": "*" + record.name + "*"},
                                   {"type": "text", "text": self.format_amount(record.amount_total, record.currency_id)},
                                   {"type": "text", "text": msg}
                               ]
                           },
                           {
                               "type": "footer",
                               "parameters": [{"type": "footer", "text": self.cleanhtml(self.env.user.signature)}]
                           },

                       ],
                       "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
                       }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'rejected':
            self.template_errors(whatsapp_template_id)

    def get_media_id(self, attachment_id, whatsapp_instance_id):
        url_upload_media = whatsapp_instance_id.whatsapp_endpoint + '/uploadMedia?token=' + whatsapp_instance_id.whatsapp_token
        encoded_file = str(attachment_id.datas)
        media_payload = {"body": "data:" + attachment_id.mimetype + ";base64," + encoded_file[2:-1]}
        headers = {"Content-Type": "application/json"}
        response_media = requests.post(url_upload_media, data=json.dumps(media_payload), headers=headers)
        if response_media.status_code == 201 or response_media.status_code == 200:
            _logger.info("\nMedia Uploaded Successfully in whatsapp chat api")
            json_response_media_response = json.loads(response_media.text)
            return json_response_media_response.get('mediaId')

    def get_add_in_opt_in_user(self, whatsapp_instance_id, headers, number_without_code, record):
        opt_in_list_url = "https://api.gupshup.io/sm/api/v1/users/" + whatsapp_instance_id.whatsapp_gupshup_app_name
        opt_in_list_response = requests.get(opt_in_list_url, headers=headers)
        registered_numbers = [user['phoneCode'] for user in opt_in_list_response.json().get('users')]
        if number_without_code not in registered_numbers:
            opt_in_url = "https://api.gupshup.io/sm/api/v1/app/opt/in/" + whatsapp_instance_id.whatsapp_gupshup_app_name
            opt_in_response = requests.post(opt_in_url, data={'user': str(record.partner_id.country_id.phone_code) + number_without_code}, headers=headers)
            if opt_in_response.status_code == 202:
                _logger.info("\nOpt-in partner successfully")
        return True

    def add_message_in_chatter(self, record, active_model, attachment_id):
        mail_message_body = ''
        mail_message_body = """<p style='margin:0px; font-size:13px; font-family:"Lucida Grande", Helvetica, Verdana, Arial, sans-serif'><img src="/web_editor/font_to_img/62002/rgb(73,80,87)/13" data-class="fa fa-whatsapp" style="border-style:none; vertical-align:middle; height:auto; width:auto" width="0" height="0"></p>"""
        mail_message_body += self.message
        update_msg = self.convert_to_html(mail_message_body)
        body_mail_msg = "<br />".join(update_msg.split("\n"))
        mail_message_id = self.env['mail.message'].sudo().create({
            'res_id': record.id,
            'model': active_model,
            'body': body_mail_msg,
            'attachment_ids': [(4, attachment_id.id)],
        })
        mail_message_id.message_format()

    def create_whatsapp_message_for_template(self, mobile_with_country, message, message_id, chatId_message, whatsapp_instance_id, model, record, attachment_id):
        whatsapp_messages_dict = {
            'message_id': message_id,
            'name': message,
            'message_body': message,
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
            'attachment_id': attachment_id.id
        }
        if model == 'res.partner':
            whatsapp_messages_dict['partner_id'] = record.id
        else:
            if self._context.get('partner_id'):
                whatsapp_messages_dict['partner_id'] = self._context.get('partner_id')
            elif not model == 'mail.channel' and not model == 'odoo.group' and not model == 'whatsapp.marketing':
                if record.partner_id:
                    whatsapp_messages_dict['partner_id'] = record.partner_id.id

        whatsapp_messages_id = self.env['whatsapp.messages'].sudo().create(whatsapp_messages_dict)
        _logger.info("Whatsapp message created in odoo %s: ", str(whatsapp_messages_id.id))

    def template_errors(self, whatsapp_template_id):
        if whatsapp_template_id:
            if whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'PENDING' or whatsapp_template_id.approval_state == 'REJECTED' or whatsapp_template_id.approval_state == 'rejected':
                raise UserError(_('Template %s state is %s state. Please approve template from %s') % (
                    whatsapp_template_id.name, whatsapp_template_id.approval_state, whatsapp_template_id.provider))
            elif not whatsapp_template_id.approval_state and whatsapp_template_id.state == 'draft':
                raise UserError(_('Template %s is in %s state please export template') % whatsapp_template_id.approval_state, whatsapp_template_id.name)

        else:
            raise UserError(_('Template not found. Please click on Create Missing Templates from Whatsapp Instance'))

    def send_message_from_gupshup(self, whatsapp_instance_id):
        if whatsapp_instance_id.send_whatsapp_through_template:
            self.send_message_from_gupshup_through_template(whatsapp_instance_id)
        else:
            self.send_message_from_gupshup_without_template(whatsapp_instance_id)

    def send_message_from_gupshup_through_template(self, whatsapp_instance_id):
        active_model = self.env.context.get('active_model')
        if active_model == 'sale.order':
            self.gupshup_template_sale_order_send_template_message(whatsapp_instance_id)
        elif active_model == 'account.move':
            self.gupshup_template_account_invoice_send_template_message(whatsapp_instance_id)
        elif active_model == 'stock.picking':
            self.gupshup_template_delivery_order_send_template_message(whatsapp_instance_id)
        elif active_model == 'account.payment':
            self.gupshup_template_account_payment_send_template_message(whatsapp_instance_id)
        elif active_model == 'purchase.order':
            self.gupshup_template_purchase_order_send_template_message(whatsapp_instance_id)

    def send_message_from_gupshup_without_template(self, whatsapp_instance_id):
        for res_partner_id in self.partner_ids:
            if res_partner_id.country_id.phone_code and res_partner_id.mobile:
                whatsapp_number = res_partner_id.mobile
                whatsapp_msg_number_without_space = whatsapp_number.replace(" ", "")
                whatsapp_msg_number_without_plus = whatsapp_msg_number_without_space.replace('+', '')
                whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace('+' + str(res_partner_id.country_id.phone_code), "")
                whatsapp_msg_source_number = whatsapp_instance_id.gupshup_source_number
                headers = {"Content-Type": "application/x-www-form-urlencoded", "apikey": whatsapp_instance_id.whatsapp_gupshup_api_key}
                opt_in_list_url = "https://api.gupshup.io/sm/api/v1/users/" + whatsapp_instance_id.whatsapp_gupshup_app_name
                opt_in_list_response = requests.get(opt_in_list_url, headers=headers)
                registered_numbers = [user['phoneCode'] for user in opt_in_list_response.json().get('users')]
                if whatsapp_msg_number_without_code not in registered_numbers:
                    opt_in_url = "https://api.gupshup.io/sm/api/v1/app/opt/in/" + whatsapp_instance_id.whatsapp_gupshup_app_name
                    opt_in_response = requests.post(opt_in_url, data={'user': whatsapp_msg_number_without_plus}, headers=headers)
                temp_data = {
                    'channel': 'whatsapp',
                    'source': whatsapp_msg_source_number,
                    'destination': whatsapp_msg_number_without_plus,
                    'message': json.dumps({
                        'type': 'text',
                        'text': self.message
                    })
                }
                url = 'https://api.gupshup.io/sm/api/v1/msg'
                response = requests.post(url, headers=headers, data=temp_data)
                if response.status_code in [202, 201, 200]:
                    _logger.info("\nSend Message successfully")
                    json_response = json.loads(response.text)
                    active_model = self.env.context.get('active_model')
                    record = self.env[active_model].browse(self.env.context.get('active_id'))
                    self.env['whatsapp.msg.res.partner'].with_context({'partner_id': res_partner_id.id}).gupshup_create_whatsapp_message(
                        whatsapp_msg_number_without_plus, self.message, json_response.get('messageId'), whatsapp_instance_id, active_model,
                        record, self.attachment_ids[0])
                    if self.attachment_ids:
                        for attachment in self.attachment_ids:
                            attachment_data = False
                            if attachment.mimetype in ['image/jpeg', 'image/png']:
                                attachment_data = {
                                    'channel': 'whatsapp',
                                    'source': whatsapp_msg_source_number,
                                    'destination': whatsapp_msg_number_without_plus,
                                    'message': json.dumps({
                                        'type': 'image',
                                        'originalUrl': attachment.public_url,
                                        'caption': attachment.name
                                    })
                                }
                            elif attachment.mimetype in ['audio/aac', 'audio/mp4', 'audio/amr', 'audio/mpeg']:
                                attachment_data = {
                                    'channel': 'whatsapp',
                                    'source': whatsapp_msg_source_number,
                                    'destination': whatsapp_msg_number_without_plus,
                                    'message': json.dumps({
                                        'type': 'audio',
                                        'url': attachment.public_url,
                                    })
                                }
                            elif attachment.mimetype in ['video/mp4', 'video/3gpp']:
                                attachment_data = {
                                    'channel': 'whatsapp',
                                    'source': whatsapp_msg_source_number,
                                    'destination': whatsapp_msg_number_without_plus,
                                    'message': json.dumps({
                                        'type': 'video',
                                        'url': attachment.public_url,
                                        'caption': attachment.name
                                    })
                                }
                            else:
                                attachment_data = {
                                    'channel': 'whatsapp',
                                    'source': whatsapp_msg_source_number,
                                    'destination': whatsapp_msg_number_without_plus,
                                    'message': json.dumps({
                                        'type': 'file',
                                        'url': attachment.public_url,
                                        'filename': attachment.name
                                    })
                                }
                            attachment_url = 'https://api.gupshup.io/sm/api/v1/msg'
                            att_response = requests.post(attachment_url, headers=headers, data=attachment_data)
                            if att_response.status_code in [202, 201, 200]:
                                _logger.info("\nSend Attachment successfully")
                                json_response = json.loads(response.text)

                                self.env['whatsapp.msg.res.partner'].gupshup_create_whatsapp_message_for_attachment(whatsapp_msg_number_without_plus, attachment, json_response.get('messageId'),
                                                                                    attachment.mimetype,
                                                                                    whatsapp_instance_id, active_model, record)

    def gupshup_template_sale_order_send_template_message(self, whatsapp_instance_id):
        url = 'https://api.gupshup.io/sm/api/v1/template/msg'
        headers = {"Content-Type": "application/x-www-form-urlencoded", "apikey": whatsapp_instance_id.whatsapp_gupshup_api_key}
        active_model = self.env.context.get('active_model')
        record = self.env[active_model].browse(self.env.context.get('active_id'))
        if record.partner_id.mobile and record.partner_id.country_id:
            whatsapp_number = record.partner_id.mobile
            whatsapp_msg_number_without_space = whatsapp_number.replace(" ", "")
            number_without_code = ''
            if '+' in whatsapp_msg_number_without_space:
                number_without_code = whatsapp_msg_number_without_space.replace('+' + str(record.partner_id.country_id.phone_code), "")
            else:
                number_without_code = whatsapp_msg_number_without_space.replace(str(record.partner_id.country_id.phone_code), "")

            self.get_add_in_opt_in_user(whatsapp_instance_id, headers, number_without_code, record)

            response = None
            if self.attachment_ids:
                if not whatsapp_instance_id.sale_order_add_signature and not whatsapp_instance_id.sale_order_add_order_product_details and not whatsapp_instance_id.sale_order_add_order_info_msg:
                    response = self.gupshup_template_sale_order_without_order_details_lines_signature(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                      whatsapp_instance_id)
                elif whatsapp_instance_id.sale_order_add_signature and not whatsapp_instance_id.sale_order_add_order_product_details and not whatsapp_instance_id.sale_order_add_order_info_msg:
                    response = self.gupshup_template_sale_order_without_order_details_lines_with_signature(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                           whatsapp_instance_id)
                elif not whatsapp_instance_id.sale_order_add_signature and not whatsapp_instance_id.sale_order_add_order_product_details and whatsapp_instance_id.sale_order_add_order_info_msg:
                    response = self.gupshup_template_sale_order_without_lines_signature_with_order_details(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                           whatsapp_instance_id)
                elif not whatsapp_instance_id.sale_order_add_signature and whatsapp_instance_id.sale_order_add_order_product_details and not whatsapp_instance_id.sale_order_add_order_info_msg:
                    response = self.gupshup_template_sale_order_without_order_details_signature_with_lines(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                           whatsapp_instance_id)
                elif whatsapp_instance_id.sale_order_add_signature and not whatsapp_instance_id.sale_order_add_order_product_details and whatsapp_instance_id.sale_order_add_order_info_msg:
                    response = self.gupshup_template_sale_order_without_lines_with_signature_order_details(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                           whatsapp_instance_id)
                elif whatsapp_instance_id.sale_order_add_signature and whatsapp_instance_id.sale_order_add_order_product_details and not whatsapp_instance_id.sale_order_add_order_info_msg:
                    response = self.gupshup_template_sale_order_without_order_details_with_signature_lines(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                           whatsapp_instance_id)
                elif not whatsapp_instance_id.sale_order_add_signature and whatsapp_instance_id.sale_order_add_order_product_details and whatsapp_instance_id.sale_order_add_order_info_msg:
                    response = self.gupshup_template_sale_order_without_signature_with_order_details_lines(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                           whatsapp_instance_id)
                elif whatsapp_instance_id.sale_order_add_signature and whatsapp_instance_id.sale_order_add_order_product_details and whatsapp_instance_id.sale_order_add_order_info_msg:
                    response = self.gupshup_template_sale_order_with_signature_order_details_lines(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                   whatsapp_instance_id)
            if response.status_code == 201 or response.status_code == 200 or response.status_code == 202:
                json_response = json.loads(response.text)
                self.env['whatsapp.msg.res.partner'].with_context({'partner_id': record.partner_id.id}).gupshup_create_whatsapp_message(
                    str(record.partner_id.country_id.phone_code) + number_without_code, self.message, json_response.get('messageId'), whatsapp_instance_id, 'sale.order',
                    record, self.attachment_ids[0])
                if whatsapp_instance_id.sale_order_add_message_in_chatter:
                    self.add_message_in_chatter(record, active_model, self.attachment_ids[0])
        return True

    def gupshup_template_sale_order_without_order_details_lines_signature(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'sale_order_without_order_details_lines_signature_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps({"id": whatsapp_template_id.template_id, "params": [record.partner_id.name]}),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_sale_order_without_order_details_lines_with_signature(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'sale_order_without_order_details_lines_with_signature_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            instance_signature = ''
            if whatsapp_instance_id.signature:
                instance_signature = whatsapp_instance_id.signature
            else:
                instance_signature = self.env.user.company_id.name
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            instance_signature
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_sale_order_without_lines_signature_with_order_details(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'sale_order_without_lines_signature_with_order_details_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            instance_signature = ''
            if whatsapp_instance_id.signature:
                instance_signature = whatsapp_instance_id.signature
            else:
                instance_signature = self.env.user.company_id.name
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            record.name,
                            self.format_amount(record.amount_total, record.pricelist_id.currency_id)
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_sale_order_without_order_details_signature_with_lines(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'sale_order_without_order_details_signature_with_lines_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            msg = ''
            line_count = 1
            for line_id in record.order_line:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.product_uom_qty and line_id.product_uom.name:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.product_uom_qty) + " " + str(line_id.product_uom.name)
                    if line_id.price_unit:
                        msg += "  *" + _("Unit Price") + ":* " + str(line_id.price_unit)
                    if line_id.price_subtotal:
                        msg += "  *" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                    line_count += 1
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            msg
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_sale_order_without_lines_with_signature_order_details(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'sale_order_without_lines_with_signature_order_details_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            instance_signature = ''
            if whatsapp_instance_id.signature:
                instance_signature = whatsapp_instance_id.signature
            else:
                instance_signature = self.env.user.company_id.name
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            record.name,
                            self.format_amount(record.amount_total, record.pricelist_id.currency_id),
                            instance_signature
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_sale_order_without_order_details_with_signature_lines(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'sale_order_without_lines_with_signature_order_details_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            instance_signature = ''
            if whatsapp_instance_id.signature:
                instance_signature = whatsapp_instance_id.signature
            else:
                instance_signature = self.env.user.company_id.name
            msg = ''
            line_count = 1
            for line_id in record.order_line:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.product_uom_qty and line_id.product_uom.name:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.product_uom_qty) + " " + str(line_id.product_uom.name)
                    if line_id.price_unit:
                        msg += "  *" + _("Unit Price") + ":* " + str(line_id.price_unit)
                    if line_id.price_subtotal:
                        msg += "  *" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                    line_count += 1

            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            msg,
                            instance_signature
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_sale_order_without_signature_with_order_details_lines(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'sale_order_without_signature_with_order_details_lines_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            msg = ''
            line_count = 1
            for line_id in record.order_line:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.product_uom_qty and line_id.product_uom.name:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.product_uom_qty) + " " + str(line_id.product_uom.name)
                    if line_id.price_unit:
                        msg += "  *" + _("Unit Price") + ":* " + str(line_id.price_unit)
                    if line_id.price_subtotal:
                        msg += "  *" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                    line_count += 1

            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            record.name,
                            self.format_amount(record.amount_total, record.pricelist_id.currency_id),
                            msg,
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_sale_order_with_signature_order_details_lines(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'sale_order_with_signature_order_details_lines_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            msg = ''
            line_count = 1
            for line_id in record.order_line:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.product_uom_qty and line_id.product_uom.name:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.product_uom_qty) + " " + str(line_id.product_uom.name)
                    if line_id.price_unit:
                        msg += "  *" + _("Unit Price") + ":* " + str(line_id.price_unit)
                    if line_id.price_subtotal:
                        msg += "  *" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                    line_count += 1
            instance_signature = ''
            if whatsapp_instance_id.signature:
                instance_signature = whatsapp_instance_id.signature
            else:
                instance_signature = self.env.user.company_id.name
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            record.name,
                            self.format_amount(record.amount_total, record.pricelist_id.currency_id),
                            msg,
                            instance_signature
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_account_invoice_send_template_message(self, whatsapp_instance_id):
        url = 'https://api.gupshup.io/sm/api/v1/template/msg'
        headers = {"Content-Type": "application/x-www-form-urlencoded", "apikey": whatsapp_instance_id.whatsapp_gupshup_api_key}
        active_model = self.env.context.get('active_model')
        record = self.env[active_model].browse(self.env.context.get('active_id'))
        if record.partner_id.mobile and record.partner_id.country_id:
            whatsapp_number = record.partner_id.mobile
            whatsapp_msg_number_without_space = whatsapp_number.replace(" ", "")
            number_without_code = ''
            if '+' in whatsapp_msg_number_without_space:
                number_without_code = whatsapp_msg_number_without_space.replace('+' + str(record.partner_id.country_id.phone_code), "")
            else:
                number_without_code = whatsapp_msg_number_without_space.replace(str(record.partner_id.country_id.phone_code), "")

            self.get_add_in_opt_in_user(whatsapp_instance_id, headers, number_without_code, record)

            response = None
            if self.attachment_ids:
                if not whatsapp_instance_id.account_invoice_add_signature and not whatsapp_instance_id.account_invoice_add_invoice_product_details and not whatsapp_instance_id.account_invoice_add_invoice_info_msg:
                    response = self.gupshup_template_account_invoice_without_invoice_details_lines_signature(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                             whatsapp_instance_id)
                elif whatsapp_instance_id.account_invoice_add_signature and not whatsapp_instance_id.account_invoice_add_invoice_product_details and not whatsapp_instance_id.account_invoice_add_invoice_info_msg:
                    response = self.gupshup_template_account_invoice_without_invoice_details_lines_with_signature(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                                  whatsapp_instance_id)
                elif not whatsapp_instance_id.account_invoice_add_signature and not whatsapp_instance_id.account_invoice_add_invoice_product_details and whatsapp_instance_id.account_invoice_add_invoice_info_msg:
                    response = self.gupshup_template_account_invoice_without_lines_signature_with_invoice_details(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                                  whatsapp_instance_id)
                elif not whatsapp_instance_id.account_invoice_add_signature and whatsapp_instance_id.account_invoice_add_invoice_product_details and not whatsapp_instance_id.account_invoice_add_invoice_info_msg:
                    response = self.gupshup_template_account_invoice_without_invoice_details_signature_with_lines(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                                  whatsapp_instance_id)
                elif whatsapp_instance_id.account_invoice_add_signature and not whatsapp_instance_id.account_invoice_add_invoice_product_details and whatsapp_instance_id.account_invoice_add_invoice_info_msg:
                    response = self.gupshup_template_account_invoice_without_lines_with_signature_invoice_details(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                                  whatsapp_instance_id)
                elif whatsapp_instance_id.account_invoice_add_signature and whatsapp_instance_id.account_invoice_add_invoice_product_details and not whatsapp_instance_id.account_invoice_add_invoice_info_msg:
                    response = self.gupshup_template_account_invoice_without_invoice_details_with_signature_lines(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                                  whatsapp_instance_id)
                elif not whatsapp_instance_id.account_invoice_add_signature and whatsapp_instance_id.account_invoice_add_invoice_product_details and whatsapp_instance_id.account_invoice_add_invoice_info_msg:
                    response = self.gupshup_template_account_invoice_without_signature_with_invoice_details_lines(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                                  whatsapp_instance_id)
                elif whatsapp_instance_id.account_invoice_add_signature and whatsapp_instance_id.account_invoice_add_invoice_product_details and whatsapp_instance_id.account_invoice_add_invoice_info_msg:
                    response = self.gupshup_template_account_invoice_with_signature_invoice_details_lines(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                          whatsapp_instance_id)

            if response.status_code == 201 or response.status_code == 200 or response.status_code == 202:
                json_response = json.loads(response.text)
                self.env['whatsapp.msg.res.partner'].with_context({'partner_id': record.partner_id.id}).gupshup_create_whatsapp_message(
                    str(record.partner_id.country_id.phone_code) + number_without_code, self.message, json_response.get('messageId'), whatsapp_instance_id, 'sale.order',
                    record, self.attachment_ids[0])
                if whatsapp_instance_id.account_invoice_add_message_in_chatter:
                    self.add_message_in_chatter(record, active_model, self.attachment_ids[0])
        return True

    def gupshup_template_account_invoice_without_invoice_details_lines_signature(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'account_invoice_without_invoice_details_lines_signature_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps({"id": whatsapp_template_id.template_id, "params": [record.partner_id.name]}),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_account_invoice_without_invoice_details_lines_with_signature(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'account_invoice_without_invoice_details_lines_with_signature_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            instance_signature = ''
            if whatsapp_instance_id.signature:
                instance_signature = whatsapp_instance_id.signature
            else:
                instance_signature = self.env.user.company_id.name
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            instance_signature
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_account_invoice_without_lines_signature_with_invoice_details(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'account_invoice_without_lines_signature_with_invoice_details_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            record.name,
                            self.format_amount(record.amount_total, record.currency_id)
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_account_invoice_without_invoice_details_signature_with_lines(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'account_invoice_without_invoice_details_signature_with_lines_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            msg = ''
            line_count = 1
            for line_id in record.invoice_line_ids:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.quantity:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.quantity)
                    if line_id.price_unit:
                        msg += "  *" + _("Unit Price") + ":* " + str(line_id.price_unit)
                    if line_id.price_subtotal:
                        msg += "  *" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                    line_count += 1
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            msg
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_account_invoice_without_lines_with_signature_invoice_details(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'sale_order_without_lines_with_signature_order_details_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            instance_signature = ''
            if whatsapp_instance_id.signature:
                instance_signature = whatsapp_instance_id.signature
            else:
                instance_signature = self.env.user.company_id.name
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            record.name,
                            self.format_amount(record.amount_total, record.currency_id),
                            instance_signature
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_account_invoice_without_invoice_details_with_signature_lines(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'account_invoice_without_invoice_details_with_signature_lines_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            instance_signature = ''
            if whatsapp_instance_id.signature:
                instance_signature = whatsapp_instance_id.signature
            else:
                instance_signature = self.env.user.company_id.name
            msg = ''
            line_count = 1
            for line_id in record.invoice_line_ids:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.quantity:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.quantity)
                    if line_id.price_unit:
                        msg += "  *" + _("Unit Price") + ":* " + str(line_id.price_unit)
                    if line_id.price_subtotal:
                        msg += "  *" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                    line_count += 1

            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            msg,
                            instance_signature
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_account_invoice_without_signature_with_invoice_details_lines(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'account_invoice_without_signature_with_invoice_details_lines_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            msg = ''
            line_count = 1
            for line_id in record.invoice_line_ids:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.quantity:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.quantity)
                    if line_id.price_unit:
                        msg += "  *" + _("Unit Price") + ":* " + str(line_id.price_unit)
                    if line_id.price_subtotal:
                        msg += "  *" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                    line_count += 1

            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            record.name,
                            self.format_amount(record.amount_total, record.currency_id),
                            msg,
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_account_invoice_with_signature_invoice_details_lines(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'account_invoice_with_signature_invoice_details_lines_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            line_count = 1
            msg = ''
            for line_id in record.invoice_line_ids:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.quantity:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.quantity)
                    if line_id.price_unit:
                        msg += "  *" + _("Unit Price") + ":* " + str(line_id.price_unit)
                    if line_id.price_subtotal:
                        msg += "  *" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                    line_count += 1
            instance_signature = ''
            if whatsapp_instance_id.signature:
                instance_signature = whatsapp_instance_id.signature
            else:
                instance_signature = self.env.user.company_id.name
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            record.name,
                            self.format_amount(record.amount_total, record.currency_id),
                            msg,
                            instance_signature
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_delivery_order_send_template_message(self, whatsapp_instance_id):
        url = 'https://api.gupshup.io/sm/api/v1/template/msg'
        headers = {"Content-Type": "application/x-www-form-urlencoded", "apikey": whatsapp_instance_id.whatsapp_gupshup_api_key}
        active_model = self.env.context.get('active_model')
        record = self.env[active_model].browse(self.env.context.get('active_id'))
        if record.partner_id.mobile and record.partner_id.country_id:
            whatsapp_number = record.partner_id.mobile
            whatsapp_msg_number_without_space = whatsapp_number.replace(" ", "")
            number_without_code = ''
            if '+' in whatsapp_msg_number_without_space:
                number_without_code = whatsapp_msg_number_without_space.replace('+' + str(record.partner_id.country_id.phone_code), "")
            else:
                number_without_code = whatsapp_msg_number_without_space.replace(str(record.partner_id.country_id.phone_code), "")

            self.get_add_in_opt_in_user(whatsapp_instance_id, headers, number_without_code, record)

            response = None
            if self.attachment_ids:
                if not whatsapp_instance_id.delivery_order_add_signature and not whatsapp_instance_id.delivery_order_add_order_product_details and not whatsapp_instance_id.delivery_order_add_order_info_msg:
                    response = self.gupshup_template_delivery_order_without_order_details_lines_signature(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                          whatsapp_instance_id)
                elif whatsapp_instance_id.delivery_order_add_signature and not whatsapp_instance_id.delivery_order_add_order_product_details and not whatsapp_instance_id.delivery_order_add_order_info_msg:
                    response = self.gupshup_template_delivery_order_without_order_details_lines_with_signature(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                               whatsapp_instance_id)
                elif not whatsapp_instance_id.delivery_order_add_signature and not whatsapp_instance_id.delivery_order_add_order_product_details and whatsapp_instance_id.delivery_order_add_order_info_msg:
                    response = self.gupshup_template_delivery_order_without_lines_signature_with_order_details(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                               whatsapp_instance_id)
                elif not whatsapp_instance_id.delivery_order_add_signature and whatsapp_instance_id.delivery_order_add_order_product_details and not whatsapp_instance_id.delivery_order_add_order_info_msg:
                    response = self.gupshup_template_delivery_order_without_order_details_signature_with_lines(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                               whatsapp_instance_id)
                elif whatsapp_instance_id.delivery_order_add_signature and not whatsapp_instance_id.delivery_order_add_order_product_details and whatsapp_instance_id.delivery_order_add_order_info_msg:
                    response = self.gupshup_template_delivery_order_without_lines_with_signature_order_details(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                               whatsapp_instance_id)
                elif whatsapp_instance_id.delivery_order_add_signature and whatsapp_instance_id.delivery_order_add_order_product_details and not whatsapp_instance_id.delivery_order_add_order_info_msg:
                    response = self.gupshup_template_delivery_order_without_order_details_with_signature_lines(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                               whatsapp_instance_id)
                elif not whatsapp_instance_id.delivery_order_add_signature and whatsapp_instance_id.delivery_order_add_order_product_details and whatsapp_instance_id.delivery_order_add_order_info_msg:
                    response = self.gupshup_template_delivery_order_without_signature_with_order_details_lines(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                               whatsapp_instance_id)
                elif whatsapp_instance_id.delivery_order_add_signature and whatsapp_instance_id.delivery_order_add_order_product_details and whatsapp_instance_id.delivery_order_add_order_info_msg:
                    response = self.gupshup_template_delivery_order_with_signature_order_details_lines(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                       whatsapp_instance_id)
            if response.status_code == 201 or response.status_code == 200 or response.status_code == 202:
                json_response = json.loads(response.text)
                self.env['whatsapp.msg.res.partner'].with_context({'partner_id': record.partner_id.id}).gupshup_create_whatsapp_message(
                    str(record.partner_id.country_id.phone_code) + number_without_code, self.message, json_response.get('messageId'), whatsapp_instance_id, 'sale.order',
                    record, self.attachment_ids[0])
                if whatsapp_instance_id.delivery_order_add_message_in_chatter:
                    self.add_message_in_chatter(record, active_model, self.attachment_ids[0])
        return True

    def gupshup_template_delivery_order_without_order_details_lines_signature(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'delivery_order_without_order_details_lines_signature_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps({"id": whatsapp_template_id.template_id, "params": [record.partner_id.name]}),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_delivery_order_without_order_details_lines_with_signature(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'delivery_order_without_order_details_lines_with_signature_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            instance_signature = ''
            if whatsapp_instance_id.signature:
                instance_signature = whatsapp_instance_id.signature
            else:
                instance_signature = self.env.user.company_id.name
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            instance_signature
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_delivery_order_without_lines_signature_with_order_details(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'delivery_order_without_lines_signature_with_order_details_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            instance_signature = ''
            if whatsapp_instance_id.signature:
                instance_signature = whatsapp_instance_id.signature
            else:
                instance_signature = self.env.user.company_id.name
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            record.name,
                            record.origin
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_delivery_order_without_order_details_signature_with_lines(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'sale_order_without_order_details_signature_with_lines_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            msg = ''
            line_count = 1
            for line_id in record.move_ids_without_package:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.product_uom_qty and line_id.product_uom:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.product_uom_qty) + " " + str(line_id.product_uom.name)
                    if line_id.quantity_done:
                        msg += "  *" + _("Done") + ":* " + str(line_id.quantity_done)
                    line_count += 1
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            msg
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_delivery_order_without_lines_with_signature_order_details(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'delivery_order_without_lines_with_signature_order_details_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            instance_signature = ''
            if whatsapp_instance_id.signature:
                instance_signature = whatsapp_instance_id.signature
            else:
                instance_signature = self.env.user.company_id.name
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            record.name,
                            record.origin,
                            instance_signature
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_delivery_order_without_order_details_with_signature_lines(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'delivery_order_without_order_details_with_signature_lines_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            instance_signature = ''
            if whatsapp_instance_id.signature:
                instance_signature = whatsapp_instance_id.signature
            else:
                instance_signature = self.env.user.company_id.name
            msg = ''
            line_count = 1
            for line_id in record.move_ids_without_package:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.product_uom_qty and line_id.product_uom:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.product_uom_qty) + " " + str(line_id.product_uom.name)
                    if line_id.quantity_done:
                        msg += "  *" + _("Done") + ":* " + str(line_id.quantity_done)
                    line_count += 1

            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            msg,
                            instance_signature
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_delivery_order_without_signature_with_order_details_lines(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'delivery_order_without_signature_with_order_details_lines_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            msg = ''
            line_count = 1
            for line_id in record.move_ids_without_package:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.product_uom_qty and line_id.product_uom:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.product_uom_qty) + " " + str(line_id.product_uom.name)
                    if line_id.quantity_done:
                        msg += "  *" + _("Done") + ":* " + str(line_id.quantity_done)
                    line_count += 1

            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            record.name,
                            record.origin,
                            msg,
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_delivery_order_with_signature_order_details_lines(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'delivery_order_with_signature_order_details_lines_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            line_count = 1
            msg = ''
            for line_id in record.move_ids_without_package:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.product_uom_qty and line_id.product_uom:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.product_uom_qty) + " " + str(line_id.product_uom.name)
                    if line_id.quantity_done:
                        msg += "  *" + _("Done") + ":* " + str(line_id.quantity_done)
                    line_count += 1
            instance_signature = ''
            if whatsapp_instance_id.signature:
                instance_signature = whatsapp_instance_id.signature
            else:
                instance_signature = self.env.user.company_id.name
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            record.name,
                            record.origin,
                            msg,
                            instance_signature
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_account_payment_send_template_message(self, whatsapp_instance_id):
        url = 'https://api.gupshup.io/sm/api/v1/template/msg'
        headers = {"Content-Type": "application/x-www-form-urlencoded", "apikey": whatsapp_instance_id.whatsapp_gupshup_api_key}
        active_model = self.env.context.get('active_model')
        record = self.env[active_model].browse(self.env.context.get('active_id'))
        if record.partner_id.mobile and record.partner_id.country_id:
            whatsapp_number = record.partner_id.mobile
            whatsapp_msg_number_without_space = whatsapp_number.replace(" ", "")
            number_without_code = ''
            if '+' in whatsapp_msg_number_without_space:
                number_without_code = whatsapp_msg_number_without_space.replace('+' + str(record.partner_id.country_id.phone_code), "")
            else:
                number_without_code = whatsapp_msg_number_without_space.replace(str(record.partner_id.country_id.phone_code), "")

            self.get_add_in_opt_in_user(whatsapp_instance_id, headers, number_without_code, record)

            response = None
            if self.attachment_ids:
                if not whatsapp_instance_id.account_invoice_add_signature and not whatsapp_instance_id.account_payment_details:
                    response = self.gupshup_template_account_payment_without_payment_details_signature(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                       whatsapp_instance_id)
                elif whatsapp_instance_id.account_invoice_add_signature and not whatsapp_instance_id.account_payment_details:
                    response = self.gupshup_template_account_payment_without_payment_details_with_signature(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                            whatsapp_instance_id)
                elif not whatsapp_instance_id.account_invoice_add_signature and whatsapp_instance_id.account_payment_details:
                    response = self.gupshup_template_account_payment_without_signature_with_payment_details(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                            whatsapp_instance_id)
                elif whatsapp_instance_id.account_invoice_add_signature and whatsapp_instance_id.account_payment_details:
                    response = self.gupshup_template_account_payment_with_signature_payment_details(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                    whatsapp_instance_id)

            if response.status_code == 201 or response.status_code == 200 or response.status_code == 202:
                json_response = json.loads(response.text)
                self.env['whatsapp.msg.res.partner'].with_context({'partner_id': record.partner_id.id}).gupshup_create_whatsapp_message(
                    str(record.partner_id.country_id.phone_code) + number_without_code, self.message, json_response.get('messageId'), whatsapp_instance_id, 'sale.order',
                    record, self.attachment_ids[0])
                if whatsapp_instance_id.account_invoice_add_message_in_chatter:
                    self.add_message_in_chatter(record, active_model, self.attachment_ids[0])
        return True

    def gupshup_template_account_payment_without_payment_details_signature(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'account_payment_without_payment_details_signature_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps({"id": whatsapp_template_id.template_id, "params": [record.partner_id.name]}),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_account_payment_without_payment_details_with_signature(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'account_payment_without_payment_details_with_signature_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            instance_signature = ''
            if whatsapp_instance_id.signature:
                instance_signature = whatsapp_instance_id.signature
            else:
                instance_signature = self.env.user.company_id.name
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            instance_signature
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_account_payment_without_signature_with_payment_details(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'account_payment_without_signature_with_payment_details_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            record_ref = ''
            line_count = 1
            if record.ref:
                record_ref += record.ref
            else:
                record_ref += ''

            line_count += 1
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            record.name,
                            self.format_amount(record.amount_total, record.currency_id),
                            record.payment_type,
                            record.journal_id.name,
                            str(record.date),
                            record_ref
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_account_payment_with_signature_payment_details(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'account_payment_with_signature_payment_details_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            instance_signature = ''
            if whatsapp_instance_id.signature:
                instance_signature = whatsapp_instance_id.signature
            else:
                instance_signature = self.env.user.company_id.name
            record_ref = ''
            line_count = 1
            if record.ref:
                record_ref += record.ref
            else:
                record_ref += ''

            line_count += 1
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            record.name,
                            self.format_amount(record.amount_total, record.currency_id),
                            record.payment_type,
                            record.journal_id.name,
                            str(record.date),
                            record_ref,
                            instance_signature
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_purchase_order_send_template_message(self, whatsapp_instance_id):
        url = 'https://api.gupshup.io/sm/api/v1/template/msg'
        headers = {"Content-Type": "application/x-www-form-urlencoded", "apikey": whatsapp_instance_id.whatsapp_gupshup_api_key}
        active_model = self.env.context.get('active_model')
        record = self.env[active_model].browse(self.env.context.get('active_id'))
        if record.partner_id.mobile and record.partner_id.country_id:
            whatsapp_number = record.partner_id.mobile
            whatsapp_msg_number_without_space = whatsapp_number.replace(" ", "")
            number_without_code = ''
            if '+' in whatsapp_msg_number_without_space:
                number_without_code = whatsapp_msg_number_without_space.replace('+' + str(record.partner_id.country_id.phone_code), "")
            else:
                number_without_code = whatsapp_msg_number_without_space.replace(str(record.partner_id.country_id.phone_code), "")

            self.get_add_in_opt_in_user(whatsapp_instance_id, headers, number_without_code, record)

            response = None
            if self.attachment_ids:
                if not whatsapp_instance_id.purchase_order_add_signature and not whatsapp_instance_id.purchase_order_add_order_product_details and not whatsapp_instance_id.purchase_order_add_order_info_msg:
                    response = self.gupshup_template_purchase_order_without_order_details_lines_signature(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                          whatsapp_instance_id)
                elif whatsapp_instance_id.purchase_order_add_signature and not whatsapp_instance_id.purchase_order_add_order_product_details and not whatsapp_instance_id.purchase_order_add_order_info_msg:
                    response = self.gupshup_template_purchase_order_without_order_details_lines_with_signature(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                               whatsapp_instance_id)
                elif not whatsapp_instance_id.purchase_order_add_signature and not whatsapp_instance_id.purchase_order_add_order_product_details and whatsapp_instance_id.purchase_order_add_order_info_msg:
                    response = self.gupshup_template_purchase_order_without_lines_signature_with_order_details(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                               whatsapp_instance_id)
                elif not whatsapp_instance_id.purchase_order_add_signature and whatsapp_instance_id.purchase_order_add_order_product_details and not whatsapp_instance_id.purchase_order_add_order_info_msg:
                    response = self.gupshup_template_purchase_order_without_order_details_signature_with_lines(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                               whatsapp_instance_id)
                elif whatsapp_instance_id.purchase_order_add_signature and not whatsapp_instance_id.purchase_order_add_order_product_details and whatsapp_instance_id.purchase_order_add_order_info_msg:
                    response = self.gupshup_template_purchase_order_without_lines_with_signature_order_details(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                               whatsapp_instance_id)
                elif whatsapp_instance_id.purchase_order_add_signature and whatsapp_instance_id.purchase_order_add_order_product_details and not whatsapp_instance_id.purchase_order_add_order_info_msg:
                    response = self.gupshup_template_purchase_order_without_order_details_with_signature_lines(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                               whatsapp_instance_id)
                elif not whatsapp_instance_id.purchase_order_add_signature and whatsapp_instance_id.purchase_order_add_order_product_details and whatsapp_instance_id.purchase_order_add_order_info_msg:
                    response = self.gupshup_template_purchase_order_without_signature_with_order_details_lines(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                               whatsapp_instance_id)
                elif whatsapp_instance_id.purchase_order_add_signature and whatsapp_instance_id.purchase_order_add_order_product_details and whatsapp_instance_id.purchase_order_add_order_info_msg:
                    response = self.gupshup_template_purchase_order_with_signature_order_details_lines(url, headers, record, number_without_code, self.attachment_ids[0],
                                                                                                       whatsapp_instance_id)

            if response.status_code == 201 or response.status_code == 200 or response.status_code == 202:
                json_response = json.loads(response.text)
                self.env['whatsapp.msg.res.partner'].with_context({'partner_id': record.partner_id.id}).gupshup_create_whatsapp_message(
                    str(record.partner_id.country_id.phone_code) + number_without_code, self.message, json_response.get('messageId'), whatsapp_instance_id, 'sale.order',
                    record, self.attachment_ids[0])
                if whatsapp_instance_id.purchase_order_add_message_in_chatter:
                    self.add_message_in_chatter(record, active_model, self.attachment_ids[0])
        return True

    def gupshup_template_purchase_order_without_order_details_lines_signature(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'purchase_order_without_order_details_lines_signature_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps({"id": whatsapp_template_id.template_id, "params": [record.partner_id.name]}),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_purchase_order_without_order_details_lines_with_signature(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'purchase_order_without_order_details_lines_with_signature_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            instance_signature = ''
            if whatsapp_instance_id.signature:
                instance_signature = whatsapp_instance_id.signature
            else:
                instance_signature = self.env.user.company_id.name
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            instance_signature
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_purchase_order_without_lines_signature_with_order_details(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'purchase_order_without_lines_signature_with_order_details_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            record.name,
                            self.format_amount(record.amount_total, record.currency_id)
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_purchase_order_without_order_details_signature_with_lines(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'purchase_order_without_order_details_signature_with_lines_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            msg = ''
            line_count = 1
            for line_id in record.order_line:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.product_qty and line_id.product_uom:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.product_qty) + " " + str(line_id.product_uom.name)
                    if line_id.price_unit:
                        msg += "  *" + _("Unit Price") + ":* " + str(line_id.price_unit)
                    if line_id.price_subtotal:
                        msg += "  *" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                    line_count += 1
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            msg
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_purchase_order_without_lines_with_signature_order_details(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'purchase_order_without_lines_with_signature_order_details_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            instance_signature = ''
            if whatsapp_instance_id.signature:
                instance_signature = whatsapp_instance_id.signature
            else:
                instance_signature = self.env.user.company_id.name
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            record.name,
                            self.format_amount(record.amount_total, record.currency_id),
                            instance_signature
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_purchase_order_without_order_details_with_signature_lines(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'purchase_order_without_order_details_with_signature_lines_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            instance_signature = ''
            if whatsapp_instance_id.signature:
                instance_signature = whatsapp_instance_id.signature
            else:
                instance_signature = self.env.user.company_id.name
            msg = ''
            line_count = 1
            for line_id in record.order_line:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.product_qty and line_id.product_uom:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.product_uom_qty) + " " + str(line_id.product_uom.name)
                    if line_id.price_unit:
                        msg += "  *" + _("Unit Price") + ":* " + str(line_id.price_unit)
                    if line_id.price_subtotal:
                        msg += "  *" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                    line_count += 1

            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            msg,
                            instance_signature
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_purchase_order_without_signature_with_order_details_lines(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'purchase_order_without_signature_with_order_details_lines_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            msg = ''
            line_count = 1
            for line_id in record.order_line:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.product_qty and line_id.product_uom:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.product_qty) + " " + str(line_id.product_uom.name)
                    if line_id.price_unit:
                        msg += "  *" + _("Unit Price") + ":* " + str(line_id.price_unit)
                    if line_id.price_subtotal:
                        msg += "  *" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                    line_count += 1

            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            record.name,
                            self.format_amount(record.amount_total, record.currency_id),
                            msg,
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)

    def gupshup_template_purchase_order_with_signature_order_details_lines(self, url, headers, record, number_without_code, attachment_id, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'purchase_order_with_signature_order_details_lines_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            line_count = 1
            msg = ''
            for line_id in record.order_line:
                if line_id:
                    if line_id.product_id:
                        msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.display_name
                    if line_id.product_qty and line_id.product_uom:
                        msg += "  *" + _("Qty") + ":* " + str(line_id.product_qty) + " " + str(line_id.product_uom.name)
                    if line_id.price_unit:
                        msg += "  *" + _("Unit Price") + ":* " + str(line_id.price_unit)
                    if line_id.price_subtotal:
                        msg += "  *" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                    line_count += 1
            instance_signature = ''
            if whatsapp_instance_id.signature:
                instance_signature = whatsapp_instance_id.signature
            else:
                instance_signature = self.env.user.company_id.name
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            record.name,
                            self.format_amount(record.amount_total, record.currency_id),
                            msg,
                            instance_signature
                        ]
                    }
                ),
                "message": json.dumps({"type": "document", "document": {"link": attachment_id.public_url, "filename": attachment_id.name}})
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.template_errors(whatsapp_template_id)
