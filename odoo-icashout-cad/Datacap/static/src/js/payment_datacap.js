import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class PaymentDatacap extends PaymentInterface {
    constructor(pos, payment_method_id) {
        super(pos, payment_method_id);
        this.enable_reversals();
        console.log("PaymentDatacap: Initialized for payment method ID:", payment_method_id);
    }

    get fast_payments() {
        // Dynamically return true if the payment method name is "Manual Entry"
        return this.payment_method_id?.name === "Manual Entry";
    }

    async send_payment_request(uuid) {
        const line = this.pos.get_order().get_selected_paymentline();
        const methodId = line.payment_method_id?.id;
        const amount = parseFloat(line.amount).toFixed(2);

        if (!methodId || amount == 0) {
            this.show_error("Invalid payment. Amount is missing or zero.");
            line.set_payment_status("retry");
            return false;
        }

        line.set_payment_status("waiting");

        try {
            // Wake up device (max 5 attempts)
            for (let i = 0; i < 5; i++) {
                const reset = await this.reset_pad(methodId);
                if (reset) break;
                if (i === 4) throw new Error("Failed to wake up EMV device.");
                await new Promise((r) => setTimeout(r, 20000));
            }

            let response;
            if (amount < 0) {
                response = await this.pos.data.silentCall("pos.payment.method", "process_refund", [[methodId], Math.abs(amount), uuid]);
                console.log("send_payment_request: Used process_refund for refund");
            } else if (this.fast_payments) {
                response = await this.pos.data.silentCall("pos.payment.method", "process_manual_entry", [[methodId], amount, null, uuid]);
                console.log("send_payment_request: Used process_manual_entry for Manual Entry");
            } else {
                response = await this.pos.data.silentCall("pos.payment.method", "process_emv_sale", [[methodId], amount, null, uuid]);
                console.log("send_payment_request: Used process_emv_sale for EMV Sale");
            }

            const cmdStatus = response?.RStream?.CmdStatus || "Unknown";
            const textResponse = response?.RStream?.TextResponse || "No additional information";

            if (cmdStatus.toUpperCase() === "APPROVED") {
                line.set_payment_status("done");
                line.transaction_id = response?.RStream?.RefNo || uuid;
                line.card_type = response?.RStream?.CardType;
                line.set_receipt_info(response);
                return true;
            } else {
                line.set_payment_status("retry");
                this.show_error(`Payment CmdStatus: ${cmdStatus}\nTextResponse: ${textResponse}`);
                return false;
            }
        } catch (error) {
            this.show_error(error.message);
            line.set_payment_status("retry");
            return false;
        } finally {
            await this.reset_pad(methodId); // Always reset
        }
    }

    async send_payment_cancel(order, uuid) {
        const line = this.pos.get_order().get_selected_paymentline();
        line?.set_payment_status("retry");
        const methodId = line?.payment_method_id?.id;
        await this.reset_pad(methodId);
    }

    async send_payment_reversal(uuid) {
        const line = this.pos.get_order().get_paymentline(uuid);
        const methodId = line?.payment_method_id?.id;
        const txnId = line?.transaction_id;

        if (!methodId || !txnId) {
            this.show_error("Missing payment method or transaction ID.");
            return false;
        }

        try {
            const response = await this.pos.data.silentCall("pos.payment.method", "void_transaction", [[methodId], txnId, uuid]);
            if (response?.RStream?.CmdStatus === "Approved") return true;
            this.show_error("Void failed: " + (response?.RStream?.CmdStatus || "Unknown error"));
            return false;
        } catch (error) {
            this.show_error("Void error: " + error.message);
            return false;
        }
    }

    async close() {
        const line = this.pos.get_order()?.get_selected_paymentline();
        const methodId = line?.payment_method_id?.id;
        await this.reset_pad(methodId);
    }

    async reset_pad(methodId) {
        if (!methodId) return false;
        try {
            const result = await this.pos.data.silentCall("pos.payment.method", "emv_pad_reset", [[methodId]]);
            return result === true;
        } catch {
            return false;
        }
    }

    show_error(message) {
        this.env.services.dialog.add(AlertDialog, {
            title: "Datacap Error",
            body: message,
        });
    }
}
