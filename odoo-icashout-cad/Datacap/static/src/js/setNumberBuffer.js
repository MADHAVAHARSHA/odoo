/** @odoo-module **/

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreen.prototype, {
    async updateSelectedPaymentline(amount = false) {
        console.log("updateSelectedPaymentline called with amount:", amount);
        console.log("Payment methods from config:", this.payment_methods_from_config);

        // Find the Datacap (card) payment method
        let cardMethod = this.payment_methods_from_config.find(pm => pm.is_datacap);
        // Fallback: Identify Datacap by ID if is_datacap isn't set
        if (!cardMethod) {
            cardMethod = this.payment_methods_from_config.find(pm => pm.id === 2); // Datacap ID: 2
            console.log("Fallback: Identified Datacap by ID (2):", cardMethod);
        }
        console.log("Card method found:", cardMethod);

        // If no Datacap method is found, show an error if amount is provided, else proceed
        if (!cardMethod) {
            console.warn("No Datacap payment method found even after fallback");
            if (amount !== false) {
                this.dialog.add(AlertDialog, {
                    title: _t("Error"),
                    body: _t("Datacap payment method not configured. Please select another method."),
                });
            }
            return super.updateSelectedPaymentline(amount);
        }

        // Get the full amount from the number buffer
        const bufferAmount = this.numberBuffer.getFloat();
        console.log("Number buffer amount:", bufferAmount);

        // If no payment lines exist or all are paid, prioritize Datacap
        const datacapExists = this.paymentLines.some(line => line.payment_method_id.id === cardMethod.id);
        if (this.paymentLines.every((line) => line.paid) || this.paymentLines.length === 0) {
            if (!datacapExists) {
                console.log("No payment lines or all paid, adding Datacap payment line");
                await this.addNewPaymentLine(cardMethod);
                this._startManualInputTimer(); // Start 10-second timer for manual input
            }
        }

        // If a keypad input or buffer update is detected, ensure Datacap is used
        if (amount !== false || bufferAmount !== null) {
            console.log("Keypad input or buffer update detected, prioritizing Datacap payment method");

            // Check if a Datacap line already exists
            let datacapLine = this.paymentLines.find(line => line.payment_method_id.id === cardMethod.id);

            // Remove all non-Datacap payment lines to ensure only Datacap is used for the initial amount
            const nonDatacapLines = this.paymentLines.filter(line => line.payment_method_id.id !== cardMethod.id);
            for (const line of nonDatacapLines) {
                console.log("Removing non-Datacap line:", line.payment_method_id.name);
                this.currentOrder.remove_paymentline(line);
            }

            // Add a new Datacap payment line if none exists
            if (!datacapLine) {
                console.log("Adding new Datacap payment line");
                await this.addNewPaymentLine(cardMethod);
                datacapLine = this.paymentLines.find(line => line.payment_method_id.id === cardMethod.id);
                this._startManualInputTimer(); // Start 10-second timer for manual input
            }

            // Ensure the Datacap line is selected and update its amount
            if (datacapLine) {
                console.log("Selecting Datacap line:", datacapLine.payment_method_id.name);
                this.currentOrder.select_paymentline(datacapLine);

                // Check terminal payment status and allow manual update within the timer window
                const payment_terminal = datacapLine.payment_method_id.payment_terminal;
                const payment_status = datacapLine.get_payment_status();
                if (payment_terminal) {
                    console.log("Payment terminal detected, status:", payment_status);
                    if (this._isManualInputAllowed() && ["waiting", "waitingCard", "timeout"].includes(payment_status)) {
                        console.log("Manual input allowed within 10-second window");
                    } else if (["waiting", "waitingCard", "timeout"].includes(payment_status)) {
                        console.log("Terminal payment in progress, cannot update amount manually");
                        return;
                    }
                }

                // Update the amount on the Datacap line with the full buffer value
                const hasCashPaymentMethod = this.payment_methods_from_config.some(
                    (method) => method.type === "cash"
                );
                const finalAmount = bufferAmount !== null ? bufferAmount : amount;
                if (
                    !hasCashPaymentMethod &&
                    finalAmount > this.currentOrder.get_due() + datacapLine.amount
                ) {
                    console.log("Amount exceeds due amount, adjusting to due amount");
                    datacapLine.set_amount(0);
                    this.numberBuffer.set(this.currentOrder.get_due().toString());
                    datacapLine.set_amount(this.currentOrder.get_due());
                    this.showMaxValueError();
                } else {
                    datacapLine.set_amount(finalAmount);
                }
            } else {
                console.warn("No Datacap line found after adding");
            }
        } else {
            // For non-keypad input with no buffer value, proceed with original logic
            await super.updateSelectedPaymentline(amount);
        }

        // Update the UI once at the end
        if (this.selectedPaymentLine) {
            console.log("UI updated, selected payment method:", this.selectedPaymentLine.payment_method_id.name);
            this.render();
        }
    },

    // Private method to manage the 10-second manual input timer
    _startManualInputTimer() {
        if (!this._manualInputTimer) {
            this._manualInputTimer = setTimeout(() => {
                console.log("10-second manual input window expired");
                this._manualInputTimer = null; // Clear the timer
            }, 1000); // 1 seconds
        }
    },

    // Check if manual input is still allowed within the 10-second window
    _isManualInputAllowed() {
        return this._manualInputTimer !== null;
    },
});