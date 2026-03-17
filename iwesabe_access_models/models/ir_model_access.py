# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _

class IrModelAccess(models.Model):
	_inherit = 'ir.model.access'

	@api.model
	@tools.ormcache_context('self._uid', 'model', 'mode', 'raise_exception', keys=('lang',))
	def check(self, model, mode='read', raise_exception=True):
		result = super(IrModelAccess, self).check(model, mode, raise_exception=raise_exception)
		# ('read', 'write', 'create', 'unlink')
		if model == 'access.model':
			return result
		if self.env.user:
			if not self.env.context.get('iwesabe_access_models'):
				model_id = self.env['ir.model'].sudo().with_context(iwesabe_access_models=True).search([('model','=','access.model')])
				if model_id.exists():
					access_model_ids = self.env['access.model'].sudo().with_context(iwesabe_access_models=True).search([('user_id','=',self.env.user.id)])
					if access_model_ids and model:
						models = access_model_ids.mapped('ir_model_id.model')
						if model in models:
							access_model_id = access_model_ids.filtered(lambda x:x.ir_model_id.model == model)
							if access_model_id:
								if access_model_id.remove_create:
									if mode == 'create':
										return False
								if access_model_id.remove_edit:
									if mode == 'write':
										return False
								if access_model_id.remove_delete:
									if mode == 'unlink':
										return False
		return result