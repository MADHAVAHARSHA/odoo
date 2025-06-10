from odoo import api, models, fields
import logging
import json
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def sync_from_ui(self, orders):
        """Override sync_from_ui to update pos.payment with cached EMV response before saving the order."""
        start_time = datetime.now()
        _logger.debug("Starting sync_from_ui with orders: %s", json.dumps(orders, indent=4))
        print(f"Starting sync_from_ui with orders: {json.dumps(orders, indent=4)}")

        # Step 1: Process each order and apply EMV responses before syncing
        for order in orders:
            ui_order = order  # No 'data' key, use the order directly
            payments = ui_order.get('payment_ids', [])
            if not payments:
                _logger.debug("No payments for order %s", ui_order.get('uuid'))
                print(f"No payments for order {ui_order.get('uuid')}")
                continue

            for payment in payments:
                if isinstance(payment, (list, tuple)) and len(payment) == 3 and payment[0] == 0:
                    payment_data = payment[2]  # Get the payment values
                else:
                    continue

                payment_method_id = payment_data.get('payment_method_id')
                if not payment_method_id:
                    _logger.warning("Payment method ID not found for payment in order %s", ui_order.get('uuid'))
                    print(f"Payment method ID not found for payment in order {ui_order.get('uuid')}")
                    continue

                # Check if the payment method uses Datacap terminal
                payment_method = self.env['pos.payment.method'].browse(payment_method_id)
                if payment_method.use_payment_terminal != 'datacap':
                    continue

                uuid = payment_data.get('uuid')
                if not uuid:
                    _logger.warning("UUID not found for payment in order %s", ui_order.get('uuid'))
                    print(f"UUID not found for payment in order {ui_order.get('uuid')}")
                    continue

                # Wait for EMV response to be available in pos.emv.cache
                max_attempts = 10
                delay_ms = 100
                attempt = 0
                emv_response = False

                fetch_start = datetime.now()
                while attempt < max_attempts:
                    attempt += 1
                    emv_response = self.env['pos.emv.cache'].search([('uuid', '=', uuid)], limit=1)
                    if emv_response:
                        break
                    _logger.debug("EMV response not found for UUID %s (attempt %s/%s). Retrying after %sms...",
                                  uuid, attempt, max_attempts, delay_ms)
                    print(
                        f"EMV response not found for UUID {uuid} (attempt {attempt}/{max_attempts}). Retrying after {delay_ms}ms...")
                    self.env.cr.commit()  # Commit to ensure we see updates from other threads
                    self.env.clear()  # Clear the environment to avoid stale data
                    if emv_response:  # Call _invalidate_cache on the recordset if it exists
                        emv_response._invalidate_cache()
                    import time
                    time.sleep(delay_ms / 1000.0)  # Sleep for the delay in seconds

                if not emv_response:
                    _logger.warning("No EMV response found in pos.emv.cache for UUID %s after %s attempts", uuid,
                                    max_attempts)
                    print(f"No EMV response found in pos.emv.cache for UUID {uuid} after {max_attempts} attempts")
                    continue

                _logger.debug("Retrieved emv_response from pos.emv.cache for UUID %s: %s. Time: %s",
                              uuid, json.dumps(emv_response.response, indent=4), datetime.now() - fetch_start)
                print(
                    f"Retrieved emv_response from pos.emv.cache for UUID {uuid}: {json.dumps(emv_response.response, indent=4)}. Time: {datetime.now() - fetch_start}")

                # Check if the response has expired
                if (fields.Datetime.from_string(emv_response.timestamp) + timedelta(minutes=5)) < fields.Datetime.now():
                    _logger.warning("Cached EMV response for UUID %s expired", uuid)
                    print(f"Cached EMV response for UUID {uuid} expired")
                    emv_response.unlink()
                    continue

                # Apply the EMV response to the payment record
                rstream = json.loads(emv_response.response).get('RStream', {})
                if rstream.get("CmdStatus") != "Approved":
                    _logger.warning("EMV response not approved for UUID %s: %s", uuid,
                                    rstream.get("TextResponse", "Unknown"))
                    print(f"EMV response not approved for UUID {uuid}: {rstream.get('TextResponse', 'Unknown')}")
                    emv_response.unlink()
                    continue

                update_vals = {
                    'payment_ref_no': rstream.get("RefNo", ""),
                    'payment_method_authcode': rstream.get("AuthCode", ""),
                    'card_type': rstream.get("CardType", ""),
                    'card_no': rstream.get("AcctNo", "****")[-4:],
                    'name': rstream.get("ApplicationLabel", ""),
                    'ticket': rstream.get("InvoiceNo", ""),
                    'payment_status': "Approved",
                    'entry_method': rstream.get("EntryMethod", ""),
                    'aid': rstream.get("AID", ""),
                    'tvr': rstream.get("TVR", ""),
                    'iad': rstream.get("IAD", ""),
                    'tsi': rstream.get("TSI", ""),
                    'cvm': rstream.get("CVM", ""),
                    'acq_ref_data': rstream.get("AcqRefData", ""),
                    'process_data': rstream.get("ProcessData", ""),
                    'record_no': rstream.get("RecordNo", ""),
                    'payapi_id': rstream.get("PayAPI_Id", ""),
                    'capture_status': rstream.get("CaptureStatus", ""),
                    'authorized_amount': float(rstream.get("Authorize", 0.0)),
                    'purchase_amount': float(rstream.get("Purchase", 0.0)),
                    'text_response': rstream.get("TextResponse", ""),
                    'receipt_lines': "\n".join([rstream.get(f"Line{i}", "") for i in range(1, 23)]),
                }

                # Update the payment record directly (for new payments, this will be created by super())
                payment_data.update(update_vals)
                _logger.debug("Applied EMV response to payment in order %s: %s", ui_order.get('uuid'),
                              json.dumps(update_vals, indent=4))
                print(
                    f"Applied EMV response to payment in order {ui_order.get('uuid')}: {json.dumps(update_vals, indent=4)}")

                # Delete the cache entry
                emv_response.unlink()
                _logger.debug("Removed EMV response from pos.emv.cache for UUID %s", uuid)
                print(f"Removed EMV response from pos.emv.cache for UUID {uuid}")

        # Step 2: Call super().sync_from_ui() with the updated orders
        sync_start = datetime.now()
        result = super(PosOrder, self).sync_from_ui(orders)
        _logger.debug("Result from super().sync_from_ui: %s. Time: %s", json.dumps(result, indent=4, default=str),
                      datetime.now() - sync_start)
        print(
            f"Result from super().sync_from_ui: {json.dumps(result, indent=4, default=str)}. Time: {datetime.now() - sync_start}")

        # Step 3: Cleanup expired entries
        cleanup_start = datetime.now()
        self.env['pos.emv.cache'].cleanup_expired()
        _logger.debug("Cleanup expired pos.emv.cache entries completed. Time: %s", datetime.now() - cleanup_start)
        print(f"Cleanup expired pos.emv.cache entries completed. Time: {datetime.now() - cleanup_start}")

        _logger.debug("sync_from_ui completed. Total time: %s", datetime.now() - start_time)
        print(f"sync_from_ui completed. Total time: {datetime.now() - start_time}")
        return result

    def _apply_emv_response_to_payment(self, payment, rstream):
        """Apply the EMV response data to the pos.payment record."""
        _logger.debug("Applying EMV response to payment ID: %s with RStream: %s", payment.id, json.dumps(rstream, indent=4))
        print(f"Applying EMV response to payment ID {payment.id} with RStream: {json.dumps(rstream, indent=4)}")

        update_vals = {
            'payment_ref_no': rstream.get("RefNo", ""),
            'payment_method_authcode': rstream.get("AuthCode", ""),
            'card_type': rstream.get("CardType", ""),
            'card_no': rstream.get("AcctNo", "****")[-4:],
            'name': rstream.get("ApplicationLabel", ""),
            'ticket': rstream.get("InvoiceNo", ""),
            'payment_status': "Approved",
            'entry_method': rstream.get("EntryMethod", ""),
            'aid': rstream.get("AID", ""),
            'tvr': rstream.get("TVR", ""),
            'iad': rstream.get("IAD", ""),
            'tsi': rstream.get("TSI", ""),
            'cvm': rstream.get("CVM", ""),
            'acq_ref_data': rstream.get("AcqRefData", ""),
            'process_data': rstream.get("ProcessData", ""),
            'record_no': rstream.get("RecordNo", ""),
            'payapi_id': rstream.get("PayAPI_Id", ""),
            'capture_status': rstream.get("CaptureStatus", ""),
            'authorized_amount': float(rstream.get("Authorize", 0.0)),
            'purchase_amount': float(rstream.get("Purchase", 0.0)),
            'text_response': rstream.get("TextResponse", ""),
            'receipt_lines': "\n".join([rstream.get(f"Line{i}", "") for i in range(1, 23)]),
        }

        _logger.debug("Update values for payment ID %s: %s", payment.id, json.dumps(update_vals, indent=4))
        print(f"Update values for payment ID {payment.id}: {json.dumps(update_vals, indent=4)}")
        payment.write(update_vals)
        _logger.info(f"POS Payment {payment.id} updated with EMV response data: {json.dumps(update_vals, indent=4)}")
        print(f"POS Payment {payment.id} updated with EMV response data: {json.dumps(update_vals, indent=4)}")