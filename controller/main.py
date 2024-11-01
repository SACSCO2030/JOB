from odoo import http, _, modules
import logging
import json
from werkzeug.exceptions import Forbidden, NotFound
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.addons.web.controllers.main import ensure_db, Home, SIGN_UP_REQUEST_PARAMS
import phonenumbers
import datetime
import time
from odoo.http import request, JsonRPCDispatcher, Response
from odoo.tools import date_utils
import pytz
from odoo.tools import ustr
import requests
import base64
from odoo.service import common as auth, model
import io
import os
import mimetypes

_logger = logging.getLogger(__name__)
from odoo.addons.web.controllers.main import ensure_db, Home, SIGN_UP_REQUEST_PARAMS

from odoo.addons.phone_validation.tools import phone_validation
from ...pragtech_whatsapp_base.controller.main import WhatsappBase
import werkzeug.datastructures
import werkzeug.exceptions
import werkzeug.local
import werkzeug.routing
import werkzeug.security
import werkzeug.wrappers
import werkzeug.wsgi
import functools

from werkzeug.urls import URL, url_parse, url_encode, url_quote
from werkzeug.exceptions import (HTTPException, BadRequest, Forbidden,
                                 NotFound, InternalServerError)
try:
    from werkzeug.middleware.proxy_fix import ProxyFix as ProxyFix_
    ProxyFix = functools.partial(ProxyFix_, x_for=1, x_proto=1, x_host=1)
except ImportError:
    from werkzeug.contrib.fixers import ProxyFix

try:
    from werkzeug.utils import send_file as _send_file
except ImportError:
    pass
    # from .tools._vendor.send_file import send_file as _send_file

def make_json_response_inherit(self, data, headers=None, cookies=None, status=200):
    """ Helper for JSON responses, it json-serializes ``data`` and
    sets the Content-Type header accordingly if none is provided.

    :param data: the data that will be json-serialized into the response body
    :param int status: http status code
    :param List[(str, str)] headers: HTTP headers to set on the response
    :param collections.abc.Mapping cookies: cookies to set on the client
    :rtype: :class:`~odoo.http.Response`
    """
    data = json.dumps(data, ensure_ascii=False, default=date_utils.json_default)

    headers = werkzeug.datastructures.Headers(headers)
    headers['Content-Length'] = len(data)
    if 'Content-Type' not in headers:
        headers['Content-Type'] = 'application/json; charset=utf-8'
    data = ''
    return request.make_response(data, headers.to_wsgi_list(), cookies, status)


# def _json_response_inherit(self, result=None, error=None):
#     print("\nIn whatsapp integration _json_response_inherit: ",_json_response_inherit)
#     response = ''
#     if error is not None:
#         response = error
#     if result is not None:
#         response = result
#     mime = 'application/json'
#     # body = json.dumps(response, default=date_utils.json_default)
#     body = ''
#     res = Response(
#         body, status=error and error.pop('http_status', 200) or 200,
#         headers=[('Content-Type', mime), ('Content-Length', len(body))]
#     )
#     print("\n_json_response_inherit res: ",res,"\ttype: ",type(res))
#     return res


class AttachmentGlobalUrl(http.Controller):

    @http.route(['/whatsapp_attachment/<string:whatsapp_access_token>/get_attachment'], type='http', auth='public')
    def social_post_instagram_image(self, whatsapp_access_token):
        social_post = request.env['ir.attachment'].sudo().search(
            [('access_token', '=', whatsapp_access_token)])

        if not social_post:
            raise Forbidden()
        
        if social_post["type"] == "url":
            if social_post["url"]:
                return request.redirect(social_post["url"])
            else:
                return request.not_found()
        elif social_post["datas"]:
            data = io.BytesIO(base64.standard_b64decode(social_post["datas"]))
            # we follow what is done in ir_http's binary_content for the extension management
            extension = os.path.splitext(social_post["name"] or '')[1]
            extension = extension if extension else mimetypes.guess_extension(social_post["mimetype"] or '')
            filename = social_post['name']
            filename = filename if os.path.splitext(filename)[1] else filename + extension
            return http.send_file(data, filename=filename, as_attachment=True)
        else:
            return request.not_found()


        # status, headers, image_base64 = request.env['ir.http'].sudo().binary_content(
        #     id=social_post.id,
        #     default_mimetype='image/jpeg'
        # )

        # return request.env['ir.http']._get_serve_attachment(status, headers, image_base64)


