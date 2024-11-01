import uuid
from werkzeug.urls import url_encode, url_join
from odoo import api, fields, models, _


class Attachment(models.Model):
    _inherit = "ir.attachment"

    access_token = fields.Char('Token', readonly=True)
    public_url = fields.Char('Public URL', readonly=True)

    @api.model
    def create(self, vals):
        res = super(Attachment, self).create(vals)
        res.access_token = uuid.uuid4()
        config_obj = self.env['ir.config_parameter'].get_param('web.base.url')
        att_link = url_join(config_obj, f'/whatsapp_attachment/{res.access_token}/get_attachment')
        res.write({'public_url': att_link})
        return res
