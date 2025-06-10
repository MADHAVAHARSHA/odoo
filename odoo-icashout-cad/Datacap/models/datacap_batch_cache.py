from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta

class DatacapBatchCache(models.Model):
    _name = "datacap.batch.cache"
    _description = "Datacap Batch Summary Cache"

    payment_method_id = fields.Many2one("pos.payment.method", required=True, ondelete="cascade")
    batch_no = fields.Char(required=True)
    batch_item_count = fields.Integer(required=True)
    net_batch_total = fields.Float(required=True)
    expire_at = fields.Datetime(required=True, index=True)

    @api.model
    def set_cache(self, payment_method_id, batch_data):
        self.search([('payment_method_id', '=', payment_method_id)]).unlink()
        self.create({
            'payment_method_id': payment_method_id,
            'batch_no': batch_data['BatchNo'],
            'batch_item_count': batch_data['BatchItemCount'],
            'net_batch_total': batch_data['NetBatchTotal'],
            'expire_at': fields.Datetime.now() + timedelta(minutes=5),
        })

    @api.model
    def get_valid_cache(self, payment_method_id):
        now = fields.Datetime.now()
        return self.search([
            ('payment_method_id', '=', payment_method_id),
            ('expire_at', '>', now)
        ], limit=1)
