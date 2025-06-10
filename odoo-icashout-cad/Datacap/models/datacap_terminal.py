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

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    datacap_base_url = fields.Char(string="API URL", default="https://cloud-test.dcap.com", help="The base URL for Datacap's API.",store = True)
    datacap_merchant_id = fields.Char(string="Merchant ID", help="The Merchant ID used to identify the merchant account with Datacap.",store = True)
    datacap_operator_id = fields.Char(string="Operator ID", help="The Operator ID used to authenticate Datacap transactions.",store = True)
    datacap_device_id = fields.Char(string="Device ID", help="The EMV-capable Device ID assigned by Datacap.",store = True)
    datacap_username = fields.Char(string="Username", help="The username used for Datacap authentication.",store = True)
    datacap_password = fields.Char(string="Password", groups='base.group_system', help="The password used for Datacap authentication.",store = True)


    def _get_payment_terminal_selection(self):
        # Add 'datacap' to the terminal selection options
        return super()._get_payment_terminal_selection() + [('datacap', 'Datacap')]

    #Download EMV_Parameters
    def download_emv_params(self):
        """Download EMV parameters from Datacap."""
        self.ensure_one()

        # Validate required fields
        if not self.datacap_merchant_id:
            raise UserError("Merchant ID is required for EMVParamDownload.")
        if not self.datacap_base_url:
            raise UserError("API URL is required for EMVParamDownload.")
        if not self.datacap_username or not self.datacap_password:
            raise UserError("Username and Password are required for Basic Authentication.")
        if not self.datacap_device_id:
            raise UserError("Device ID is required for EMVParamDownload.")

        # Construct payload with TStream root
        payload = {
            "TStream": {
                "Transaction": {
                    "MerchantID": self.datacap_merchant_id,
                    "POSPackageID": "OdooPOS:1.0",
                    "TranCode": "EMVParamDownload",
                    "SequenceNo": "0010010010",
                    "TranDeviceID": self.datacap_device_id,
                }
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            # Send the POST request with basic authentication
            response = requests.post(
                f"{self.datacap_base_url}/EMVParamDownload/",
                json=payload,
                headers=headers,
                auth=HTTPBasicAuth(self.datacap_username, self.datacap_password),
                timeout=TIMEOUT,
            )
            response.raise_for_status()

            # Parse the JSON response
            response_data = response.json()
            _logger.info("Datacap Full Response: %s", response_data)

            # Check if the response is successful
            if response_data.get("RStream", {}).get("CmdStatus") != "Success":
                error_message = response_data.get("RStream", {}).get("TextResponse", "Unknown error")
                raise UserError(f"Datacap Error: {error_message}")

            # Trigger a success popup message
            message = "Terminal connected successfully, and parameters downloaded."
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': message,
                    'sticky': False,
                    'type': 'success',
                }
            }

        except requests.exceptions.RequestException as e:
            _logger.error("Datacap communication error: %s", e)
            raise UserError("Failed to connect to Datacap. Please try again later.")

    # Batch Summary

    def batch_summary(self):
        """Download EMV parameters from Datacap."""
        self.ensure_one()

        # Validate required fields
        if not self.datacap_merchant_id:
            raise UserError("Merchant ID is required for BatchSummary.")
        if not self.datacap_base_url:
            raise UserError("API URL is required for BatchSummary.")
        if not self.datacap_username or not self.datacap_password:
            raise UserError("Username and Password are required for Basic Authentication.")
        if not self.datacap_device_id:
            raise UserError("Device ID is required for BatchSummary.")

        # Construct payload with TStream root
        payload = {
            "TStream": {
                "Admin": {
                    "MerchantID": self.datacap_merchant_id,
                    "POSPackageID": "OdooPOS:1.0",
                    "TranType": "Administrative",
                    "TranCode": "BatchSummary",
                    "SequenceNo": "0010010010",
                    "TranDeviceID": self.datacap_device_id,
                }
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            # Send the POST request with basic authentication
            response = requests.post(
                f"{self.datacap_base_url}/BatchSummary/",
                json=payload,
                headers=headers,
                auth=HTTPBasicAuth(self.datacap_username, self.datacap_password),
                timeout=TIMEOUT,
            )
            response.raise_for_status()

            # Parse the JSON response
            response_data = response.json()
            _logger.info("Datacap Full Response: %s", response_data)

            # Check if the response is successful
            if response_data.get("RStream", {}).get("CmdStatus") != "Success":
                error_message = response_data.get("RStream", {}).get("TextResponse", "Unknown error")
                raise UserError(f"Datacap Error: {error_message}")

            # Extract BatchSummary details from RStream
            rstream = response_data.get("RStream", {})
            batch_data = {
                "BatchNo": rstream.get("BatchNo"),
                "BatchItemCount": int(rstream.get("BatchItemCount", 0)),
                "NetBatchTotal": float(rstream.get("NetBatchTotal", 0.0)),
            }

            # Cache it for 5 minutes
            self.env['datacap.batch.cache'].set_cache(self.id, batch_data)

            # Trigger a success popup message
            message = (
                f"Batch Summary Successful!\n\n"
                f"Batch No: {batch_data['BatchNo']}\n"
                f"Item Count: {batch_data['BatchItemCount']}\n"
                f"Net Total: ${batch_data['NetBatchTotal']:.2f}\n"
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': message,
                    'sticky': False,
                    'type': 'success',
                }
            }

        except requests.exceptions.RequestException as e:
            _logger.error("Datacap communication error: %s", e)
            raise UserError("Failed to connect to Datacap. Please try again later.")


    def batch_close(self):
        """Closes the current batch using the Datacap terminal.

        Returns:
            dict: A success or error response for the batch close.

        Raises:
            UserError: If required credentials or BatchSummary data are missing, or the request fails.
        """
        self.ensure_one()

        # Validate required fields
        if not self.datacap_merchant_id:
            raise UserError(_("Merchant ID is required for BatchClose."))
        if not self.datacap_base_url:
            raise UserError(_("API URL is required for BatchClose."))
        if not self.datacap_username or not self.datacap_password:
            raise UserError(_("Username and Password are required for Basic Authentication."))
        if not self.datacap_device_id:
            raise UserError(_("Device ID is required for BatchClose."))

        # Perform BatchSummary to get required data
        batch_summary_response = self.batch_summary()
        if batch_summary_response.get('type') != 'ir.actions.client' or batch_summary_response.get('params', {}).get(
                'type') != 'success':
            raise UserError(_("Failed to retrieve BatchSummary data. BatchClose cannot proceed."))

        # Extract BatchSummary data from stored response
        batch_summary_data = self._get_batch_summary_data()
        if not batch_summary_data or not all(
                key in batch_summary_data for key in ['BatchNo', 'BatchItemCount', 'NetBatchTotal']):
            raise UserError(_("BatchSummary data is missing required fields: BatchNo, BatchItemCount, NetBatchTotal."))

        # Construct payload with TStream root
        payload = {
            "TStream": {
                "Admin": {
                    "MerchantID": self.datacap_merchant_id,
                    "POSPackageID": "OdooPOS:1.0",
                    "SecureDevice": "CloudEMV2",
                    "TranType": "Administrative",
                    "TranCode": "BatchClose",
                    "SequenceNo": batch_summary_data.get("SequenceNo", "0010010010"),
                    "TranDeviceID": self.datacap_device_id,
                    "BatchNo": batch_summary_data.get("BatchNo"),
                    "BatchItemCount": str(batch_summary_data.get("BatchItemCount")),
                    "NetBatchTotal": f"{float(batch_summary_data.get('NetBatchTotal')):.2f}",
                }
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            # Send the POST request with basic authentication
            _logger.info("Initiating BatchClose request: %s", json.dumps(payload, indent=4))
            print(f"Initiating BatchClose request: {json.dumps(payload, indent=4)}")

            response = requests.post(
                f"{self.datacap_base_url}/BatchClose/",
                json=payload,
                headers=headers,
                auth=HTTPBasicAuth(self.datacap_username, self.datacap_password),
                timeout=TIMEOUT,
            )
            response.raise_for_status()

            # Parse the JSON response
            response_data = response.json()
            _logger.info("Datacap BatchClose Response: %s", json.dumps(response_data, indent=4))
            print(f"Datacap BatchClose Response: {json.dumps(response_data, indent=4)}")

            # Check if the response is successful
            if response_data.get("RStream", {}).get("CmdStatus") == "Success":
                # Trigger a success popup message
                message = f"Batch {batch_summary_data.get('BatchNo')} closed successfully."
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Success',
                        'message': message,
                        'sticky': False,
                        'type': 'success',
                    }
                }
            else:
                error_message = response_data.get("RStream", {}).get("TextResponse", "Unknown error")
                _logger.warning("BatchClose failed: %s", error_message)
                print(f"BatchClose failed: {error_message}")
                raise UserError(f"Datacap Error: {error_message}")

        except requests.exceptions.RequestException as e:
            _logger.error("Datacap communication error: %s", str(e))
            print(f"Datacap communication error: {str(e)}")
            raise UserError(_("Failed to connect to Datacap. Please try again later."))


    def _get_batch_summary_data(self):
        cache = self.env['datacap.batch.cache'].get_valid_cache(self.id)
        if not cache:
            return None
        return {
            "BatchNo": cache.batch_no,
            "BatchItemCount": cache.batch_item_count,
            "NetBatchTotal": cache.net_batch_total,
        }

    #Reset_EMV_Params
    def reset_emv_params(self):
        """Reset EMV parameters to default or clear fields."""
        self.ensure_one()

        # Clear or reset specific fields
        self.datacap_base_url = "https://cloud-test.dcap.com"
        self.datacap_merchant_id = False
        self.datacap_operator_id = False
        self.datacap_device_id = False
        self.datacap_username = False
        self.datacap_password = False

        # Log the reset action
        _logger.info("EMV parameters for %s have been reset.", self.name)

        # Display a notification to the user
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Parameters Reset',
                'message': 'EMV parameters have been reset to default.',
                'sticky': False,
                'type': 'info',
            }
        }

    def emv_pad_reset(self):
        self.ensure_one()

        if not self.datacap_merchant_id:
            raise UserError("Merchant ID is required for EMVSale.")
        if not self.datacap_base_url:
            raise UserError("API URL is required for EMVSale.")
        if not self.datacap_username or not self.datacap_password:
            raise UserError("Username and Password are required for Basic Authentication.")
        if not self.datacap_device_id:
            raise UserError("Device ID is required for EMVSale.")

            # Construct a simplified payload for EMVSale simulation
            payload = {
                "TStream": {
                    "Transaction": {
                        "MerchantID": self.datacap_merchant_id,
                        "POSPackageID": "OdooPOS:1.0",
                        "TranCode": "EMVPadReset",
                        "SequenceNo": "0010010010",  # Unique sequence number (update as necessary)
                        "TranDeviceID": self.datacap_device_id,
                    }
                }
            }

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            try:
                # Optionally send the POST request to Datacap (can be skipped if simulation)
                response = requests.post(
                    f"{self.datacap_base_url}/EMVPadReset/",
                    json=payload,
                    headers=headers,
                    auth=HTTPBasicAuth(self.datacap_username, self.datacap_password),
                    timeout=TIMEOUT,
                )
                response.raise_for_status()

                # Log and parse the response
                _logger.info("EMV Pad Reset Response: %s", response.text)

                if "<CmdStatus>Success</CmdStatus>" in response.text:
                    _logger.info("EMV Pad Reset successfully completed.")
                    # Trigger a success notification
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Success',
                            'message': 'EMV Pad reset successfully.',
                            'sticky': False,
                            'type': 'success',
                        }
                    }
                else:
                    # Parse error message from response
                    error_message = self._extract_error_message(response.text)
                    raise UserError(f"EMV Pad Reset Error: {error_message}")

            except requests.exceptions.RequestException as e:
                _logger.error("EMV Pad Reset communication error: %s", e)
                raise UserError("Failed to connect to Datacap. Please try again later.")

    # Process an EMVSale
    def process_manual_entry(self, amount, payment_id=None, uuid=None):
        """Process an EMV Sale transaction and store the response in the database."""
        self.ensure_one()
        _logger.debug("Starting process_emv_sale with amount: %s, payment_id: %s, uuid: %s", amount, payment_id,
                      uuid)
        print(f"Starting process_emv_sale with amount: {amount}, payment_id: {payment_id}, uuid: {uuid}")

        if not uuid:
            _logger.warning("No uuid provided; using payment method ID %s as fallback key", self.id)
            print(f"No uuid provided; using payment method ID {self.id} as fallback key")
            uuid = str(self.id)  # Fallback, though we expect UUID from frontend

        if not self.datacap_merchant_id:
            raise UserError("Merchant ID is required for EMVSale.")
        if not self.datacap_base_url:
            raise UserError("API URL is required for EMVSale.")
        if not self.datacap_username or not self.datacap_password:
            raise UserError("Username and Password are required for Basic Authentication.")
        if not self.datacap_device_id:
            raise UserError("Device ID is required for EMVSale.")

        payload = {
            "TStream": {
                "Transaction": {
                    "MerchantID": self.datacap_merchant_id,
                    "POSPackageID": "OdooPOS:1.0",
                    "TranCode": "EMVSale",
                    "SequenceNo": "0010010010",
                    "TranDeviceID": self.datacap_device_id,
                    "InvoiceNo": str(self.id),
                    # "PartialAuth": "Allow",
                    "RefNo": str(self.id),
                    "Account": {
                        "AcctNo": "Prompt"
                    },
                    "Amount": {"Purchase": amount},
                }
            }
        }
        _logger.debug("Constructed payload: %s", json.dumps(payload, indent=4))
        print(f"Constructed payload: {json.dumps(payload, indent=4)}")

        try:
            response = requests.post(
                f"{self.datacap_base_url}/EMVSale/",
                json=payload,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                auth=HTTPBasicAuth(self.datacap_username, self.datacap_password),
                timeout=2000,
            )
            response.raise_for_status()
            response_data = response.json()
            _logger.info("Datacap Response: %s", json.dumps(response_data, indent=4))
            print(f"Datacap Response: {json.dumps(response_data, indent=4)}")

            rstream = response_data.get("RStream", {})
            cmd_status = rstream.get("CmdStatus", "Unknown")

            if cmd_status == "Approved":
                self.env['pos.emv.cache'].create({
                    'uuid': uuid,
                    'response': json.dumps(response_data),
                    'timestamp': fields.Datetime.now(),
                })
                _logger.debug("Stored EMV response in pos.emv.cache for uuid %s", uuid)
                print(f"Stored EMV response in pos.emv.cache for uuid {uuid}")
            else:
                _logger.warning("Transaction not approved: %s", cmd_status)
                print(f"Transaction not approved: {cmd_status}")

            _logger.debug("Returning response from process_emv_sale: %s", json.dumps(response_data, indent=4))
            return response_data

        except requests.exceptions.RequestException as e:
            _logger.error(f"Datacap communication error: {e}")
            print(f"Datacap communication error: {e}")
            raise UserError("Failed to connect to Datacap. Please try again later.")

    #Process an EMVSale
    def process_emv_sale(self, amount, payment_id=None, uuid=None):
        """Process an EMV Sale transaction and store the response in the database."""
        self.ensure_one()
        _logger.debug("Starting process_emv_sale with amount: %s, payment_id: %s, uuid: %s", amount, payment_id, uuid)
        print(f"Starting process_emv_sale with amount: {amount}, payment_id: {payment_id}, uuid: {uuid}")

        if not uuid:
            _logger.warning("No uuid provided; using payment method ID %s as fallback key", self.id)
            print(f"No uuid provided; using payment method ID {self.id} as fallback key")
            uuid = str(self.id)  # Fallback, though we expect UUID from frontend

        if not self.datacap_merchant_id:
            raise UserError("Merchant ID is required for EMVSale.")
        if not self.datacap_base_url:
            raise UserError("API URL is required for EMVSale.")
        if not self.datacap_username or not self.datacap_password:
            raise UserError("Username and Password are required for Basic Authentication.")
        if not self.datacap_device_id:
            raise UserError("Device ID is required for EMVSale.")

        payload = {
            "TStream": {
                "Transaction": {
                    "MerchantID": self.datacap_merchant_id,
                    "POSPackageID": "OdooPOS:1.0",
                    "TranCode": "EMVSale",
                    "SequenceNo": "0010010010",
                    "TranDeviceID": self.datacap_device_id,
                    "InvoiceNo": str(self.id),
                    # "CardType": "Credit",
                    # "PartialAuth": "Allow",
                    "RefNo": str(self.id),
                    "Amount": {"Purchase": amount},
                }
            }
        }
        _logger.debug("Constructed payload: %s", json.dumps(payload, indent=4))
        print(f"Constructed payload: {json.dumps(payload, indent=4)}")

        try:
            response = requests.post(
                f"{self.datacap_base_url}/EMVSale/",
                json=payload,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                auth=HTTPBasicAuth(self.datacap_username, self.datacap_password),
                timeout=2000,
            )
            response.raise_for_status()
            response_data = response.json()
            _logger.info("Datacap Response: %s", json.dumps(response_data, indent=4))
            print(f"Datacap Response: {json.dumps(response_data, indent=4)}")

            rstream = response_data.get("RStream", {})
            cmd_status = rstream.get("CmdStatus", "Unknown")

            if cmd_status == "Approved":
                self.env['pos.emv.cache'].create({
                    'uuid': uuid,
                    'response': json.dumps(response_data),
                    'timestamp': fields.Datetime.now(),
                })
                _logger.debug("Stored EMV response in pos.emv.cache for uuid %s", uuid)
                print(f"Stored EMV response in pos.emv.cache for uuid {uuid}")
            else:
                _logger.warning("Transaction not approved: %s", cmd_status)
                print(f"Transaction not approved: {cmd_status}")

            _logger.debug("Returning response from process_emv_sale: %s", json.dumps(response_data, indent=4))
            return response_data

        except requests.exceptions.RequestException as e:
            _logger.error(f"Datacap communication error: {e}")
            print(f"Datacap communication error: {e}")
            raise UserError("Failed to connect to Datacap. Please try again later.")



    def process_refund(self, amount,uuid):
        """Processes a refund using the Datacap terminal.

        Args:
            amount (float): The refund amount.

        Returns:
            dict: A success or error response for the refund.

        Raises:
            UserError: If required credentials or parameters are missing or the request fails.
        """
        self.ensure_one()

        # Validate required fields
        if not self.datacap_merchant_id:
            raise UserError(_("Merchant ID is required for refunds."))
        if not self.datacap_base_url:
            raise UserError(_("API URL is required for refunds."))
        if not self.datacap_username or not self.datacap_password:
            raise UserError(_("Username and Password are required for basic authentication."))
        if not self.datacap_device_id:
            raise UserError(_("Device ID is required for refunds."))

        # Find a recent pos.payment record matching the amount and payment method
        payment_record = self.env['pos.payment'].search([
            ('payment_method_id', '=', self.id),
            ('amount', '=', amount),
            ('payment_status', 'in', ['done', 'pending','Approved']),  # Only non-refunded/voided payments
        ], order='id desc', limit=1)

        #print("payment records are printing ", payment_record)

        if not payment_record:
            _logger.warning("No payment record found for amount: %s and payment method: %s", amount, self.id)
            print(f"No payment record found for amount: {amount} and payment method: {self.id}")
            raise UserError("No eligible payment found for this amount and payment method.")

        _logger.debug("Payment Record: %s", payment_record.read())
        print(f"Payment Record: {payment_record.read()}")

        # Get the associated pos.order
        order = payment_record.pos_order_id

        if not order:
            _logger.error("No order associated with payment record: %s", payment_record.id)
            print(f"No order associated with payment record: {payment_record.id}")
            raise UserError("No order associated with this payment.")

        _logger.debug("Found pos.order: %s", order.read())
        print(f"Found pos.order: {order.read()}")

        # Construct refund payload
        payload = {
            "TStream": {
                "Transaction": {
                    "MerchantID": self.datacap_merchant_id,
                    "POSPackageID": "OdooPOS:1.0",
                    "TranCode": "EMVReturn",
                    "SequenceNo": "0010010010",
                    "TranDeviceID": self.datacap_device_id,
                    "InvoiceNo": str(payment_record.id),  # Use payment ID for uniqueness
                    "RefNo": str(payment_record.id),
                    "Amount": {
                        "Purchase": f"{amount:.2f}"
                    },
                    "ReturnClearExpDate": "Allow",
                    "Duplicate": "None",
                    "RecordNo": payment_record.record_no or "RecordNumberRequested",
                    "Frequency": "OneTime",
                    "CardHolderID": "Allow_V2",
                    "ForceOffline": "N",
                    "MaxTransactions": "0",
                    "OfflineTransactionPurchaseLimit": "0.00"
                }
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Make the refund API call
        try:
            _logger.info("Initiating refund request: %s", json.dumps(payload, indent=4))
            print(f"Initiating refund request: {json.dumps(payload, indent=4)}")

            response = requests.post(
                f"{self.datacap_base_url}/EMVReturn/",
                json=payload,
                headers=headers,
                auth=HTTPBasicAuth(self.datacap_username, self.datacap_password),
                timeout=TIMEOUT
            )
            response.raise_for_status()

            response_data = response.json()
            _logger.info("Datacap Response: %s", json.dumps(response_data, indent=4))
            print(f"Datacap Response: {json.dumps(response_data, indent=4)}")

            if response_data.get("RStream", {}).get("CmdStatus") == "Approved":
                # Update pos.payment.payment_status
                payment_record.write({'payment_status': 'refunded'})
                _logger.info("Payment %s marked as refunded", payment_record.id)

                # Store EMVReturn response in cache
                self.env['pos.emv.cache'].create({
                    'uuid': uuid or str(payment_record.id),
                    'response': json.dumps(response_data),
                    'timestamp': fields.Datetime.now(),
                })
                _logger.debug("Stored EMVReturn response in pos.emv.cache for uuid %s", uuid or str(payment_record.id))

                return {
                    "RStream": {
                        "CmdStatus": "Approved",
                        "TextResponse": "APPROVED",
                    }
                }

            else:
                error_message = response_data.get("RStream", {}).get("TextResponse", "Unknown error")
                _logger.warning("Refund failed: %s", error_message)
                print(f"Refund failed: {error_message}")
                raise UserError(f"Datacap Error: {error_message}")

        except requests.exceptions.RequestException as e:
            _logger.error("Refund communication error: %s", str(e))
            print(f"Refund communication error: {str(e)}")
            raise UserError(_("Failed to connect to Datacap. Please try again later."))

    def void_sale_by_record_number(self, order_uuid, amount):
        """Processes a void sale by record number using the Datacap terminal.

        Args:
            order_uuid (str): The UUID of the pos.order.
            amount (float): The amount to be voided.

        Returns:
            dict: A success or error response for the void sale.

        Raises:
            UserError: If required credentials, payment record, or request fails.
        """
        _logger.debug("Attempting to void sale with order UUID: %s and Amount: %s", order_uuid, amount)
        print(f"Attempting to void sale with order UUID: {order_uuid} and Amount: {amount}")

        # Step 1: Find the pos.order by its UUID
        order = self.env['pos.order'].search([('uuid', '=', order_uuid)], limit=1)
        if not order:
            _logger.warning("No pos.order found with UUID: %s", order_uuid)
            print(f"No pos.order found with UUID: {order_uuid}")
            raise UserError("No order found with the provided UUID.")

        _logger.debug("Found pos.order: %s", order.read())
        print(f"Found pos.order: {order.read()}")

        # Step 2: Find the associated pos.payment record via pos_order_id
        payment_record = self.env['pos.payment'].search([
            ('pos_order_id', '=', order.id),
            ('amount', '=', amount),
        ], limit=1)

        if not payment_record:
            _logger.warning("No payment record found for order UUID: %s with amount: %s", order_uuid, amount)
            print(f"No payment record found for order UUID: {order_uuid} with amount: {amount}")
            raise UserError("No payment record found for this order and amount.")

        _logger.debug("Payment Record: %s", payment_record.read())
        print(f"Payment Record: {payment_record.read()}")

        # Step 3: Get the payment method from the payment record
        payment_method = payment_record.payment_method_id
        if not payment_method:
            _logger.error("No payment method associated with payment record: %s", payment_record.id)
            print(f"No payment method associated with payment record: {payment_record.id}")
            raise UserError("No payment method associated with this payment.")

        # Extract necessary details
        merchant_id = payment_method.datacap_merchant_id
        base_url = payment_method.datacap_base_url or "https://cloud-test.dcap.com"
        username = payment_method.datacap_username
        password = payment_method.datacap_password
        tran_device_id = payment_method.datacap_device_id


        pos_package_id = "OdooPOS:1.0"
        tran_type = "Credit"
        tran_code = "VoidReturnByRecordNo"
        invoice_no = payment_record.ticket or payment_record.name
        ref_no = payment_record.payment_ref_no or str(payment_record.id)
        auth_code = payment_record.payment_method_authcode
        sequence_no = "0010010010"
        record_no = payment_record.record_no
        frequency = "OneTime"
        AcqRefData = payment_record.acq_ref_data
        ProcessData = payment_record.process_data

        # Validate required fields
        if not merchant_id:
            raise UserError("Payment method is missing the Merchant ID required for voiding.")
        if not base_url:
            raise UserError("Payment method is missing the API URL required for voiding.")
        if not tran_device_id:
            raise UserError("Payment method is missing the Device ID required for voiding.")
        if not username or not password:
            raise UserError("Payment method is missing the username or password required for authentication.")
        if not record_no:
            raise UserError("Payment record is missing the record number required for voiding.")
        if not auth_code:
            raise UserError("Payment record is missing the authorization code required for voiding.")

        # Construct the void sale request payload
        payload = {
            "TStream": {
                "Transaction": {
                    "MerchantID": merchant_id,
                    "POSPackageID": pos_package_id,
                    "TranType": tran_type,
                    "TranCode": tran_code,
                    "InvoiceNo": invoice_no,
                    "TranDeviceID": tran_device_id,
                    "RefNo": ref_no,
                    "AuthCode": auth_code,
                    "Amount": {
                        "Purchase": f"{abs(amount):.2f}"
                    },
                    "AcqRefData" : AcqRefData,
                    "ProcessData" :ProcessData,
                    "SequenceNo": sequence_no,
                    "RecordNo": record_no,
                    "Frequency": frequency,
                }
            }
        }
        _logger.debug("Void sale payload: %s", json.dumps(payload, indent=4))
        print(f"Void sale payload: {json.dumps(payload, indent=4)}")

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Step 4: Make the void sale API call
        try:
            response = requests.post(
                f"{base_url}/VoidReturnByRecordNo/",
                json=payload,
                headers=headers,
                auth=HTTPBasicAuth(username, password),
                timeout=60
            )
            response.raise_for_status()
            response_data = response.json()
            _logger.info("Void sale response: %s", json.dumps(response_data, indent=4))
            print(f"Void sale response: {json.dumps(response_data, indent=4)}")

            rstream = response_data.get("RStream", {})
            if rstream.get("CmdStatus") == "Approved":
                # Update pos.payment.payment_status
                payment_record.write({'payment_status': 'Voided'})
                _logger.info("Payment %s marked as voided", payment_record.id)
                print(f"Payment {payment_record.id} marked as voided")

                # Update pos.order.state, bypassing readonly
                # order.with_context(force_readonly=True).write({'state': 'voided'})
                # _logger.info("Order %s state updated to voided", order.id)
                print(f"Order {order.id} state updated to voided")

                # Store VoidReturnByRecordNo response in pos.emv.cache
                self.env['pos.emv.cache'].create({
                    'uuid': order_uuid or str(payment_record.id),
                    'response': json.dumps(response_data),
                    'timestamp': fields.Datetime.now(),
                })
                _logger.debug("Stored VoidReturnByRecordNo response in pos.emv.cache for uuid %s",
                              order_uuid or str(payment_record.id))

                return {
                    "RStream": {
                        "CmdStatus": "Approved",
                        "TextResponse": "APPROVED",
                    }
                }
            else:
                error_message = rstream.get("TextResponse", "Unknown error")
                _logger.warning("Void sale failed: %s", error_message)
                print(f"Void sale failed: {error_message}")
                raise UserError(f"Datacap Error: {error_message}")

        except requests.exceptions.RequestException as e:
            _logger.error("Datacap communication error: %s", str(e))
            print(f"Datacap communication error: {str(e)}")
            raise UserError("Failed to connect to Datacap. Please try again later.")

    def _extract_error_message(self, response_text):
        """Extract error message from XML response."""
        try:
            from xml.etree.ElementTree import fromstring
            root = fromstring(response_text)
            return root.find(".//TextResponse").text or "Unknown error"
        except Exception as e:
            _logger.error("Failed to parse error message: %s", e)
            return "Unknown error"


