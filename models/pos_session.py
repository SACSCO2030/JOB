from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pos_data_process(self, loaded_data):
        super()._pos_data_process(loaded_data)
        loaded_data['whatsapp_msg_templates_by_id'] = {whatsapp_message_template['id']: whatsapp_message_template for whatsapp_message_template in loaded_data['whatsapp.message.template']}

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        new_model = 'whatsapp.message.template'
        if new_model not in result:
            result.append(new_model)
        return result

    def _loader_params_whatsapp_message_template(self):
        return {'search_params': {'domain': '', 'fields': ['name', 'id', 'message'], 'load': False}}

    def _get_pos_ui_whatsapp_message_template(self, params):
        whatsapp_message_templates = self.env['whatsapp.message.template'].search_read(**params['search_params'])
        whatsapp_message_template_ids = [whatsapp_message_template['id'] for whatsapp_message_template in whatsapp_message_templates]

        return whatsapp_message_templates