class SendMessage(http.Controller):
    _name = 'send.message.controller'

    def format_amount(self, amount, currency):
        fmt = "%.{0}f".format(currency.decimal_places)
        lang = http.request.env['res.lang']._lang_get(http.request.env.context.get('lang') or 'en_US')

        formatted_amount = lang.format(fmt, currency.round(amount), grouping=True, monetary=True) \
            .replace(r' ', u'\N{NO-BREAK SPACE}').replace(r'-', u'-\N{ZERO WIDTH NO-BREAK SPACE}')
        pre = post = u''
        if currency.position == 'before':
            pre = u'{symbol}\N{NO-BREAK SPACE}'.format(symbol=currency.symbol or '')
        else:
            post = u'\N{NO-BREAK SPACE}{symbol}'.format(symbol=currency.symbol or '')
        return u'{pre}{0}{post}'.format(formatted_amount, pre=pre, post=post)

    @http.route('/whatsapp/send/message', type='http', auth='user', website=True, csrf=False)
    def sale_order_paid_status(self, **post):
        whatsapp_instance_id = http.request.env['whatsapp.instance'].get_whatsapp_instance()
        if whatsapp_instance_id.provider == "whatsapp_chat_api":
            if whatsapp_instance_id.send_whatsapp_through_template:
                return self.chat_api_send_pos_whatsapp_message_through_template(post, whatsapp_instance_id)
            else:
                return self.chat_api_send_pos_whatsapp_message_without_template(post, whatsapp_instance_id)
        elif whatsapp_instance_id.provider == "gupshup":
            if whatsapp_instance_id.send_whatsapp_through_template:
                return self.gupshup_send_pos_whatsapp_message_through_template(post, whatsapp_instance_id)
            else:
                return self.gupshup_send_pos_whatsapp_message_without_template(post, whatsapp_instance_id)

    def chat_api_send_pos_whatsapp_message_through_template(self, post, whatsapp_instance_id):
        url = whatsapp_instance_id.whatsapp_endpoint + '/sendTemplate?token=' + whatsapp_instance_id.whatsapp_token
        headers = {"Content-Type": "application/json"}
        pos_order = http.request.env['pos.order'].sudo().search([('pos_reference', '=', post.get('order'))])
        user_context = pos_order.env.context.copy()
        user_context.update({'lang': pos_order.partner_id.lang})
        pos_order.env.context = user_context

        context = request.env.context.copy()
        context.update({'lang': pos_order.partner_id.lang})
        request.env.context = context
        if pos_order.partner_id:
            context = request.env.context.copy()
            context.update({'lang': pos_order.partner_id.lang})
            request.env.context = context
            if pos_order.partner_id.mobile and pos_order.partner_id.country_id.phone_code:
                whatsapp_template_id = http.request.env['whatsapp.templates'].sudo().search(
                    [('name', '=', 'send_pos_message_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id), ('default_template', '=', True)])
                whatsapp_number = pos_order.partner_id.mobile
                whatsapp_msg_number_without_space = whatsapp_number.replace(" ", "")
                whatsapp_msg_number_without_code = ''
                if '+' in whatsapp_msg_number_without_space:
                    whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace('+' + str(pos_order.partner_id.country_id.phone_code), "")
                else:
                    whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace(str(pos_order.partner_id.country_id.phone_code), "")
                if whatsapp_template_id.approval_state == 'approved':
                    line_count = 1
                    msg = ''
                    for line_id in pos_order.lines:
                        if line_id:
                            if line_id.product_id:
                                msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.name
                            if line_id.qty:
                                msg += "  *" + _("Qty") + ":* " + str(line_id.qty)
                            if line_id.price_unit:
                                msg += "  *" + _("Unit Price") + ":* " + str(line_id.price_unit)
                            if line_id.price_subtotal:
                                msg += "  *" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                            line_count += 1
                    payload = {
                        "template": whatsapp_template_id.name,
                        "language": {"policy": "deterministic", "code": whatsapp_template_id.languages.iso_code},
                        "namespace": whatsapp_template_id.namespace,
                        "params": [
                            {
                                "type": "body",
                                "parameters": [
                                    {"type": "text", "text": pos_order.partner_id.name},
                                    {"type": "text", "text": pos_order.name},
                                    {"type": "text", "text": self.format_amount(pos_order.amount_total, pos_order.pricelist_id.currency_id)},
                                    {"type": "text", "text": msg},
                                ]
                            }
                        ],
                        "phone": str(pos_order.partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code
                    }
                    response = requests.post(url, data=json.dumps(payload), headers=headers)
                    if response.status_code == 201 or response.status_code == 200:
                        json_response = json.loads(response.text)
                        if json_response.get('sent') and json_response.get('description') == 'Message has been sent to the provider':
                            _logger.info("\nSend Message successfully")
                            message = _("Hello") + " " + pos_order.partner_id.name
                            if pos_order.partner_id.parent_id:
                                msg += "(" + pos_order.partner_id.parent_id.name + ")"
                            message += "\n\n" + _("Your") + " "
                            message += _("POS") + " *" + pos_order.name + "* "
                            message += " " + _("with Total Amount") + " " + self.format_amount(pos_order.amount_total, pos_order.pricelist_id.currency_id) + "."
                            message += "\n\n" + _("Following is your order details.")
                            message += msg
                            mobile_with_country = str(pos_order.partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code
                            http.request.env['whatsapp.msg'].create_whatsapp_message(mobile_with_country, message, json_response.get('id'), json_response.get('message'), "text",
                                                                                     whatsapp_instance_id,
                                                                                     'pos.order', pos_order)
                            return "Send Message successfully"
                        elif not json_response.get('sent') and json_response.get('error').get('message') == 'Recipient is not a valid WhatsApp user':
                            return "Phone not exists on whatsapp"

    def chat_api_send_pos_whatsapp_message_without_template(self, post, whatsapp_instance_id):
        pos_order = http.request.env['pos.order'].sudo().search([('pos_reference', '=', post.get('order'))])
        user_context = pos_order.env.context.copy()
        user_context.update({'lang': pos_order.partner_id.lang})
        pos_order.env.context = user_context

        context = request.env.context.copy()
        context.update({'lang': pos_order.partner_id.lang})
        request.env.context = context
        if pos_order.partner_id:
            context = request.env.context.copy()
            context.update({'lang': pos_order.partner_id.lang})
            request.env.context = context
            if pos_order.partner_id.mobile and pos_order.partner_id.country_id.phone_code:
                doc_name = _("POS")
                msg = _("Hello") + " " + pos_order.partner_id.name
                if pos_order.partner_id.parent_id:
                    msg += "(" + pos_order.partner_id.parent_id.name + ")"
                msg += "\n\n" + _("Your") + " "
                msg += doc_name + " *" + pos_order.name + "* "
                msg += " " + _("with Total Amount") + " " + self.format_amount(pos_order.amount_total, pos_order.pricelist_id.currency_id) + "."
                msg += "\n\n" + _("Following is your order details.")
                for line_id in pos_order.lines:
                    msg += "\n\n*" + _("Product") + ":* " + line_id.product_id.name + "\n*" + _("Qty") + ":* " + str(line_id.qty) + " " + "\n*" + _("Unit Price") + ":* " + str(
                        line_id.price_unit) + "\n*" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                    msg += "\n------------------"
                whatsapp_number = pos_order.partner_id.mobile
                whatsapp_msg_number_without_space = whatsapp_number.replace(" ", "")
                if '+' in whatsapp_msg_number_without_space:
                    whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace(
                        '+' + str(pos_order.partner_id.country_id.phone_code), "")
                else:
                    whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace(str(pos_order.partner_id.country_id.phone_code), "")
                url = whatsapp_instance_id.whatsapp_endpoint + '/sendMessage?token=' + whatsapp_instance_id.whatsapp_token
                headers = {"Content-Type": "application/json"}
                mobile_with_country = str(pos_order.partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code
                tmp_dict = {"phone": str(pos_order.partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code, "body": msg}
                response = requests.post(url, json.dumps(tmp_dict), headers=headers)
                if response.status_code == 201 or response.status_code == 200:
                    json_send_message_response = json.loads(response.text)
                    if not json_send_message_response.get('sent') and json_send_message_response.get('error') and json_send_message_response.get(
                            'error').get('message') == 'Recipient is not a valid WhatsApp user':
                        return "Phone not exists on whatsapp"
                    elif json_send_message_response.get('sent'):
                        _logger.info("\nSend Message successfully")
                        json_send_message_response = json.loads(response.text)
                        http.request.env['whatsapp.msg'].create_whatsapp_message(mobile_with_country, msg, json_send_message_response.get('id'),
                                                                                 json_send_message_response.get('message'),
                                                                                 "text", whatsapp_instance_id, 'pos.order', pos_order)
                        return "Send Message successfully"

    def gupshup_send_pos_whatsapp_message_through_template(self, post, whatsapp_instance_id):
        url = 'https://api.gupshup.io/sm/api/v1/template/msg'
        headers = {"Content-Type": "application/x-www-form-urlencoded", "apikey": whatsapp_instance_id.whatsapp_gupshup_api_key}
        pos_order = http.request.env['pos.order'].sudo().search([('pos_reference', '=', post.get('order'))])
        user_context = pos_order.env.context.copy()
        user_context.update({'lang': pos_order.partner_id.lang})
        pos_order.env.context = user_context

        context = request.env.context.copy()
        context.update({'lang': pos_order.partner_id.lang})
        request.env.context = context
        if pos_order.partner_id:
            context = request.env.context.copy()
            context.update({'lang': pos_order.partner_id.lang})
            request.env.context = context
            if pos_order.partner_id.mobile and pos_order.partner_id.country_id.phone_code:
                whatsapp_template_id = http.request.env['whatsapp.templates'].sudo().search(
                    [('name', '=', 'send_pos_message_' + whatsapp_instance_id.sequence), ('whatsapp_instance_id', '=', whatsapp_instance_id.id), ('default_template', '=', True)])
                whatsapp_number = pos_order.partner_id.mobile
                whatsapp_msg_number_without_space = whatsapp_number.replace(" ", "")
                whatsapp_msg_number_without_code = ''
                if '+' in whatsapp_msg_number_without_space:
                    whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace('+' + str(pos_order.partner_id.country_id.phone_code), "")
                else:
                    whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace(str(pos_order.partner_id.country_id.phone_code), "")
                if whatsapp_template_id.approval_state == 'APPROVED':
                    line_count = 1
                    msg = ''
                    for line_id in pos_order.lines:
                        if line_id:
                            if line_id.product_id:
                                msg += " *" + _("Product") + str(line_count) + ":* " + line_id.product_id.name
                            if line_id.qty:
                                msg += "  *" + _("Qty") + ":* " + str(line_id.qty)
                            if line_id.price_unit:
                                msg += "  *" + _("Unit Price") + ":* " + str(line_id.price_unit)
                            if line_id.price_subtotal:
                                msg += "  *" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                            line_count += 1
                    payload = {
                        "source": whatsapp_instance_id.gupshup_source_number,
                        "destination": str(pos_order.partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
                        "template": json.dumps(
                            {
                                "id": whatsapp_template_id.template_id,
                                "params": [
                                    pos_order.partner_id.name,
                                    pos_order.name,
                                    self.format_amount(pos_order.amount_total, pos_order.pricelist_id.currency_id),
                                    msg,
                                ]
                            }
                        ),
                    }
                    response = requests.post(url, data=payload, headers=headers)
                    if response.status_code == 201 or response.status_code == 200 or response.status_code == 202:
                        json_response = json.loads(response.text)
                        _logger.info("\nSend Message successfully")
                        message = _("Hello") + " " + pos_order.partner_id.name
                        if pos_order.partner_id.parent_id:
                            msg += "(" + pos_order.partner_id.parent_id.name + ")"
                        message += "\n\n" + _("Your") + " "
                        message += _("POS") + " *" + pos_order.name + "* "
                        message += " " + _("with Total Amount") + " " + self.format_amount(pos_order.amount_total, pos_order.pricelist_id.currency_id) + "."
                        message += "\n\n" + _("Following is your order details.")
                        message += msg
                        mobile_with_country = str(pos_order.partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code
                        http.request.env['whatsapp.msg.res.partner'].with_context({'partner_id': pos_order.partner_id.id}).gupshup_create_whatsapp_message(
                            str(pos_order.partner_id.country_id.phone_code) + whatsapp_msg_number_without_code, message, json_response.get('messageId'), whatsapp_instance_id,
                            'pos.order',
                            pos_order)
                        return "Send Message successfully"

    def gupshup_send_pos_whatsapp_message_without_template(self, post, whatsapp_instance_id):
        pos_order = http.request.env['pos.order'].sudo().search([('pos_reference', '=', post.get('order'))])
        user_context = pos_order.env.context.copy()
        user_context.update({'lang': pos_order.partner_id.lang})
        pos_order.env.context = user_context

        context = request.env.context.copy()
        context.update({'lang': pos_order.partner_id.lang})
        request.env.context = context
        if pos_order.partner_id:
            context = request.env.context.copy()
            context.update({'lang': pos_order.partner_id.lang})
            request.env.context = context
            if pos_order.partner_id.mobile and pos_order.partner_id.country_id.phone_code:
                doc_name = _("POS")
                msg = _("Hello") + " " + pos_order.partner_id.name
                if pos_order.partner_id.parent_id:
                    msg += "(" + pos_order.partner_id.parent_id.name + ")"
                msg += "\n\n" + _("Your") + " "
                msg += doc_name + " *" + pos_order.name + "* "
                msg += " " + _("with Total Amount") + " " + self.format_amount(pos_order.amount_total, pos_order.pricelist_id.currency_id) + "."
                msg += "\n\n" + _("Following is your order details.")
                for line_id in pos_order.lines:
                    msg += "\n\n*" + _("Product") + ":* " + line_id.product_id.name + "\n*" + _("Qty") + ":* " + str(line_id.qty) + " " + "\n*" + _("Unit Price") + ":* " + str(
                        line_id.price_unit) + "\n*" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                    msg += "\n------------------"
                whatsapp_number = pos_order.partner_id.mobile
                whatsapp_msg_number_without_space = whatsapp_number.replace(" ", "")
                whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace('+' + str(pos_order.partner_id.country_id.phone_code), "")
                url = 'https://api.gupshup.io/sm/api/v1/msg'
                headers = {"Content-Type": "application/x-www-form-urlencoded", "apikey": whatsapp_instance_id.whatsapp_gupshup_api_key}
                temp_data = {
                    'channel': 'whatsapp',
                    'source': whatsapp_instance_id.gupshup_source_number,
                    'destination': str(pos_order.partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
                    'message': json.dumps({
                        'type': 'text',
                        'text': msg
                    })
                }
                response = requests.post(url, temp_data, headers=headers)
                if response.status_code == 201 or response.status_code == 200 or response.status_code == 202:
                    json_send_message_response = json.loads(response.text)
                    _logger.info("\nSend Message successfully")
                    http.request.env['whatsapp.msg.res.partner'].with_context({'partner_id': pos_order.partner_id.id}).gupshup_create_whatsapp_message(
                        str(pos_order.partner_id.country_id.phone_code) + whatsapp_msg_number_without_code, msg, json_send_message_response.get('messageId'), whatsapp_instance_id,
                        'pos.order', pos_order)
                    return "Send Message successfully"


class AuthSignupHomeDerived(AuthSignupHome):

    def get_auth_signup_config(self):
        """retrieve the module config (which features are enabled) for the login page"""
        get_param = request.env['ir.config_parameter'].sudo().get_param
        countries = request.env['res.country'].sudo().search([])
        return {
            'signup_enabled': request.env['res.users']._get_signup_invitation_scope() == 'b2c',
            'reset_password_enabled': get_param('auth_signup.reset_password') == 'True',
            'countries': countries
        }

    def get_auth_signup_qcontext(self):
        SIGN_UP_REQUEST_PARAMS.add('mobile')
        qcontext = super().get_auth_signup_qcontext()
        return qcontext

    def do_signup(self, qcontext):
        """ Shared helper that creates a res.partner out of a token """
        values = self._prepare_signup_values(qcontext)
        if qcontext.get('country_id'):
            values['country_id'] = qcontext.get('country_id')
        if qcontext.get('mobile'):
            values['mobile'] = qcontext.get('mobile')
        self._signup_with_values(qcontext.get('token'), values)
        request.env.cr.commit()


class WhatsappIntegration(WhatsappBase):

    def convert_epoch_to_unix_timestamp(self, msg_time):
        # msg_time = int(msg_time)
        formatted_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(msg_time))
        date_time_obj = datetime.datetime.strptime(formatted_time, '%Y-%m-%d %H:%M:%S')
        dt = False
        if date_time_obj:
            timezone = pytz.timezone(request.env['res.users'].sudo().browse([int(2)]).tz or 'UTC')
        dt = pytz.UTC.localize(date_time_obj)
        dt = dt.astimezone(timezone)
        dt = ustr(dt).split('+')[0]
        return date_time_obj

    @http.route(['/whatsapp/response/message'], type='json', auth='public')
    def whatsapp_response(self):
        super(WhatsappIntegration, self).whatsapp_response()
        _logger.info("In chat api whatsapp integration controller-----------------------")

        data = json.loads(request.httprequest.data)
        _logger.info("data %s: ", str(data))
        _request = data
        if 'messages' in data and data['messages']:
            msg_list = []
            msg_dict = {}
            res_partner_obj = request.env['res.partner']
            whatapp_msg = request.env['whatsapp.messages']
            mail_channel_obj = request.env['mail.channel']
            mail_message_obj = request.env['mail.message']
            project_task_obj = request.env['project.task']

            for msg in data['messages']:
                if 'quotedMsgId' in msg and msg['quotedMsgId']:
                    project_task_id = project_task_obj.sudo().search([('whatsapp_msg_id', '=', msg['quotedMsgId'])])
                    chat_id = msg['chatId']
                    chatid_split = chat_id.split('@')
                    mobile = '+' + chatid_split[0]
                    mobile_coutry_code = phonenumbers.parse(mobile, None)
                    mobile_number = mobile_coutry_code.national_number
                    country_code = mobile_coutry_code.country_code
                    res_country_id = request.env['res.country'].sudo().search([('phone_code', '=', country_code)], limit=1)
                    reg_sanitized_number = phone_validation.phone_format(str(mobile_number), res_country_id.code, country_code)
                    res_partner_obj = res_partner_obj.sudo().search([('mobile', '=', reg_sanitized_number)], limit=1)
                    mail_message_id = mail_message_obj.sudo().search([('whatsapp_message_id', '=', msg['quotedMsgId'])], limit=1)
                    if mail_message_id.model == 'mail.channel' and mail_message_id.res_id:
                        channel_id = mail_channel_obj.sudo().search([('id', '=', mail_message_id.res_id)])
                        channel_id.with_context(from_odoobot=True).message_post(body=msg['body'], message_type="notification",
                                                                                subtype_xmlid="mail.mt_comment", author_id=res_partner_obj.id)
                        mail_message_id.with_context(from_odoobot=True)
                    if project_task_id:
                        if msg.get('body') == 'done' or msg.get('body') == 'Done':
                            project_task_update_record = project_task_id.write({'whatsapp_done_stage': True})

                else:
                    if '@c.us' in msg['chatId'] and not msg.get('fromMe'):  # @c.us is for contacts & @g.us is for group
                        res_partner_id = res_partner_obj.sudo().search([('chatId', '=', msg['chatId'])], limit=1)

                        if res_partner_id:
                            self.send_notification_to_admin(res_partner_id, msg)

                        _logger.info("msg_dict %s: ", str(msg_dict))
                        if len(msg_dict) > 0:
                            msg_list.append(msg_dict)
            for msg in msg_list:
                whatapp_msg_id = whatapp_msg.sudo().search([('message_id', '=', msg.get('message_id'))])
                if whatapp_msg_id:
                    whatapp_msg_id.sudo().write(msg)
                    _logger.info("whatapp_msg_id %s: ", str(whatapp_msg_id))
                    if 'messages' in data and data['messages']:
                        for msg in data['messages']:
                            if whatapp_msg_id and msg['type'] == 'document':
                                msg_attchment_dict = {}
                                url = msg['body']
                                data_base64 = base64.b64encode(requests.get(url.strip()).content)
                                msg_attchment_dict = {'datas': data_base64, 'type': 'binary',
                                                      'res_model': 'whatsapp.messages', 'res_id': whatapp_msg_id.id}
                                if msg.get('caption'):
                                    msg_attchment_dict['name'] = msg.get('caption')
                                elif msg.get('name'):
                                    msg_attchment_dict['name'] = msg.get('name')
                                elif msg.get('body'):
                                    msg_attchment_dict['name'] = msg.get('body')
                                attachment_id = request.env['ir.attachment'].sudo().create(msg_attchment_dict)
                                res_update_whatsapp_msg = whatapp_msg_id.sudo().write({'attachment_id': attachment_id.id})
                                if res_update_whatsapp_msg:
                                    _logger.info("whatapp_msg_id %s: ", str(whatapp_msg_id.id))
                else:
                    res_whatsapp_msg = whatapp_msg.sudo().create(msg)
                    _logger.info("res_whatsapp_msg2111 %s: ", str(res_whatsapp_msg))
                    if 'messages' in data and data['messages']:
                        for msg in data['messages']:
                            if res_whatsapp_msg and msg['type'] == 'document':
                                msg_attchment_dict = {}
                                url = msg['body']
                                data_base64 = base64.b64encode(requests.get(url.strip()).content)
                                msg_attchment_dict = {'type': 'binary',
                                                      'res_model': 'whatsapp.messages', 'res_id': res_whatsapp_msg.id}
                                if msg.get('caption'):
                                    msg_attchment_dict['name'] = msg.get('caption')
                                elif msg.get('name'):
                                    msg_attchment_dict['name'] = msg.get('name')
                                elif msg.get('body'):
                                    msg_attchment_dict['name'] = msg.get('body')
                                if data_base64:
                                    msg_attchment_dict['datas'] = data_base64
                                attachment_id = request.env['ir.attachment'].sudo().create(msg_attchment_dict)
                                res_update_whatsapp_msg = res_whatsapp_msg.sudo().write({'attachment_id': attachment_id.id})
                                if res_update_whatsapp_msg:
                                    _logger.info("res_whatsapp_msg %s: ", str(res_whatsapp_msg.id))

        return 'OK'

    @http.route(['/gupshup/response/message'], type='json', auth='public')
    def gupshup_whatsapp_response(self):
        _logger.info("\n---------------------In whatsapp integration gupshup controller-----------------------")
        super(WhatsappIntegration, self).gupshup_whatsapp_response()
        data = json.loads(request.httprequest.data)
        _logger.info("data from gupshup %s: ", str(data))
        if data.get('type') == 'message' and data['payload'] and data['payload'].get('sender'):
            payload = data['payload'].get('sender')
            text_payload = data['payload'].get('payload')
            res_partner_obj = request.env['res.partner'].sudo()
            whatsapp_msg = request.env['whatsapp.messages']
            whatsapp_instance_id = request.env['whatsapp.instance'].get_whatsapp_instance()
            whatsapp_msg_source_number = whatsapp_instance_id.gupshup_source_number
            sender_phone = payload.get('phone')
            timestamp = ''
            if payload.get('timestamp'):
                timestamp = self.gupshup_convert_epoch_to_unix_timestamp(payload.get('timestamp'))
            message = text_payload.get('text')
            message_id = text_payload.get('id')
            sender_name = payload.get('name')
            res_partner = False
            for partner in res_partner_obj.search([('mobile', '!=', False)]):
                partner_phone = partner.mobile.replace(" ", "")
                phone = partner_phone.replace("+", "")
                if phone == sender_phone:
                    res_partner = partner

            whatsapp_msg_id = whatsapp_msg.sudo().search([('message_id', '=', data['payload'].get('id'))])
            if whatsapp_msg_id:
                pass
            else:
                whatsapp_message_dict = {
                    'message_body': message,
                    'senderName': sender_name,
                    'state': 'received',
                    'message_id': message_id,
                    'to': whatsapp_msg_source_number,
                    'partner_id': res_partner.id,
                }
                if timestamp:
                    whatsapp_message_dict['time'] = timestamp
                whatsapp_message_id = whatsapp_msg.sudo().create(whatsapp_message_dict)
                if whatsapp_message_id:
                    _logger.info("Whatsapp Message created in odoo from gupshup %s: ", str(whatsapp_message_id.id))
            error = None
            result = None
            request_id = request.jsonrequest.get('id')
            status = 200
            response = {'jsonrpc': '2.0', 'id': request_id}
            # print("\naddons response: ", response)
            if error is not None:
                response['error'] = error
                status = error.pop('http_status', 200)
            if result is not None:
                response['result'] = result
            res = request.request.make_json_response(response)
            # ir_http = request.registry['ir.http']
            # rule, args = ir_http._match(request.httprequest.path)
            # request._set_request_dispatcher(rule)
            # request.dispatcher.pre_dispatch(rule, args)
            # response = request.dispatcher.dispatch(rule.endpoint, args)
            # request.dispatcher.post_dispatch(response)
            # response = request.dispatcher.dispatch(rule.endpoint, args)
            # ir_http._post_dispatch(response)
            # print("\nintegration23333333")
            # request._json_response = self.make_json_response_inherit(request, JsonRPCDispatcher)

            # request._json_response = _json_response_inherit.__get__(request, JsonRPCDispatcher)
            # uid = auth.dispatch('authenticate', [request.env.cr.dbname, 'admin', 'admin', {}])
            # print("\nuid: ",uid)
            # ctx = model.dispatch('execute_kw', [
            #     request.env.cr.dbname, uid, 'admin',
            #     'res.users', 'context_get', []
            # ])
            # print("\nctx in whatsapp integration: ",ctx)
            # request._json_response = _json_response_inherit.__get__(request, ctx)
            return 'OK'

    def whatsapp_marketing_bidirectional_message(self, data):
        _logger.info("In whatsapp integration marketing controller")
        if 'messages' in data and data['messages']:
            msg_dict = {}
            whatsapp_contact_obj = request.env['whatsapp.contact']
            whatapp_msg = request.env['whatsapp.messages']
            for msg in data['messages']:
                if 'chatId' in msg and msg['chatId']:
                    whatsapp_contact_obj = whatsapp_contact_obj.sudo().search([('whatsapp_id', '=', msg['chatId'])], limit=1)
                    if whatsapp_contact_obj:
                        msg_dict = {'whatsapp_contact_id': whatsapp_contact_obj.id}

                    _logger.info("In whatsapp integration marketing msg_dict %s: ", str(msg_dict))
                    if len(msg_dict) > 0:
                        whatapp_msg_id = whatapp_msg.sudo().search([('message_id', '=', msg['id'])])
                        if whatapp_msg_id:
                            whatapp_msg_id.sudo().write(msg_dict)
        return 'OK'

    def send_notification_to_admin(self, partner, msg):
        mail_channel_obj = request.env['mail.channel']
        whatsapp_chat_ids = request.env.ref('pragmatic_odoo_whatsapp_integration.group_whatsapp_chat')
        whatsapp_chat_users_ids = whatsapp_chat_ids.sudo().users
        whatsapp_partner_ids = whatsapp_chat_users_ids.mapped('partner_id')
        if partner:
            channel_exist = mail_channel_obj.sudo().search([('channel_partner_ids', '=', partner.id)], limit=1)
            if channel_exist:
                if msg.get('type') == 'chat':
                    channel_exist.with_context(from_odoobot=True).message_post(body=msg['body'],
                                                                               message_type="notification",
                                                                               subtype_xmlid="mail.mt_comment",
                                                                               author_id=partner.id)
                else:
                    data_base64 = base64.b64encode(requests.get(msg.get('body').strip()).content)
                    attachment_dict = {
                        'datas': data_base64,
                        'type': 'binary',
                        'res_model': 'mail.compose.message',
                        'res_id': channel_exist.id
                    }
                    if msg.get('caption'):
                        attachment_dict['name'] = msg.get('caption')
                    else:
                        attachment_dict['name'] = msg.get('body')
                    attachment_id = request.env['ir.attachment'].sudo().create(attachment_dict)
                    _logger.info("Attachment is created in odoo when updating mail channel attachment id %s: ", str(attachment_id))
                    if msg.get('caption'):
                        message_update = channel_exist.with_context(from_odoobot=True).message_post(body=msg.get('caption'), attachment_ids=[attachment_id.id],
                                                                                                    message_type="notification",
                                                                                                    subtype_xmlid="mail.mt_comment",
                                                                                                    author_id=partner.id)
                    else:
                        message_update = channel_exist.with_context(from_odoobot=True).message_post(attachment_ids=[attachment_id.id],
                                                                                                    message_type="notification",
                                                                                                    subtype_xmlid="mail.mt_comment",
                                                                                                    author_id=partner.id)

            else:
                image_path = modules.get_module_resource('pragmatic_odoo_whatsapp_integration', 'static/img',
                                                         'whatsapp_logo.png')
                image = base64.b64encode(open(image_path, 'rb').read())
                partner_list = []
                for whatsapp_chat_partner_id in whatsapp_partner_ids:
                    partner_list.append(whatsapp_chat_partner_id.id)
                partner_list.append(partner.id)
                if len(partner_list) > 0:
                    channel_dict = {
                        'name': 'Chat with {}'.format(partner.name),
                        'channel_partner_ids': [(6, 0, partner_id) for partner_id in partner_list],
                        # 'public': 'private',
                        'image_128': image,
                    }
                    channel = mail_channel_obj.sudo().create(channel_dict)
                    if msg.get('type') == 'chat':
                        channel.with_context(from_odoobot=True).message_post(body=msg['body'],
                                                                             message_type="notification",
                                                                             subtype_xmlid="mail.mt_comment",
                                                                             author_id=partner.id)
                    else:
                        data_base64 = base64.b64encode(requests.get(msg.get('body').strip()).content)
                        attachment_dict = {
                            'datas': data_base64,
                            'type': 'binary',
                            'res_model': 'mail.compose.message',
                            'res_id': channel.id
                        }
                        if msg.get('caption'):
                            attachment_dict['name'] = msg.get('caption')
                        else:
                            attachment_dict['name'] = msg.get('body')

                        attachment_id = request.env['ir.attachment'].sudo().create(attachment_dict)
                        channel.with_context(from_odoobot=True).message_post(attachment_ids=[attachment_id.id],
                                                                             message_type="notification",
                                                                             subtype_xmlid="mail.mt_comment",
                                                                             author_id=partner.id)
                        _logger.info("Attachment is created in odoo when updating mail channel attachment id %s: ", str(attachment_id))

    def meta_send_notification_to_admin(self, partner, msg):
        mail_channel_obj = request.env['mail.channel']
        whatsapp_chat_ids = request.env.ref('pragmatic_odoo_whatsapp_integration.group_whatsapp_chat')
        whatsapp_chat_users_ids = whatsapp_chat_ids.sudo().users
        whatsapp_partner_ids = whatsapp_chat_users_ids.mapped('partner_id')
        if partner:
            channel_exist = mail_channel_obj.sudo().search([('channel_partner_ids', '=', partner.id)], limit=1)
            if channel_exist:
                if msg.get('type') == 'text':
                    channel_exist.with_context(from_odoobot=True).message_post(body=msg.get('text').get('body'),
                                                                               message_type="notification",
                                                                               subtype_xmlid="mail.mt_comment",
                                                                               author_id=partner.id)
                # else:
                #     data_base64 = base64.b64encode(requests.get(msg.get('body').strip()).content)
                #     attachment_dict = {
                #         'datas': data_base64,
                #         'type': 'binary',
                #         'res_model': 'mail.compose.message',
                #         'res_id': channel_exist.id
                #     }
                #     if msg.get('caption'):
                #         attachment_dict['name'] = msg.get('caption')
                #     else:
                #         attachment_dict['name'] = msg.get('body')
                #     attachment_id = request.env['ir.attachment'].sudo().create(attachment_dict)
                #     _logger.info("Attachment is created in odoo when updating mail channel attachment id %s: ", str(attachment_id))
                #     if msg.get('caption'):
                #         message_update = channel_exist.with_context(from_odoobot=True).message_post(body=msg.get('caption'), attachment_ids=[attachment_id.id],
                #                                                                                     message_type="notification",
                #                                                                                     subtype_xmlid="mail.mt_comment",
                #                                                                                     author_id=partner.id)
                #     else:
                #         message_update = channel_exist.with_context(from_odoobot=True).message_post(attachment_ids=[attachment_id.id],
                #                                                                                     message_type="notification",
                #                                                                                     subtype_xmlid="mail.mt_comment",
                #                                                                                     author_id=partner.id)

            else:
                image_path = modules.get_module_resource('pragmatic_odoo_whatsapp_integration', 'static/img',
                                                         'whatsapp_logo.png')
                image = base64.b64encode(open(image_path, 'rb').read())
                partner_list = []
                for whatsapp_chat_partner_id in whatsapp_partner_ids:
                    partner_list.append(whatsapp_chat_partner_id.id)
                partner_list.append(partner.id)
                if len(partner_list) > 0:
                    channel_dict = {
                        'name': 'Chat with {}'.format(partner.name),
                        'channel_partner_ids': [(6, 0, partner_id) for partner_id in partner_list],
                        'image_128': image,
                    }
                    channel = mail_channel_obj.sudo().create(channel_dict)
                    if msg.get('type') == 'text':
                        channel.with_context(from_odoobot=True).message_post(body=msg.get('text').get('body'),
                                                                             message_type="notification",
                                                                             subtype_xmlid="mail.mt_comment",
                                                                             author_id=partner.id)
                    # else:
                    #     data_base64 = base64.b64encode(requests.get(msg.get('body').strip()).content)
                    #     attachment_dict = {
                    #         'datas': data_base64,
                    #         'type': 'binary',
                    #         'res_model': 'mail.compose.message',
                    #         'res_id': channel.id
                    #     }
                    #     if msg.get('caption'):
                    #         attachment_dict['name'] = msg.get('caption')
                    #     else:
                    #         attachment_dict['name'] = msg.get('body')

                    #     attachment_id = request.env['ir.attachment'].sudo().create(attachment_dict)
                    #     channel.with_context(from_odoobot=True).message_post(attachment_ids=[attachment_id.id],
                    #                                                          message_type="notification",
                    #                                                          subtype_xmlid="mail.mt_comment",
                    #                                                          author_id=partner.id)
                    #     _logger.info("Attachment is created in odoo when updating mail channel attachment id %s: ", str(attachment_id))


    def gupshup_convert_epoch_to_unix_timestamp(self, msg_time):
        your_dt = datetime.datetime.fromtimestamp(int(msg_time) / 1000)
        return your_dt


    @http.route('/whatsapp_meta/response/message',type='http',auth='public',methods=['GET', 'POST'], website=True,csrf=False)
    def meta_whatsapp_response_ne(self):
        if request.httprequest.method == 'GET':
            _logger.info("In whatsapp integration controller verification")
            whatsapp_instance_id = request.env['whatsapp.instance'].get_whatsapp_instance()
            verify_token = whatsapp_instance_id.whatsapp_meta_webhook_token

            VERIFY_TOKEN = verify_token

            if 'hub.mode' in request.httprequest.args:
                mode = request.httprequest.args.get('hub.mode')
            if 'hub.verify_token' in request.httprequest.args:
                token = request.httprequest.args.get('hub.verify_token')

            if 'hub.challenge' in request.httprequest.args:
                challenge = request.httprequest.args.get('hub.challenge')

            if 'hub.mode' in request.httprequest.args and 'hub.verify_token' in request.httprequest.args:
                mode = request.httprequest.args.get('hub.mode')
                token = request.httprequest.args.get('hub.verify_token')

                if mode == 'subscribe' and token == VERIFY_TOKEN:

                    challenge = request.httprequest.args.get('hub.challenge')
                    return http.Response(challenge, status=200)

                    # return challenge, 200
                else:
                    return http.Response('ERROR', status=403)

            return 'SOMETHING', 200
        super(WhatsappIntegration, self).meta_whatsapp_response_ne()
        if request.httprequest.method == 'POST':
            data = json.loads(request.httprequest.data)
            _logger.info("data %s: ", str(data))
            if data.get('entry')[0].get('changes')[0].get('value').get('messages'):
                msg_list = []
                msg_dict = {}
                res_partner_obj = request.env['res.partner']
                whatapp_msg = request.env['whatsapp.messages']
                mail_channel_obj = request.env['mail.channel']
                mail_message_obj = request.env['mail.message']
                project_task_obj = request.env['project.task']

                for msg in data.get('entry')[0].get('changes')[0].get('value').get('messages'):
                    if msg.get('context'):
                        project_task_id = project_task_obj.sudo().search([('whatsapp_msg_id', '=', msg.get('id'))])
                        # chat_id = msg['chatId']
                        # chatid_split = chat_id.split('@')
                        mobile = '+' + msg.get('from')
                        mobile_coutry_code = phonenumbers.parse(mobile, None)
                        mobile_number = mobile_coutry_code.national_number
                        country_code = mobile_coutry_code.country_code
                        res_country_id = request.env['res.country'].sudo().search([('phone_code', '=', country_code)], limit=1)
                        reg_sanitized_number = phone_validation.phone_format(str(mobile_number), res_country_id.code, country_code)
                        res_partner_obj = res_partner_obj.sudo().search([('mobile', '=', mobile)], limit=1)
                        mail_message_id = mail_message_obj.sudo().search([('whatsapp_message_id', '=', msg.get('context').get('id'))], limit=1)
                        if mail_message_id.model == 'mail.channel' and mail_message_id.res_id:
                            channel_id = mail_channel_obj.sudo().search([('id', '=', mail_message_id.res_id)])
                            body = msg.get('text').get('body') if msg.get('text') else False
                            channel_id.with_context(from_odoobot=True).message_post(body=body, message_type="notification",
                                                                                    subtype_xmlid="mail.mt_comment", author_id=res_partner_obj.id)
                            mail_message_id.with_context(from_odoobot=True)
                        if project_task_id:
                            if msg.get('body') == 'done' or msg.get('body') == 'Done':
                                project_task_update_record = project_task_id.write({'whatsapp_done_stage': True})

                    else:
                        res_partner_id = res_partner_obj.sudo().search([('chatId', '=', msg.get('from'))], limit=1)

                        if res_partner_id:
                            self.meta_send_notification_to_admin(res_partner_id, msg)

                        _logger.info("msg_dict %s: ", str(msg_dict))
                        if len(msg_dict) > 0:
                            msg_list.append(msg_dict)
                # for msg in msg_list:
                #     whatapp_msg_id = whatapp_msg.sudo().search([('message_id', '=', msg.get('message_id'))])
                #     if whatapp_msg_id:
                #         whatapp_msg_id.sudo().write(msg)
                #         _logger.info("whatapp_msg_id %s: ", str(whatapp_msg_id))
                #         if 'messages' in data and data['messages']:
                #             for msg in data['messages']:
                #                 if whatapp_msg_id and msg['type'] == 'document':
                #                     msg_attchment_dict = {}
                #                     url = msg['body']
                #                     data_base64 = base64.b64encode(requests.get(url.strip()).content)
                #                     msg_attchment_dict = {'datas': data_base64, 'type': 'binary',
                #                                           'res_model': 'whatsapp.messages', 'res_id': whatapp_msg_id.id}
                #                     if msg.get('caption'):
                #                         msg_attchment_dict['name'] = msg.get('caption')
                #                     elif msg.get('name'):
                #                         msg_attchment_dict['name'] = msg.get('name')
                #                     elif msg.get('body'):
                #                         msg_attchment_dict['name'] = msg.get('body')
                #                     attachment_id = request.env['ir.attachment'].sudo().create(msg_attchment_dict)
                #                     res_update_whatsapp_msg = whatapp_msg_id.sudo().write({'attachment_id': attachment_id.id})
                #                     if res_update_whatsapp_msg:
                #                         _logger.info("whatapp_msg_id %s: ", str(whatapp_msg_id.id))
                #     else:
                #         res_whatsapp_msg = whatapp_msg.sudo().create(msg)
                #         _logger.info("res_whatsapp_msg2111 %s: ", str(res_whatsapp_msg))
                #         if 'messages' in data and data['messages']:
                #             for msg in data['messages']:
                #                 if res_whatsapp_msg and msg['type'] == 'document':
                #                     msg_attchment_dict = {}
                #                     url = msg['body']
                #                     data_base64 = base64.b64encode(requests.get(url.strip()).content)
                #                     msg_attchment_dict = {'type': 'binary',
                #                                           'res_model': 'whatsapp.messages', 'res_id': res_whatsapp_msg.id}
                #                     if msg.get('caption'):
                #                         msg_attchment_dict['name'] = msg.get('caption')
                #                     elif msg.get('name'):
                #                         msg_attchment_dict['name'] = msg.get('name')
                #                     elif msg.get('body'):
                #                         msg_attchment_dict['name'] = msg.get('body')
                #                     if data_base64:
                #                         msg_attchment_dict['datas'] = data_base64
                #                     attachment_id = request.env['ir.attachment'].sudo().create(msg_attchment_dict)
                #                     res_update_whatsapp_msg = res_whatsapp_msg.sudo().write({'attachment_id': attachment_id.id})
                #                     if res_update_whatsapp_msg:
                #                         _logger.info("res_whatsapp_msg %s: ", str(res_whatsapp_msg.id))