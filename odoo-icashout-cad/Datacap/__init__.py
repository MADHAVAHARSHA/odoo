from . import models

from odoo import SUPERUSER_ID, api

def create_manual_entry_method_if_missing(env):
    """Post-init hook: Create 'Manual Entry' payment method if it doesn't exist."""
    method_name = "Manual Entry"

    existing = env['pos.payment.method'].search([('name', '=', method_name)], limit=1)
    if existing:
        return  # Already exists

    journal = env['account.journal'].search([('type', '=', 'bank')], limit=1)
    if not journal:
        raise Exception("No bank journal found. Please create a bank journal.")

    env['pos.payment.method'].create({
        'name': method_name,
        'type': 'bank',
        'journal_id': journal.id,
        'payment_method_type': 'terminal',
        'use_payment_terminal': 'datacap',
    })


def uninstall_remove_manual_entry(cr, registry):
    """Uninstall hook: Remove 'Manual Entry' payment method on module uninstall."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['pos.payment.method'].search([('name', '=', 'Manual Entry')]).unlink()
