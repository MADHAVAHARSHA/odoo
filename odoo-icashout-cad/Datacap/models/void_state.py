from odoo import api, models, fields
from odoo.exceptions import UserError
import requests
from requests.auth import HTTPBasicAuth
import logging
import json
from datetime import datetime, timedelta

class PosOrder(models.Model):
    _inherit = 'pos.order'

    state = fields.Selection(
        selection_add=[('Voided', 'Voided'),('refunded', 'Refunded')],
        string='Status',
        ondelete={
            'voided': 'set default',
            'refunded': 'set default'  # Reset to 'draft' if 'refunded' is removed
        }
    )
