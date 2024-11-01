# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, _
import requests
import json
import datetime
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class accountInvoice(models.Model):
    _inherit = 'account.move'

    def _payment_remainder_send_message(self):
        whatsapp_instance_id = self.env['whatsapp.instance'].get_whatsapp_instance()
        if whatsapp_instance_id.provider == "whatsapp_chat_api":
            if whatsapp_instance_id.send_whatsapp_through_template:
                self._payment_remainder_send_template_message_chat_api(whatsapp_instance_id)
            else:
                self._payment_remainder_send_message_chat_api(whatsapp_instance_id)
        elif whatsapp_instance_id.provider == "gupshup":
            if whatsapp_instance_id.send_whatsapp_through_template:
                self.send_message_from_gupshup_through_template(whatsapp_instance_id)
            else:
                self.send_message_from_gupshup_without_template(whatsapp_instance_id)

    def _payment_remainder_send_template_message_chat_api(self, whatsapp_instance_id):
        url = whatsapp_instance_id.whatsapp_endpoint + '/sendTemplate?token=' + whatsapp_instance_id.whatsapp_token
        headers = {"Content-Type": "application/json"}
        account_invoice_ids = self.env['account.move'].search(
            [('state', '=', 'posted'), ('move_type', '=', 'out_invoice'), ('payment_state', '=', 'not_paid'), ('invoice_date_due', '<', datetime.datetime.now())])
        for account_invoice_id in account_invoice_ids:
            if account_invoice_id.partner_id.country_id.phone_code and account_invoice_id.partner_id.mobile:
                res_partner_id = account_invoice_id.partner_id
                whatsapp_msg_number = res_partner_id.mobile
                if whatsapp_msg_number:
                    whatsapp_msg_number_without_space = whatsapp_msg_number.replace(" ", "")
                    message = ''
                    message += 'Hello ' + account_invoice_id.partner_id.name + '\n'
                    message += "Your invoice " + account_invoice_id.name + ' is pending.' + '\n'
                    message += "Total Amount " + self.env['whatsapp.msg'].format_amount(account_invoice_id.amount_total, account_invoice_id.currency_id) + ' and Due Amount ' + str(
                        round(account_invoice_id.partner_id.credit, 2))

                    if '+' in whatsapp_msg_number_without_space:
                        number_without_code = whatsapp_msg_number_without_space.replace('+' + str(res_partner_id.country_id.phone_code), "")
                    else:
                        number_without_code = whatsapp_msg_number_without_space.replace(str(res_partner_id.country_id.phone_code), "")

                    response = self.chat_api_payment_remainder_send_template(url, headers, account_invoice_id, number_without_code, whatsapp_instance_id)
                    if response.status_code == 201 or response.status_code == 200:
                        json_response = json.loads(response.text)
                        if json_response.get('sent') and json_response.get('description') == 'Message has been sent to the provider':
                            _logger.info("\nSend Message successfully")
                            mobile_with_country = str(res_partner_id.country_id.phone_code) + number_without_code
                            self.env['whatsapp.msg'].create_whatsapp_message(mobile_with_country, message, json_response.get('id'), json_response.get('message'), "text",
                                                                             whatsapp_instance_id,
                                                                             'crm.lead', self)
                        elif not json_response.get('sent') and json_response.get('error').get('message') == 'Recipient is not a valid WhatsApp user':
                            raise UserError(_('Please add valid whatsapp number for %s customer') % res_partner_id.name)
                        elif not json_response.get('sent') and json_response.get('message'):
                            raise UserError(_('%s') % json_response.get('message'))

    def chat_api_payment_remainder_send_template(self, url, headers, record, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'account_invoice_payment_remainder_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)],
            limit=1)
        if whatsapp_template_id.approval_state == 'approved':
            payload = {
                "template": whatsapp_template_id.name,
                "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                "namespace": whatsapp_template_id.namespace,
                "params": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": record.partner_id.name},
                            {"type": "text", "text": record.name},
                            {"type": "text", "text": self.env['whatsapp.msg'].format_amount(record.amount_total, record.currency_id)},
                            {"type": "text", "text": str(round(record.partner_id.credit, 2))},
                        ]
                    }
                ],
                "phone": str(record.partner_id.country_id.phone_code) + "" + number_without_code
            }
            return requests.post(url, data=json.dumps(payload), headers=headers)

    def _payment_remainder_send_message_chat_api(self, whatsapp_instance_id):
        account_invoice_ids = self.env['account.move'].search(
            [('state', '=', 'posted'), ('move_type', '=', 'out_invoice'), ('payment_state', '=', 'not_paid'), ('invoice_date_due', '<', datetime.datetime.now())])
        for account_invoice_id in account_invoice_ids:
            if account_invoice_id.partner_id.country_id.phone_code and account_invoice_id.partner_id.mobile:
                msg = _("Hello") + " " + account_invoice_id.partner_id.name + "\n" + _("Your invoice")
                if account_invoice_id.state == 'draft':
                    msg += " *" + _("draft") + "* "
                else:
                    msg += " *" + account_invoice_id.name + "* "
                msg += _("is pending")
                msg += "\n" + _("Total Amount") + ": " + self.env['whatsapp.msg'].format_amount(account_invoice_id.amount_total, account_invoice_id.currency_id) + " & " + _(
                    "Due Amount") + ": " + str(
                    round(account_invoice_id.partner_id.credit, 2)) + "."
                whatsapp_msg_number = account_invoice_id.partner_id.mobile
                whatsapp_msg_number_without_space = whatsapp_msg_number.replace(" ", "")
                if '+' in whatsapp_msg_number_without_space:
                    whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace('+' + str(account_invoice_id.partner_id.country_id.phone_code), "")
                else:
                    whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace(str(account_invoice_id.partner_id.country_id.phone_code), "")

                try:
                    url = whatsapp_instance_id.whatsapp_endpoint + '/sendMessage?token=' + whatsapp_instance_id.whatsapp_token
                    headers = {"Content-Type": "application/json"}
                    phone = str(account_invoice_id.partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code
                    tmp_dict = {"phone": phone, "body": msg}
                    response = requests.post(url, json.dumps(tmp_dict), headers=headers)
                    if response.status_code == 201 or response.status_code == 200:
                        json_send_message_response = json.loads(response.text)
                        if json_send_message_response.get('sent'):
                            _logger.info("\nSend Message successfully")
                            mail_message_obj = self.env['mail.message']
                            mail_message_id = mail_message_obj.sudo().create({
                                'res_id': account_invoice_id.id,
                                'model': 'account.move',
                                'body': msg,
                            })
                except Exception as e_log:
                    _logger.exception("Exception in payment remainder %s:\n", str(e_log))

    def send_message_from_gupshup_without_template(self, whatsapp_instance_id):
        account_invoice_ids = self.env['account.move'].search(
            [('state', '=', 'posted'), ('move_type', '=', 'out_invoice'), ('payment_state', '=', 'not_paid'), ('invoice_date_due', '<', datetime.datetime.now())])
        for account_invoice_id in account_invoice_ids:
            if account_invoice_id.partner_id.country_id.phone_code and account_invoice_id.partner_id.mobile:
                msg = _("Hello") + " " + account_invoice_id.partner_id.name + "\n" + _("Your invoice")
                if account_invoice_id.state == 'draft':
                    msg += " *" + _("draft") + "* "
                else:
                    msg += " *" + account_invoice_id.name + "* "
                msg += _("is pending")
                msg += "\n" + _("Total Amount") + ": " + self.env['whatsapp.msg'].format_amount(account_invoice_id.amount_total, account_invoice_id.currency_id) + " & " + _(
                    "Due Amount") + ": " + str(
                    round(account_invoice_id.partner_id.credit, 2)) + "."
                whatsapp_msg_number = account_invoice_id.partner_id.mobile
                whatsapp_msg_number_without_space = whatsapp_msg_number.replace(" ", "")
                whatsapp_msg_number_without_plus = whatsapp_msg_number_without_space.replace('+', '')
                whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace('+' + str(account_invoice_id.partner_id.country_id.phone_code), "")
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
                try:
                    url = 'https://api.gupshup.io/sm/api/v1/msg'
                    temp_data = {
                        'channel': 'whatsapp',
                        'source': whatsapp_msg_source_number,
                        'destination': whatsapp_msg_number_without_plus,
                        'message': json.dumps({
                            'type': 'text',
                            'text': msg
                        })
                    }
                    response = requests.post(url, headers=headers, data=temp_data)
                    if response.status_code == 201 or response.status_code == 200:
                        _logger.info("\nSend Message successfully")
                        whatsapp_msg = self.env['whatsapp.messages']
                        vals = {
                            'message_body': msg,
                            'senderName': whatsapp_instance_id.whatsapp_gupshup_app_name,
                            'state': 'sent',
                            'to': whatsapp_msg_source_number,
                            'partner_id': account_invoice_id.partner_id.id,
                            'time': fields.Datetime.now()
                        }
                        whatsapp_msg_id = whatsapp_msg.sudo().create(vals)
                        if whatsapp_msg_id:
                            _logger.info("\nWhatsApp message Created")
                        mail_message_obj = self.env['mail.message']
                        mail_message_id = mail_message_obj.sudo().create({
                            'res_id': account_invoice_id.id,
                            'model': 'account.move',
                            'body': msg,
                        })
                except Exception as e_log:
                    _logger.exception("Exception in payment remainder %s:\n", str(e_log))

    def send_message_from_gupshup_through_template(self, whatsapp_instance_id):
        url = 'https://api.gupshup.io/sm/api/v1/template/msg'
        headers = {"Content-Type": "application/x-www-form-urlencoded", "apikey": whatsapp_instance_id.whatsapp_gupshup_api_key}
        account_invoice_ids = self.env['account.move'].search(
            [('state', '=', 'posted'), ('move_type', '=', 'out_invoice'), ('payment_state', '=', 'not_paid'), ('invoice_date_due', '<', datetime.datetime.now())])
        for account_invoice_id in account_invoice_ids:
            if account_invoice_id.partner_id.country_id.phone_code and account_invoice_id.partner_id.mobile:
                res_partner_id = account_invoice_id.partner_id
                whatsapp_msg_number = res_partner_id.mobile
                if whatsapp_msg_number:
                    whatsapp_msg_number_without_space = whatsapp_msg_number.replace(" ", "")
                    message = ''
                    message = ''
                    message += 'Hello ' + account_invoice_id.partner_id.name + '\n'
                    message += "Your invoice " + account_invoice_id.name + ' is pending.' + '\n'
                    message += "Total Amount " + self.env['whatsapp.msg'].format_amount(account_invoice_id.amount_total, account_invoice_id.currency_id) + ' and Due Amount ' + str(
                        round(account_invoice_id.partner_id.credit, 2))

                    if '+' in whatsapp_msg_number_without_space:
                        number_without_code = whatsapp_msg_number_without_space.replace('+' + str(res_partner_id.country_id.phone_code), "")
                    else:
                        number_without_code = whatsapp_msg_number_without_space.replace(str(res_partner_id.country_id.phone_code), "")

                    response = self.gupshup_payment_remainder_send_template(url, headers, account_invoice_id, number_without_code, whatsapp_instance_id)
                    if response.status_code == 201 or response.status_code == 200 or response.status_code == 202:
                        json_response = json.loads(response.text)
                        _logger.info("\nSend Message successfully")
                        self.env['whatsapp.msg.res.partner'].with_context({'partner_id': account_invoice_id.partner_id.id}).gupshup_create_whatsapp_message(
                            str(account_invoice_id.partner_id.country_id.phone_code) + number_without_code, message, json_response.get('messageId'), whatsapp_instance_id,
                            'account.move',
                            account_invoice_id)

    def gupshup_payment_remainder_send_template(self, url, headers, record, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'account_invoice_payment_remainder_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)],
            limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(record.partner_id.country_id.phone_code) + "" + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            record.partner_id.name,
                            record.name,
                            self.env['whatsapp.msg'].format_amount(record.amount_total, record.currency_id),
                            str(round(record.partner_id.credit, 2)),
                        ]
                    }
                ),
            }
            return requests.post(url, data=payload, headers=headers)
