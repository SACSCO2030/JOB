import logging
import requests
import json
import re
import html

from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProjectTask(models.Model):
    _inherit = 'project.task'

    whatsapp_msg_id = fields.Char('Whatsapp id')
    whatsapp_done_stage = fields.Boolean(string='Done')

    @api.model
    def create(self, vals):
        res = super(ProjectTask, self).create(vals)
        try:
            whatsapp_instance_id = self.env['whatsapp.instance'].get_whatsapp_instance()
            if whatsapp_instance_id.provider == "whatsapp_chat_api":
                if whatsapp_instance_id.send_whatsapp_through_template:
                    res.send_message_on_whatsapp_through_template(whatsapp_instance_id)
                else:
                    res.send_message_on_whatsapp(whatsapp_instance_id)

            elif whatsapp_instance_id.provider == "gupshup":
                if whatsapp_instance_id.send_whatsapp_through_template:
                    res.send_message_from_gupshup_through_template(whatsapp_instance_id)
                else:
                    res.send_message_from_gupshup_without_template(whatsapp_instance_id)

        except Exception as e_log:
            _logger.exception("Exception in creating project task  %s:\n", str(e_log))
        return res

    def cleanhtml(self, raw_html):
        cleanr = re.compile('<.*?>')
        cleantext = re.sub(cleanr, '', raw_html)
        return cleantext

    def convert_to_html(self, message):
        for data in re.findall(r'\*.*?\*', message):
            # comment = "fa fa-whatsapp"
            # message += comment
            # message = tools.append_content_to_html('<div class = "%s"></div>' % tools.ustr(comment))
            message = message.replace(data, '<span style="font-weight:bolder">' + data.strip('*') + '</span>')
        return message

    def send_message_on_whatsapp(self, whatsapp_instance_id):
        for user_id in self.user_ids:
            if user_id.partner_id.mobile:
                if user_id.partner_id.country_id.phone_code and user_id.partner_id.mobile:
                    msg = ''
                    mail_message_body = ''
                    whatsapp_msg_number = user_id.partner_id.mobile
                    whatsapp_msg_number_without_space = whatsapp_msg_number.replace(" ", "")
                    if '+' in whatsapp_msg_number_without_space:
                        whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace('+' + str(user_id.partner_id.country_id.phone_code), "")
                    else:
                        whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace(str(user_id.partner_id.country_id.phone_code), "")

                    if self.project_id.name:
                        msg += "*" + _("Project") + ":* " + self.project_id.name
                    if self.name:
                        msg += "\n*" + _("Task name") + ":* " + self.name
                    if self.date_deadline:
                        msg += "\n*" + _("Deadline") + ":* " + str(self.date_deadline)
                    if self.description:
                        if len(self.description) > 11:
                            msg += "\n*" + _("Description") + ":* " + self.cleanhtml(self.description)
                    msg = _("Hello") + " " + user_id.partner_id.name + "," + "\n" + _("New task assigned to you") + "\n" + msg
                    if whatsapp_instance_id.project_task_add_signature:
                        if whatsapp_instance_id.signature:
                            msg += "\n\n" + whatsapp_instance_id.signature
                    url = whatsapp_instance_id.whatsapp_endpoint + '/sendMessage?token=' + whatsapp_instance_id.whatsapp_token
                    headers = {"Content-Type": "application/json"}
                    mobile_with_country = str(user_id.partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code
                    tmp_dict = {
                        "phone": mobile_with_country,
                        "body": msg
                    }
                    response = requests.post(url, json.dumps(tmp_dict), headers=headers)
                    if response.status_code == 201 or response.status_code == 200:
                        json_send_message_response = json.loads(response.text)
                        if not json_send_message_response.get('sent') and json_send_message_response.get('error') and json_send_message_response.get(
                                'error').get('message') == 'Recipient is not a valid WhatsApp user':
                            raise UserError(_('Please add valid whatsapp number for %s ') % user_id.partner_id.name)
                        elif json_send_message_response.get('sent'):
                            _logger.info("\nSend Message successfully")
                            response_dict = response.json()
                            self.env['whatsapp.msg'].create_whatsapp_message(mobile_with_country, msg, json_send_message_response.get('id'),
                                                                             json_send_message_response.get('message'),
                                                                             "text", whatsapp_instance_id, 'project.task', self)
                            self.write({'whatsapp_msg_id': response_dict.get('id')})
                            # self._cr.execute("insert into project_task_user_rel ")
                            # self.whatsapp_msg_id = response_dict.get('id')
                            mail_message_obj = self.env['mail.message']
                            mail_message_body = """<p style='margin:0px; font-size:13px; font-family:"Lucida Grande", Helvetica, Verdana, Arial, sans-serif'><img src="/web_editor/font_to_img/62002/rgb(73,80,87)/13" data-class="fa fa-whatsapp" style="border-style:none; vertical-align:middle; height:auto; width:auto" width="0" height="0"></p>"""
                            mail_message_body += msg
                            body_msg = self.convert_to_html(mail_message_body)
                            body_mail_msg = "<br />".join(body_msg.split("\n"))
                            if whatsapp_instance_id.project_task_add_message_in_chatter:
                                mail_message_id = mail_message_obj.sudo().create({
                                    'res_id': self.id,
                                    'model': 'project.task',
                                    'body': body_mail_msg,
                                })

    def send_message_from_gupshup_without_template(self, whatsapp_instance_id):
        res_user_id = self.env['res.users'].search([('id', '=', self.env.user.id)])
        msg = ''
        mail_message_body = ''
        for user_id in self.user_ids:
            if user_id.partner_id.mobile and user_id.partner_id.country_id.phone_code and user_id.partner_id.mobile:
                whatsapp_number = user_id.partner_id.mobile
                whatsapp_msg_number_without_space = whatsapp_number.replace(" ", "")
                whatsapp_msg_number_without_plus = whatsapp_msg_number_without_space.replace('+', '')
                whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace('+' + str(user_id.partner_id.country_id.phone_code), "")
                whatsapp_msg_source_number = whatsapp_instance_id.gupshup_source_number
                headers = {"Content-Type": "application/x-www-form-urlencoded", "apikey": whatsapp_instance_id.whatsapp_gupshup_api_key}
                opt_in_list_url = "https://api.gupshup.io/sm/api/v1/users/" + whatsapp_instance_id.whatsapp_gupshup_app_name
                opt_in_list_response = requests.get(opt_in_list_url, headers=headers)
                registered_numbers = [user['phoneCode'] for user in opt_in_list_response.json().get('users')]
                if whatsapp_msg_number_without_code not in registered_numbers:
                    opt_in_url = "https://api.gupshup.io/sm/api/v1/app/opt/in/" + whatsapp_instance_id.whatsapp_gupshup_app_name
                    opt_in_response = requests.post(opt_in_url, data={'user': whatsapp_msg_number_without_plus}, headers=headers)
                if self.project_id.name:
                    msg += "*" + _("Project") + ":* "+self.project_id.name
                if self.name:
                    msg += "\n*" + _("Task name") + ":* "+self.name
                if self.date_deadline:
                    msg+= "\n*" + _("Deadline") + ":* "+str(self.date_deadline)
                if self.description:
                    if len(self.description) > 11:
                        msg += "\n*" + _("Description") + ":* "+self.cleanhtml(self.description)
                msg = _("Hello") + " " + user_id.partner_id.name + "," + "\n" + _("New task assigned to you") + "\n" + msg
                if res_user_id:
                    if res_user_id.has_group('pragmatic_odoo_whatsapp_integration.group_project_enable_signature'):
                        user_signature = self.cleanhtml(res_user_id.signature)
                        msg += "\n\n" + user_signature

                temp_data = {
                    'channel': 'whatsapp',
                    'source': whatsapp_msg_source_number,
                    'destination': whatsapp_msg_number_without_plus,
                    'message': json.dumps({
                        'type': 'text',
                        'text': msg
                    })
                }
                url = 'https://api.gupshup.io/sm/api/v1/msg'
                response = requests.post(url, headers=headers, data=temp_data)
                if response.status_code in [202, 201, 200]:
                    _logger.info("\nSend Message successfully")
                    whatsapp_msg = self.env['whatsapp.messages']
                    vals = {
                        'message_body': msg,
                        'senderName': whatsapp_instance_id.whatsapp_gupshup_app_name,
                        'state': 'sent',
                        'to': whatsapp_msg_source_number,
                        'partner_id': user_id.partner_id.id,
                        'time': fields.Datetime.now()
                    }
                    whatsapp_msg_id = whatsapp_msg.sudo().create(vals)
                    if whatsapp_msg_id:
                        _logger.info("\nWhatsApp message Created")

                    response_dict = response.json()
                    project_task_stage_personal_id = self.env['project.task.stage.personal'].sudo().search(
                        [('user_id', '=', user_id.id), ('task_id', '=', self.id)])
                    project_task_stage_personal_id.write({'whatsapp_msg_id': response_dict.get('id')})
                    mail_message_obj = self.env['mail.message']
                    mail_message_body = """<p style='margin:0px; font-size:13px; font-family:"Lucida Grande", Helvetica, Verdana, Arial, sans-serif'><img src="/web_editor/font_to_img/62002/rgb(73,80,87)/13" data-class="fa fa-whatsapp" style="border-style:none; vertical-align:middle; height:auto; width:auto" width="0" height="0"></p>"""
                    mail_message_body += msg
                    body_msg = self.convert_to_html(mail_message_body)
                    body_mail_msg = "<br />".join(body_msg.split("\n"))
                    if self.env['ir.config_parameter'].sudo().get_param(
                            'pragmatic_odoo_whatsapp_integration.group_project_display_chatter_message'):
                        mail_message_id = mail_message_obj.sudo().create({
                            'res_id': self.id,
                            'model': 'project.task',
                            'body': body_mail_msg,
                        })

    def send_message_from_gupshup_through_template(self, whatsapp_instance_id):
        url = 'https://api.gupshup.io/sm/api/v1/template/msg'
        headers = {"Content-Type": "application/x-www-form-urlencoded", "apikey": whatsapp_instance_id.whatsapp_gupshup_api_key}
        res_user_id = self.env['res.users'].search([('id', '=', self.env.user.id)])
        for user_id in self.user_ids:
            if user_id.partner_id.mobile:
                if user_id.partner_id.country_id.phone_code and user_id.partner_id.mobile:
                    whatsapp_msg_number = user_id.partner_id.mobile
                    whatsapp_msg_number_without_space = whatsapp_msg_number.replace(" ", "")
                    if '+' in whatsapp_msg_number_without_space:
                        number_without_code = whatsapp_msg_number_without_space.replace('+' + str(user_id.partner_id.country_id.phone_code), "")
                    else:
                        number_without_code = whatsapp_msg_number_without_space.replace(str(user_id.partner_id.country_id.phone_code), "")

                    response = None
                    if not whatsapp_instance_id.project_task_add_signature:
                        response = self.gupshup_template_project_task_without_signature(url, headers, user_id, number_without_code, whatsapp_instance_id)
                        message = self.create_project_task_message(user_id.partner_id, whatsapp_instance_id, signature=False)

                    else:
                        response = self.gupshup_template_project_task_with_signature(url, headers, user_id, number_without_code, whatsapp_instance_id)
                        message = self.create_project_task_message(user_id.partner_id, whatsapp_instance_id, signature=True)

                    if response.status_code == 201 or response.status_code == 200 or response.status_code == 202:
                        json_response = json.loads(response.text)
                        _logger.info("\nSend Message successfully")
                        mobile_with_country = str(user_id.partner_id.country_id.phone_code) + number_without_code
                        self.env['whatsapp.msg.res.partner'].with_context({'partner_id': user_id.partner_id.id}).gupshup_create_whatsapp_message(
                            str(user_id.partner_id.country_id.phone_code) + number_without_code, message, json_response.get('messageId'), whatsapp_instance_id, 'project.task',
                            self)
                        self.write({'whatsapp_msg_id': json_response.get('messageId')})
                        if whatsapp_instance_id.project_task_add_message_in_chatter:
                            mail_message_obj = self.env['mail.message']
                            mail_message_body = """<p style='margin:0px; font-size:13px; font-family:"Lucida Grande", Helvetica, Verdana, Arial, sans-serif'><img src="/web_editor/font_to_img/62002/rgb(73,80,87)/13" data-class="fa fa-whatsapp" style="border-style:none; vertical-align:middle; height:auto; width:auto" width="0" height="0"></p>"""
                            mail_message_body += message
                            body_msg = self.convert_to_html(mail_message_body)
                            body_mail_msg = "<br />".join(body_msg.split("\n"))
                            mail_message_obj.sudo().create({
                                'res_id': self.id,
                                'model': 'project.task',
                                'body': body_mail_msg,
                            })

                    return True

    def gupshup_template_project_task_without_signature(self, url, headers, user_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'project_task_without_signature_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            project_name = ''
            if self.project_id:
                project_name = self.project_id.name
            else:
                project_name = ' '
            date_deadline = ''
            if self.date_deadline:
                date_deadline = str(self.date_deadline)
            else:
                date_deadline = ' '
            description = ''
            if self.description:
                santized_description = self.cleanhtml(self.description)
                if santized_description:
                    description += self.cleanhtml(self.description)
                else:
                    description = ' '
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(user_id.partner_id.country_id.phone_code) + "" + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            user_id.partner_id.name,
                            project_name,
                            self.name,
                            date_deadline,
                            description
                        ]
                    }
                ),
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.env['whatsapp.msg'].template_errors(whatsapp_template_id)

    def gupshup_template_project_task_with_signature(self, url, headers, user_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'project_task_with_signature_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id),
             ('default_template', '=', True)], limit=1)
        if whatsapp_template_id.approval_state == 'APPROVED':
            project_name = ''
            if self.project_id:
                project_name = self.project_id.name
            else:
                project_name = ' '
            date_deadline = ''
            if self.date_deadline:
                date_deadline = str(self.date_deadline)
            else:
                date_deadline = ' '
            description = ''
            if self.description:
                santized_description = self.cleanhtml(self.description)
                if santized_description:
                    description += self.cleanhtml(self.description)
                else:
                    description = ' '
            instance_signature = ''
            if whatsapp_instance_id.signature:
                instance_signature = whatsapp_instance_id.signature
            else:
                instance_signature = self.env.user.company_id.name
            payload = {
                "source": whatsapp_instance_id.gupshup_source_number,
                "destination": str(user_id.partner_id.country_id.phone_code) + "" + number_without_code,
                "template": json.dumps(
                    {
                        "id": whatsapp_template_id.template_id,
                        "params": [
                            user_id.partner_id.name,
                            project_name,
                            self.name,
                            date_deadline,
                            description,
                            instance_signature
                        ]
                    }
                ),
            }
            return requests.post(url, data=payload, headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'REJECTED':
            self.env['whatsapp.msg'].template_errors(whatsapp_template_id)

    def send_message_on_whatsapp_through_template(self, whatsapp_instance_id):
        url = whatsapp_instance_id.whatsapp_endpoint + '/sendTemplate?token=' + whatsapp_instance_id.whatsapp_token
        headers = {"Content-Type": "application/json"}
        res_user_id = self.env['res.users'].search([('id', '=', self.env.user.id)])
        for user_id in self.user_ids:
            if user_id.partner_id.mobile:
                if user_id.partner_id.country_id.phone_code and user_id.partner_id.mobile:
                    whatsapp_msg_number = user_id.partner_id.mobile
                    whatsapp_msg_number_without_space = whatsapp_msg_number.replace(" ", "")
                    if '+' in whatsapp_msg_number_without_space:
                        number_without_code = whatsapp_msg_number_without_space.replace('+' + str(user_id.partner_id.country_id.phone_code), "")
                    else:
                        number_without_code = whatsapp_msg_number_without_space.replace(str(user_id.partner_id.country_id.phone_code), "")

                    response = None
                    if not whatsapp_instance_id.project_task_add_signature:
                        response = self.chat_api_template_project_task_without_signature(url, headers, user_id, number_without_code, whatsapp_instance_id)
                        message = self.create_project_task_message(user_id.partner_id, whatsapp_instance_id, signature=False)

                    else:
                        response = self.chat_api_template_project_task_with_signature(url, headers, user_id, number_without_code, whatsapp_instance_id)
                        message = self.create_project_task_message(user_id.partner_id, whatsapp_instance_id, signature=True)
                    if response.status_code == 201 or response.status_code == 200:
                        json_response = json.loads(response.text)
                        if json_response.get('sent') and json_response.get('description') == 'Message has been sent to the provider':
                            _logger.info("\nSend Message successfully")
                            mobile_with_country = str(user_id.partner_id.country_id.phone_code) + number_without_code
                            self.env['whatsapp.msg'].create_whatsapp_message(mobile_with_country, message, json_response.get('id'), json_response.get('message'), "text",
                                                                             whatsapp_instance_id,
                                                                             'project.task', self)
                            self.write({'whatsapp_msg_id': json_response.get('id')})
                            if whatsapp_instance_id.project_task_add_message_in_chatter:
                                mail_message_obj = self.env['mail.message']
                                mail_message_body = """<p style='margin:0px; font-size:13px; font-family:"Lucida Grande", Helvetica, Verdana, Arial, sans-serif'><img src="/web_editor/font_to_img/62002/rgb(73,80,87)/13" data-class="fa fa-whatsapp" style="border-style:none; vertical-align:middle; height:auto; width:auto" width="0" height="0"></p>"""
                                mail_message_body += message
                                body_msg = self.convert_to_html(mail_message_body)
                                body_mail_msg = "<br />".join(body_msg.split("\n"))
                                mail_message_obj.sudo().create({
                                    'res_id': self.id,
                                    'model': 'project.task',
                                    'body': body_mail_msg,
                                })

                        elif not json_response.get('sent') and json_response.get('error').get('message') == 'Recipient is not a valid WhatsApp user':
                            raise UserError(_('Please add valid whatsapp number for %s customer') % user_id.partner_id.name)
                        elif not json_response.get('sent') and json_response.get('message'):
                            raise UserError(_('%s') % json_response.get('message'))
                    return True

    def create_project_task_message(self, res_partner_id, whatsapp_instance_id, signature):
        message = ''
        if self.project_id.name:
            message += "*" + _("Project") + ":* " + self.project_id.name
        if self.name:
            message += "\n*" + _("Task name") + ":* " + self.name
        if self.date_deadline:
            message += "\n*" + _("Deadline") + ":* " + str(self.date_deadline)
        if self.description:
            if len(self.description) > 11:
                message += "\n*" + _("Description") + ":* " + self.cleanhtml(self.description)
        message = _('Hello') + ' ' + res_partner_id.name + ',' + '\n' + _("New task assigned to you") + '\n' + message
        if signature:
            message += whatsapp_instance_id.signature
        return message

    def chat_api_template_project_task_without_signature(self, url, headers, user_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'project_task_without_signature_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id), ('default_template', '=', True)])
        if whatsapp_template_id.approval_state == 'approved':
            project_name = ''
            if self.project_id:
                project_name = self.project_id.name
            else:
                project_name = ' '
            date_deadline = ''
            if self.date_deadline:
                date_deadline = str(self.date_deadline)
            else:
                date_deadline = ' '
            description = ''
            if self.description:
                santized_description = self.cleanhtml(self.description)
                if santized_description:
                    description += self.cleanhtml(self.description)
                else:
                    description = ' '
            else:
                description = ' '

            payload = {
                "template": whatsapp_template_id.name,
                "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                "namespace": whatsapp_template_id.namespace,
                "params": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": user_id.partner_id.name},
                            {"type": "text", "text": project_name},
                            {"type": "text", "text": self.name},
                            {"type": "text", "text": date_deadline},
                            {"type": "text", "text": description},
                        ]
                    }
                ],
                "phone": str(user_id.partner_id.country_id.phone_code) + "" + number_without_code
            }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted':
            self.env['whatsapp.msg'].template_errors(whatsapp_template_id)

    def chat_api_template_project_task_with_signature(self, url, headers, user_id, number_without_code, whatsapp_instance_id):
        whatsapp_template_id = self.env['whatsapp.templates'].sudo().search(
            [('name', '=', 'project_task_with_signature_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id), ('default_template', '=', True)])

        if whatsapp_template_id.approval_state == 'approved':
            project_name = ''
            if self.project_id:
                project_name += self.project_id.name
            else:
                project_name = ' '
            date_deadline = ''
            if self.date_deadline:
                date_deadline += str(self.date_deadline)
            else:
                date_deadline = ' '
            description = ''
            if self.description:
                santized_description = self.cleanhtml(self.description)
                if santized_description:
                    description = santized_description
                else:
                    description = ' '
            else:
                description = ' '

            payload = {
                "template": whatsapp_template_id.name,
                "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                "namespace": whatsapp_template_id.namespace,
                "params": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": user_id.partner_id.name},
                            {"type": "text", "text": project_name},
                            {"type": "text", "text": self.name},
                            {"type": "text", "text": date_deadline},
                            {"type": "text", "text": description},
                        ]
                    },
                    {
                        "type": "footer",
                        "parameters": [{"type": "footer", "text": whatsapp_template_id.footer}]
                    }
                ],
                "phone": str(user_id.partner_id.country_id.phone_code) + "" + number_without_code
            }
            return requests.post(url, data=json.dumps(payload), headers=headers)
        elif not whatsapp_template_id or not whatsapp_template_id.approval_state or whatsapp_template_id.approval_state == 'submitted':
            self.env['whatsapp.msg'].template_errors(whatsapp_template_id)
