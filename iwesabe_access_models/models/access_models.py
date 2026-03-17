# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class AccessModels(models.Model):
    _name = 'access.model'
    _description = 'Access Model'
    
    ir_model_id = fields.Many2one('ir.model', 'Model')
    user_id = fields.Many2one('res.users')
    remove_create = fields.Boolean('Remove Create')
    remove_edit = fields.Boolean('Remove Edit')
    remove_delete = fields.Boolean('Remove Delete')
