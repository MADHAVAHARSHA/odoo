from odoo import models, fields


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    payment_ref_no = fields.Char(string="Payment Reference No.")
    payment_method_authcode = fields.Char(string="Auth Code")
    card_type = fields.Char(string="Card Type")
    card_no = fields.Char(string="Masked Card Number")
    name = fields.Char(string="Application Label")
    ticket = fields.Char(string="Invoice Number")
    payment_status = fields.Selection([
        ('Approved', 'Approved'),
        ('Declined', 'Declined'),
        ('Pending', 'Pending'),
        ('Error', 'Error'),
        ('done', 'Done'),
        ('failed', 'Failed'),
        ('Voided', 'Voided'),
        ('refunded', 'Refunded')
    ], string="Payment Status")

    entry_method = fields.Char(string="Entry Method")
    #transaction_date = fields.Date(string="Transaction Date")
    #transaction_time = fields.Char(string="Transaction Time")
    aid = fields.Char(string="AID")
    tvr = fields.Char(string="TVR")
    iad = fields.Char(string="IAD")
    tsi = fields.Char(string="TSI")
    cvm = fields.Char(string="CVM")
    acq_ref_data = fields.Text(string="Acquirer Reference Data")
    process_data = fields.Text(string="Process Data")
    record_no = fields.Text(string="Record Number")
    payapi_id = fields.Char(string="PayAPI ID")
    capture_status = fields.Char(string="Capture Status")
    authorized_amount = fields.Float(string="Authorized Amount")
    purchase_amount = fields.Float(string="Purchase Amount")
    text_response = fields.Text(string="Text Response")

    # New Field to Store Receipt Lines
    receipt_lines = fields.Text(string="Receipt Lines")
