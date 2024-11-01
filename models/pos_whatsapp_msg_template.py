# -*- coding: utf-8 -*-

from odoo import fields, models


class WhatsappMsgTemplate(models.Model):
    _name = "whatsapp.message.template"
    _description = "Whatsapp message template"

    name = fields.Char(String="Name", required=1)
    message = fields.Text(String="Message", required=1)
