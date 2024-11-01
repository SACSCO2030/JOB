import json
import requests
import logging
import base64
from odoo.http import request, Response

from odoo import fields, models, _, api
from odoo.exceptions import ValidationError
from requests.structures import CaseInsensitiveDict

_logger = logging.getLogger(__name__)


class PosConfig(models.Model):
    _inherit = 'pos.config'

    iface_whatsapp_receipt = fields.Boolean(
        string="Whatsapp Receipt", help="Allow to send POS Receipt to customer's Whatsapp")
    iface_whatsapp_receipt_auto = fields.Boolean(
        string="Whatsapp Receipt Automatically", help="Allow to send POS Receipt to customer's Whatsapp automatically")
    iface_whatsapp_msg = fields.Boolean(
        string="Whatsapp message", help="Allow to send Whatsapp message to specific customer")
    iface_whatsapp_grp_msg = fields.Boolean(
        string="Send message", help="Allow to send messages")
    iface_whatsapp_msg_template = fields.Boolean(
        string="Whatsapp message template", help="Allow to set Whatsapp default message template")
    whatsapp_msg_template_id = fields.Many2one(
        "whatsapp.message.template", string="Message Template", help="Set default whatsapp message template")

    # def get_instance_provider(self):
    #     whatsapp_instance_id = self.env['whatsapp.instance'].sudo().search([('status', '!=', 'disable')], limit=1)
    #     provider = whatsapp_instance_id.provider
    #     print('---provider---', provider)
    #     return {'provider': provider}

    @api.model
    def parse_mobile_no(self, mobile_no):
        """
        Convert mobile no. to 1msg phone no format.
        :param mobile_no: customer mobile no.
        :return:
        """
        return mobile_no.replace(" ", "").replace("+", "")

    @api.model
    def _get_chat_api_whatsapp_endpoint(self, method, whatsapp_instance_id):
        endpoint = whatsapp_instance_id.whatsapp_endpoint
        token = whatsapp_instance_id.whatsapp_token
        url = ''
        if all([endpoint, token]):
            url = f"{endpoint}/{method}?token={token}"
        else:
            ValidationError(_(f'Missing Whatsapp credentials, \ncontact to your Administrator.'))
        return url

    @api.model
    def _get_gupshup_whatsapp_endpoint(self, method):
        url = f"{'https://api.gupshup.io/sm/api/v1'}/{method}"
        return url

    @api.model
    def _get_meta_whatsapp_endpoint(self, phone_id):
        url = "https://graph.facebook.com/v16.0/{}/messages".format(phone_id)
        return url

    @api.model
    def get_whatsapp_chatlist(self, *args, **kwargs):
        whatsapp_instance_id = self.env['whatsapp.instance'].sudo().search([('status','!=','disable')], limit=1)
        if whatsapp_instance_id.provider == 'whatsapp_chat_api':
            response = self.chat_api_get_whatsapp_chatlist(
                whatsapp_instance_id)
            return response
        elif whatsapp_instance_id.provider == 'gupshup':
            response = self.gupshup_get_whatsapp_chatlist(whatsapp_instance_id)
        # elif whatsapp_instance_id.provider == 'meta':
        #     response = self.meta_get_whatsapp_chatlist(whatsapp_instance_id)
            return response

    # def meta_get_whatsapp_chatlist(self, whatsapp_instance_id):
        # token = whatsapp_instance_id.whatsapp_meta_api_token
        # business_account_id = whatsapp_instance_id.meta_whatsapp_business_account_id
        # url = "https://graph.facebook.com/v17.0/{}/phone_numbers?access_token={}".format(business_account_id, token)
        # response = requests.get(url)
        # if response.status_code in [202, 201, 200]:
        #     contact_json_response = json.loads(response.text)
        #     contacts = []
        #
        #     for item in contact_json_response['data']:
        #         contact_name = item["verified_name"]
        #         contact_number = item["display_phone_number"]
        #         contact_id = item["id"]
        #
        #         vals = {
        #             'name': contact_name,
        #             'mobile': contact_number,
        #             'whatsapp_id': contact_id
        #         }
        #
        #         contacts.append(vals)
        #
        #     print(contacts)

            # for contact in contacts:
        # token = whatsapp_instance_id.whatsapp_meta_api_token
        # number_id = whatsapp_instance_id.whatsapp_meta_phone_number_id
        # url = "https://graph.facebook.com/v16.0/{}/messages".format(number_id)
        # req_headers = CaseInsensitiveDict()
        # req_headers["Authorization"] = "Bearer " + token
        # req_headers["Content-Type"] = "application/json"
        # data_json = {
        #     "messaging_product": "whatsapp",
        #     "recipient_type": "individual",
        #     "to": '916383922849',
        #     "type": "text",
        #     "text": {
        #         "body": 'hello2',
        #     }
        # }
        # response = requests.post(url, headers=req_headers, json=data_json)
        # print("respo", response.json())
        # if response.status_code in [202, 201, 200]:
        #     _logger.info("\nSend Message successfully")
        # return response
    def chat_api_get_whatsapp_chatlist(self, whatsapp_instance_id):
        url = self._get_chat_api_whatsapp_endpoint(
            "dialogs", whatsapp_instance_id)
        response = {}
        if not url:
            response["error"] = {
                "code": 400,
                "message": "Missing Whatsapp configuration, contact to your Administrator"
            }
            return json.dumps(response)
        headers = {
            "Content-Type": "application/json",
        }
        try:
            req = requests.get(url, headers=headers)
            result = req.json()
            if req.status_code == 201 or req.status_code == 200:
                response["code"] = req.status_code
                chat_list = list(map(lambda dialog: {"id": dialog["chatId"].split(
                    '@')[0], "name": dialog["name"]}, result["dialogs"]))
                res = self.remove_duplicate_records(chat_list)
                response["chatList"] = res

            else:
                if 'error' in result:
                    message = response['error']
                    _logger.error(f"Failed Whatsapp API call => Reason: {req.reason}, Message:{message}")
                    response["error"] = {
                        "code": req.status_code,
                        "message": message
                    }
        except Exception as e:
            _logger.error(e)
            response["error"] = {
                "code": 500,
                "message": e
            }
        return response

    def remove_duplicate_records(self, test_list):
        K = "id"

        memo = set()
        res = []
        for sub in test_list:

            # testing for already present value
            if sub[K] not in memo:
                res.append(sub)

                # adding in memo if new value
                memo.add(sub[K])
        return res

    def gupshup_get_whatsapp_chatlist(self, whatsapp_instance_id):
        url = self._get_gupshup_whatsapp_endpoint("users")
        url += '/' + whatsapp_instance_id.whatsapp_gupshup_app_name
        response = {}
        headers = {"appname": whatsapp_instance_id.whatsapp_gupshup_app_name,
                   "apikey": whatsapp_instance_id.whatsapp_gupshup_api_key}
        try:
            req = requests.get(url, headers=headers)
            if req.status_code == 201 or req.status_code == 200:
                result = req.json()
                chat_list = self.get_partner_from_user(result)
                response["code"] = req.status_code
                response["chatList"] = chat_list
            else:
                message = response['error']
                _logger.error(f"Failed Whatsapp API call => Reason: {req.text}")

        except Exception as e:
            _logger.error(e)
            response["error"] = {
                "code": 500,
                "message": e
            }
        return response

    def get_partner_from_user(self, result):
        list_chat_list = []
        for users in result.get('users'):
            dict_chat_list = {}
            dict_chat_list['id'] = users.get(
                'countryCode') + users.get('phoneCode')

            gupshup_country_code = users.get('countryCode')
            gupshup_mobile = users.get('phoneCode')
            res_partner_id = self.env['res.partner'].sudo().search(
                [('mobile', '=', gupshup_country_code + gupshup_mobile)], limit=1)
            if res_partner_id:
                dict_chat_list['name'] = res_partner_id.name
            else:
                dict_chat_list['name'] = ''
            list_chat_list.append(dict_chat_list)
        return list_chat_list

    @api.model
    def action_send_whatsapp_group_msg(self, template_id, message, chat_ids, *args, **kwargs):
        for chat_id in chat_ids:
            self.action_send_whatsapp_msg(
                template_id, message, chat_id, is_bulk=True)

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
                whatsapp_messages_dict['partner_id'] = self._context.get(
                    'partner_id')
            elif not model == 'mail.channel' and not model == 'odoo.group' and not model == 'whatsapp.marketing' and not self.env.context.get(
                    'skip_partner') and not model == 'pos.order':
                if record.partner_id:
                    whatsapp_messages_dict['partner_id'] = record.partner_id.id
        whatsapp_messages_id = self.env['whatsapp.messages'].sudo().create(
            whatsapp_messages_dict)
        _logger.info("Whatsapp message created in odoo from meta %s: ", str(
            whatsapp_messages_id.id))

    @api.model
    def action_send_whatsapp_msg(self, template_id, message, mobile_no, is_bulk=False, *args, **kwargs):
        whatsapp_instance_id = self.env['whatsapp.instance'].get_whatsapp_instance(
        )
        url = ''
        if whatsapp_instance_id.provider == 'whatsapp_chat_api':
            self.chat_api_send_whatsapp_message(
                whatsapp_instance_id, template_id, message, mobile_no, is_bulk)
        elif whatsapp_instance_id.provider == 'gupshup':
            self.gupshup_send_whatsapp_message(
                whatsapp_instance_id, template_id, message, mobile_no, is_bulk)
        elif whatsapp_instance_id.provider == 'meta':
            self.meta_send_whatsapp_message(
                whatsapp_instance_id, template_id, message, mobile_no, is_bulk)

    def meta_send_whatsapp_message(self, whatsapp_instance_id, template_id, message, mobile_no, is_bulk):
        whatsapp_instance_id = self.env['whatsapp.instance'].get_whatsapp_instance(
        )
        phone_id = whatsapp_instance_id.whatsapp_meta_phone_number_id
        url = "https://graph.facebook.com/v16.0/{}/messages".format(phone_id)
        access_token = whatsapp_instance_id.whatsapp_meta_api_token
        req_headers = CaseInsensitiveDict()
        req_headers["Authorization"] = "Bearer " + access_token
        req_headers["Content-Type"] = "application/json"
        data_json = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": mobile_no,
            "type": "text",
            "text": {
                "body": message,
            }
        }
        try:
            response = requests.post(url, headers=req_headers, json=data_json)
            if response.status_code in [202, 201, 200]:
                response_dict = response.json()
                self.meta_create_whatsapp_message(data_json.get('to'), data_json.get('text').get(
                    'body'), response_dict.get('messages')[0].get('id'), whatsapp_instance_id, 'pos.order', self)
                _logger.info("\nSend Message successfully")
            else:
                if 'error' in response:
                    message = response['error']
                    _logger.error(f"Reason: {req.reason}, Message:{message}")
        except Exception as e:
            _logger.error(e)

    def chat_api_send_whatsapp_message(self, whatsapp_instance_id, template_id, message, mobile_no, is_bulk):
        whatsapp_instance_id = self.env['whatsapp.instance'].get_whatsapp_instance(
        )
        url = self._get_chat_api_whatsapp_endpoint(
            'sendMessage', whatsapp_instance_id)
        if not url:
            return json.dumps("Missing Whatsapp configuration, contact to your Administrator")
        headers = {
            "Content-Type": "application/json",
        }
        payload = {
            "phone": self.parse_mobile_no(mobile_no),
            "body": message
        }
        if is_bulk:
            if payload.get('chatId'):
                del payload['chatId']
        else:
            payload["phone"] = self.parse_mobile_no(mobile_no)
        try:
            req = requests.post(url, data=json.dumps(payload), headers=headers)
            response = req.json()
            if req.status_code == 201 or req.status_code == 200:
                self._create_whatsapp_message_from_pos(payload.get('phone'), payload.get('body'), response.get('id'),
                                                       response.get('message'), "text", whatsapp_instance_id, 'pos.order', self)
                _logger.info(f"\n11Whatsapp Message successfully send to {mobile_no}")
            else:
                if 'error' in response:
                    message = response['error']
                    _logger.error(f"Reason: {req.reason}, Message:{message}")
        except Exception as e:
            _logger.error(e)

    def gupshup_send_whatsapp_message(self, whatsapp_instance_id, template_id, message, mobile_no, is_bulk):
        url = self._get_gupshup_whatsapp_endpoint('msg')
        if not url:
            return json.dumps("Missing Whatsapp configuration, contact to your Administrator")
        headers = {"Content-Type": "application/x-www-form-urlencoded",
                   "apikey": whatsapp_instance_id.whatsapp_gupshup_api_key}
        payload = {
            'channel': 'whatsapp',
            'source': whatsapp_instance_id.gupshup_source_number,
            'destination': self.parse_mobile_no(mobile_no),
            'message': json.dumps({'type': 'text', 'text': message})
        }
        try:
            req = requests.post(url, payload, headers=headers)
            response = req.json()
            if req.status_code in [202, 201, 200]:
                _logger.info(f"\n11Whatsapp Message successfully send to {mobile_no}")
                res_partner_id = self.env['res.partner'].sudo().search(
                    [('mobile', '=', self.parse_mobile_no(mobile_no))])
                if res_partner_id:
                    self.env['whatsapp.msg.res.partner'].with_context({'partner_id': res_partner_id.id}).gupshup_create_whatsapp_message(payload.get('destination'), message, response.get('messageId'), whatsapp_instance_id,
                                                                                                                                         'pos.order', self)
                else:
                    self.env['whatsapp.msg.res.partner'].gupshup_create_whatsapp_message(payload.get('destination'), message, response.get('messageId'), whatsapp_instance_id,
                                                                                         'pos.order', self)
            else:
                if 'error' in response:
                    message = response['error']
                    _logger.error(f"Reason: {req.reason}, Message:{message}")
        except Exception as e:
            _logger.error(e)

    @api.model
    def action_send_whatsapp_receipt(self, order_id, ticket_img, mobile_no, country_id, partner_id, *args, **kwargs):
        whatsapp_instance_id = self.env['whatsapp.instance'].get_whatsapp_instance(
        )
        if whatsapp_instance_id.provider == 'whatsapp_chat_api':
            self.chat_api_send_whatsapp_receipt(
                whatsapp_instance_id, order_id, ticket_img, mobile_no, country_id, partner_id)
        elif whatsapp_instance_id.provider == 'gupshup':
            self.gupshup_send_whatsapp_receipt(
                whatsapp_instance_id, order_id, ticket_img, mobile_no, country_id, partner_id)
        elif whatsapp_instance_id.provider == 'meta':
            self.meta_send_whatsapp_receipt(
                whatsapp_instance_id, order_id, ticket_img, mobile_no, country_id, partner_id)

    def chat_api_send_whatsapp_receipt(self, whatsapp_instance_id, order_id, ticket_img, mobile_no, country_id, partner_id):
        if whatsapp_instance_id.send_whatsapp_through_template:
            whatsapp_instance_id = self.env['whatsapp.instance'].get_whatsapp_instance(
            )
            url = self._get_chat_api_whatsapp_endpoint(
                'sendTemplate', whatsapp_instance_id)
            if not url:
                return json.dumps("Missing Whatsapp configuration, contact to your Administrator")
            try:
                whatsapp_template_id = self.env['whatsapp.templates'].search(
                    [('name', 'ilike', 'send_pos_receipt_'), ('default_template', '=', True), ('whatsapp_instance_id', '=', whatsapp_instance_id.id)], limit=1)
                headers = {"Content-Type": "application/json"}
                country_id = self.env['res.country'].search(
                    [('id', '=', country_id)])
                if whatsapp_template_id.approval_state == 'approved':
                    url_upload_media = self._get_chat_api_whatsapp_endpoint(
                        'uploadMedia', whatsapp_instance_id)
                    media_payload = {"body": f"data:image/jpeg;base64,{ticket_img}"}
                    response_media = requests.post(
                        url_upload_media, data=json.dumps(media_payload), headers=headers)
                    res_partner_id = self.env['res.partner'].sudo().search(
                        [('id', '=', partner_id)])
                    if response_media.status_code == 201 or response_media.status_code == 200 and res_partner_id:
                        json_response_media_response = json.loads(
                            response_media.text)
                        payload = {
                            "template": whatsapp_template_id.name,
                            "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                            "namespace": whatsapp_template_id.namespace,
                            "params": [
                                {
                                    "type": "header",
                                    "parameters": [{"type": "image", "image": {"id": json_response_media_response.get('mediaId'), "filename": "receipt.jpeg"}}]
                                },
                                {
                                    "type": "body",
                                    "parameters": [{"type": "text", "text": res_partner_id.name}]
                                }
                            ],
                            "phone": self.parse_mobile_no(mobile_no)
                        }

                        try:
                            req = requests.post(
                                url, data=json.dumps(payload), headers=headers)
                            response = req.json()
                            if req.status_code == 201 or req.status_code == 200:
                                if response.get('sent') and response.get('description') == 'Message has been sent to the provider':
                                    _logger.info(f"\n22Whatsapp Message successfully send to {mobile_no}")
                                    return 'Whatsapp Message send successfully'
                                elif not response.get('sent') and response.get('error').get('message') == 'Recipient is not a valid WhatsApp user':
                                    return 'Phone not exists on whatsapp'
                                elif not response.get('sent') and response.get('message'):
                                    return response.get('message')
                            else:
                                if 'error' in response:
                                    message = response['error']
                                    _logger.error(f"Reason: {req.reason}, Message:{message}")
                                    return message
                                return False
                        except Exception as e:
                            _logger.error(e)
            except Exception as e:
                _logger.error(e)

        else:
            url = self._get_chat_api_whatsapp_endpoint(
                'sendFile', whatsapp_instance_id)

            if not url:
                return json.dumps("Missing Whatsapp configuration, contact to your Administrator")
            try:
                headers = {"Content-Type": "application/json"}
                country_id = self.env['res.country'].search(
                    [('id', '=', country_id)])
                image_data = f"data:image/jpeg;base64,{ticket_img}"
                payload = {
                    "phone": self.parse_mobile_no(mobile_no),
                    "body": image_data,
                    "filename": "receipt.jpeg"
                }
                try:
                    req = requests.post(
                        url, data=json.dumps(payload), headers=headers)
                    response = req.json()
                    if response.get('sent') and response.get('description') == 'Message has been sent to the provider':
                        self._create_whatsapp_message_from_pos(payload.get('phone'), payload.get('body'), response.get('id'),
                                                               response.get(
                                                                   'message'), "receipt/image", whatsapp_instance_id, 'pos.config', self, payload.get('body'),
                                                               payload.get('filename'))
                        _logger.info(f"\n22Whatsapp Message successfully send to {mobile_no}")
                        return 'Whatsapp Message send successfully'
                    elif not response.get('sent') and response.get('error'):
                        if response.get('error').get('message') == 'Recipient is not a valid WhatsApp user':
                            return 'Phone not exists on whatsapp'
                    elif not response.get('sent') and response.get('message'):
                        return response.get('message')
                except Exception as e:
                    _logger.error(e)
            except Exception as e:
                _logger.error(e)

    def gupshup_send_whatsapp_receipt(self, whatsapp_instance_id, order_id, ticket_img, mobile_no, country_id, partner_id):
        pos_order_id = request.env['pos.order'].sudo().search(
            [('id', '=', order_id)])

        if whatsapp_instance_id.send_whatsapp_through_template:
            return True
        else:
            url = self._get_gupshup_whatsapp_endpoint('msg')
        try:
            headers = {"Content-Type": "application/x-www-form-urlencoded",
                       "apikey": whatsapp_instance_id.whatsapp_gupshup_api_key}
            ir_attachment_id = self.env['ir.attachment'].create({
                'name': 'receipt.jpeg',
                'type': 'binary',
                'datas': ticket_img,
                'res_model': 'pos.order',
                'res_id': pos_order_id.id,
                'mimetype': 'image/jpeg',
            })
            payload = {
                'channel': 'whatsapp',
                'source': whatsapp_instance_id.gupshup_source_number,
                'destination': self.parse_mobile_no(mobile_no),
                'message': json.dumps({
                    'type': 'image',
                    'originalUrl': ir_attachment_id.public_url,
                    'caption': ir_attachment_id.name
                })
            }
            try:
                req = requests.post(url, data=payload, headers=headers)
                response = req.json()
                if req.status_code in [202, 201, 200]:
                    self.env['whatsapp.msg.res.partner'].gupshup_create_whatsapp_message_for_attachment(self.parse_mobile_no(mobile_no), ir_attachment_id,
                                                                                                        response.get(
                                                                                                            'messageId'), ir_attachment_id.mimetype,
                                                                                                        whatsapp_instance_id, 'pos.order', pos_order_id)
                    _logger.info(f"\n22Whatsapp Message successfully send to {mobile_no}")
                    return 'Whatsapp Message send successfully'
                else:
                    return req.text
            except Exception as e:
                _logger.error(e)
        except Exception as e:
            _logger.error(e)

    def meta_send_whatsapp_receipt(self, whatsapp_instance_id, order_id, ticket_img, mobile_no, country_id, partner_id):
        pos_order_id = request.env['pos.order'].sudo().search(
            [('id', '=', order_id)])
        # if whatsapp_instance_id.send_whatsapp_through_template:
        #     return True
        # else:
        phone_id = whatsapp_instance_id.whatsapp_meta_phone_number_id
        url = "https://graph.facebook.com/v16.0/{}/messages".format(
            phone_id)
        try:
            access_token = whatsapp_instance_id.whatsapp_meta_api_token
            req_headers = CaseInsensitiveDict()
            req_headers["Authorization"] = "Bearer " + access_token
            req_headers["Content-Type"] = "application/json"
            ir_attachment_id = self.env['ir.attachment'].create({
                'name': 'receipt.jpeg',
                'type': 'binary',
                'datas': ticket_img,
                'res_model': 'pos.order',
                'res_id': pos_order_id.id,
                'mimetype': 'image/jpeg',
            })
            data_json = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": mobile_no,
                "type": "image",
                "image": {
                        "link": ir_attachment_id.public_url,
                        "caption": ir_attachment_id.name
                },
            }
            try:
                response = requests.post(
                    url, headers=req_headers, json=data_json)
                if response.status_code in [202, 201, 200]:
                    response_dict = response.json()
                    self.meta_create_whatsapp_message(data_json.get('to'), data_json.get('text').get('body'), response_dict.get(
                        'messages')[0].get('id'), whatsapp_instance_id, 'pos.order', self, attachment_id=ir_attachment_id.id)
                    _logger.info("\nSend Message successfully")
                else:
                    if 'error' in response:
                        message = response['error']
                        _logger.error(f"Reason: {req.reason}, Message:{message}")
            except Exception as e:
                _logger.error(e)
        except Exception as e:
            _logger.error(e)

    def _create_whatsapp_message_from_pos(self, mobile_with_country, message, message_id, chatId_message, type, whatsapp_instance_id, model, record, image=False, image_name=False):
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
        }
        if image:
            whatsapp_messages_dict['msg_image'] = image
        if image_name:
            whatsapp_messages_dict['message_body'] = image_name

        whatsapp_messages_id = self.env['whatsapp.messages'].sudo().create(
            whatsapp_messages_dict)
        _logger.info("Whatsapp message created in odoo from POS %s: ",
                     str(whatsapp_messages_id.id))
