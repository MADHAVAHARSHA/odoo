from odoo import api, models, fields
from odoo.exceptions import UserError
import requests
from requests.auth import HTTPBasicAuth
import logging
import json
from functools import wraps
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)
TIMEOUT = 1000

class PosEmvCache(models.Model):
    _name = 'pos.emv.cache'
    _description = 'Temporary EMV Response Cache'

    uuid = fields.Char(string='UUID', required=True, index=True)
    response = fields.Text(string='EMV Response', required=True)  # Store as JSON string
    timestamp = fields.Datetime(string='Timestamp', default=fields.Datetime.now, required=True)
    payment_id = fields.Many2one('pos.payment', string='Payment', ondelete='cascade')

    @api.model
    def cleanup_expired(self):
        """Remove expired cache entries (older than 5 minutes)."""
        expiration_time = fields.Datetime.now() - timedelta(minutes=5)
        self.search([('timestamp', '<', expiration_time)]).unlink()
        _logger.debug("Cleaned up expired EMV cache entries")