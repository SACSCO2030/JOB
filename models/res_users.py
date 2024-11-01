import logging
from odoo import api, fields, models, _
import requests
import json

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    mobile = fields.Char()
    country_id = fields.Many2one('res.country', 'Country')

    @api.model
    def signup(self, values, token=None):
        values.update({'email': values.get('email') or values.get('login')})
        if token:
            # signup with a token: find the corresponding partner id
            partner = self.env['res.partner']._signup_retrieve_partner(token, check_validity=True, raise_exception=True)
            # invalidate signup token
            partner.write({'signup_token': False, 'signup_type': False, 'signup_expiration': False})
            partner_user = partner.user_ids and partner.user_ids[0] or False
            # avoid overwriting existing (presumably correct) values with geolocation data
            if partner.country_id or partner.zip or partner.city:
                values.pop('city', None)
                values.pop('country_id', None)
            if partner.lang:
                values.pop('lang', None)
            if partner_user:
                # user exists, modify it according to values
                values.pop('login', None)
                values.pop('name', None)
                partner_user.write(values)
                if not partner_user.login_date:
                    partner_user._notify_inviter()
                return (self.env.cr.dbname, partner_user.login, values.get('password'))
            else:
                # user does not exist: sign up invited user
                values.update({
                    'name': partner.name,
                    'partner_id': partner.id,
                    'email': values.get('email') or values.get('login'),
                })
                if partner.company_id:
                    values['company_id'] = partner.company_id.id
                    values['company_ids'] = [(6, 0, [partner.company_id.id])]
                partner_user = self._signup_create_user(values)
                partner_user._notify_inviter()

        else:
            values['mobile'] = values.get('mobile')
            values['country_id'] = values.get('country_id')
            user_id = self._signup_create_user(values)
            if values['mobile']:
                user_id.partner_id.mobile = values['mobile']
            if values['country_id']:
                user_id.partner_id.country_id = int(values['country_id'])
            whatsapp_instance_id = self.env['whatsapp.instance'].get_whatsapp_instance()
            if values.get('country_id'):
                country_id = self.env['res.country'].sudo().search([('id', '=', values.get('country_id'))])
                msg = ''
                try:
                    if values.get('mobile') and country_id:
                        whatsapp_number = str(country_id.phone_code) + "" + values.get('mobile')
                        if whatsapp_instance_id.provider == "whatsapp_chat_api":
                            if whatsapp_instance_id.send_whatsapp_through_template:
                                self.send_whatsapp_message_from_chatapi_through_template(values, whatsapp_number, whatsapp_instance_id)
                            else:
                                self.send_whatsapp_message_from_chatapi(values, whatsapp_number, whatsapp_instance_id)

                        elif whatsapp_instance_id.provider == "gupshup":
                            if whatsapp_instance_id.send_whatsapp_through_template:
                                self.send_whatsapp_message_from_gupshup_through_template(values, whatsapp_number, whatsapp_instance_id)
                            else:
                                self.send_whatsapp_message_from_gupshup(values, whatsapp_number, whatsapp_instance_id)

                except Exception as e_log:
                    _logger.exception("Exception in send message to user %s:\n", str(e_log))
        return (values.get('login'), values.get('password'))

    def send_whatsapp_message_from_chatapi_through_template(self, values, whatsapp_number, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'website_signup_page_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id), ('default_template', '=', True)])
        param = self.env['res.config.settings'].sudo().get_values()
        url = whatsapp_instance_id.whatsapp_endpoint + '/sendTemplate?token=' + whatsapp_instance_id.whatsapp_token
        headers = {"Content-Type": "application/json"}
        if whatsapp_template_id.approval_state == 'approved':
            payload = {
                "template": whatsapp_template_id.name,
                "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                "namespace": whatsapp_template_id.namespace,
                "params": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": values.get('name')},
                            {"type": "text", "text": values.get('login')}

                        ]
                    }
                ],
                "phone": whatsapp_number
            }
            response = requests.post(url, data=json.dumps(payload), headers=headers)
            if response and response.status_code == 201 or response.status_code == 200:
                json_send_message_response = json.loads(response.text)
                if json_send_message_response.get('sent'):
                    _logger.info("\nSend Message successfully")
                    message = _("Hello ") + values.get('name') + ',' + "\n" + _(
                        "You have successfully registered on our portal.") + "\n" + _("The connected email id is ") + " " + values.get('login')
                    user_id = self.env['res.users'].sudo().search([('login', '=', values.get('login'))])
                    self.env['whatsapp.msg'].create_whatsapp_message(whatsapp_number, message, json_send_message_response.get('id'),
                                                                     json_send_message_response.get('message'),
                                                                     "text", whatsapp_instance_id, 'res.users', user_id)
            return True
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted':
            self.env['whatsapp.msg'].template_errors(whatsapp_template_id)

    def send_whatsapp_message_from_chatapi(self, values, whatsapp_number, whatsapp_instance_id):
        user_id = self.env['res.users'].sudo().search([('login', '=', values.get('login'))])
        url = whatsapp_instance_id.whatsapp_endpoint + '/sendMessage?token=' + whatsapp_instance_id.whatsapp_token
        headers = {"Content-Type": "application/json"}
        message = _("Hello ") + values.get('name') + ',' + "\n" + _(
            "You have successfully registered on our portal.") + "\n" + _("The connected email id is ") + " " + values.get('login')
        tmp_dict = {
            "phone": whatsapp_number,
            "body": message,
        }
        response = requests.post(url, json.dumps(tmp_dict), headers=headers)
        if response and response.status_code == 201 or response.status_code == 200:
            json_send_message_response = json.loads(response.text)
            if json_send_message_response.get('sent'):
                _logger.info("\nSend Message successfully")
                self.env['whatsapp.msg'].create_whatsapp_message(whatsapp_number, message, json_send_message_response.get('id'),
                                                                 json_send_message_response.get('message'),
                                                                 "text", whatsapp_instance_id, 'res.users', user_id)

    def send_whatsapp_message_from_gupshup(self, values, whatsapp_number, whatsapp_instance_id):
        whatsapp_msg_source_number = whatsapp_instance_id.gupshup_source_number
        headers = {"Content-Type": "application/x-www-form-urlencoded", "apikey": whatsapp_instance_id.whatsapp_gupshup_api_key}
        opt_in_url = "https://api.gupshup.io/sm/api/v1/app/opt/in/" + whatsapp_instance_id.whatsapp_gupshup_app_name
        opt_in_response = requests.post(opt_in_url, data={'user': whatsapp_number}, headers=headers)
        if opt_in_response.status_code in [200, 202]:
            _logger.info("\nOpt-in partner successfully")
        data = {
            'source': whatsapp_msg_source_number,
            'destination': whatsapp_number,
            'template': json.dumps({
                'id': 'f186753c-3989-45b0-af9b-f2861dc2d3e3',
                'params': [values.get('name')]
            })
        }
        send_template_url = 'https://api.gupshup.io/sm/api/v1/template/msg'
        tmpl_response = requests.post(send_template_url, headers=headers, data=data)
        if tmpl_response.status_code in [200, 201, 202]:
            _logger.info("\nInitial Template called successfully")

        url = 'https://api.gupshup.io/sm/api/v1/msg'
        temp_data = {
            'channel': 'whatsapp',
            'source': whatsapp_msg_source_number,
            'destination': whatsapp_number,
            'message': json.dumps({
                'type': 'text',
                'text': _("Hello ") + values.get('name') + ',' + "\n" + _("You have successfully registered and logged in") + "\n" + _("*Your Email:* ") + " " + values.get('login')
            })
        }
        response = requests.post(url, headers=headers, data=temp_data)
        if response and response.status_code == 201 or response.status_code == 200:
            _logger.info("\nSend Message successfully")

    def send_whatsapp_message_from_gupshup_through_template(self, values, whatsapp_number, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'website_signup_page_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id), ('default_template', '=', True)])
        url = 'https://api.gupshup.io/sm/api/v1/template/msg'
        headers = {"Content-Type": "application/x-www-form-urlencoded", "apikey": whatsapp_instance_id.whatsapp_gupshup_api_key}
        user_id = self.env['res.users'].sudo().search([('login', '=', values.get('login'))])
        self.env['whatsapp.msg'].get_add_in_opt_in_user(whatsapp_instance_id, headers, whatsapp_number, user_id)
        if whatsapp_template_id.approval_state == 'APPROVED':
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": whatsapp_number,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            values.get('name'),
                            values.get('login'),
                        ]
                    }
                ),
            }
            response = requests.post(url, data=payload, headers=headers)
            if response and response.status_code == 201 or response.status_code == 200:
                json_send_message_response = json.loads(response.text)
                if json_send_message_response.get('sent'):
                    _logger.info("\nSend Message successfully")
                    message = _("Hello ") + values.get('name') + ',' + "\n" + _(
                        "You have successfully registered on our portal.") + "\n" + _("The connected email id is ") + " " + values.get('login')
                    self.env['whatsapp.msg'].create_whatsapp_message(whatsapp_number, message, json_send_message_response.get('id'),
                                                                     json_send_message_response.get('message'),
                                                                     "text", whatsapp_instance_id, 'res.users', user_id)
                    self.env['whatsapp.msg.res.partner'].with_context({'partner_id': user_id.partner_id.id}).gupshup_create_whatsapp_message(
                        whatsapp_number, message, json_send_message_response.get('messageId'), whatsapp_instance_id, 'res.users',
                        user_id)
            return True
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted' or whatsapp_template_id.approval_state == 'REJECTED':
            self.env['whatsapp.msg'].template_errors(whatsapp_template_id)
