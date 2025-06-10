import { _t } from "@web/core/l10n/translation";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(TicketScreen.prototype, {
    setup() {
        this.state = useState({
            voidButtonDisabled: true,
        });
        console.log("TicketScreen setup executed");
        super.setup(...arguments);
    },

    mounted() {
        super.mounted(...arguments);
        console.log("TicketScreen mounted");
        this._updateVoidButtonState?.();
    },

    onClickOrder(clickedOrder) {
        console.log("Selected Order:", clickedOrder);

        this.setSelectedOrder(clickedOrder);
        this.numberBuffer.reset();

        if ((!clickedOrder || clickedOrder.uiState.locked) && !this.getSelectedOrderlineId()) {
            const firstLine = this.getSelectedOrder().get_orderlines()[0];
            if (firstLine) {
                this.state.selectedOrderlineIds[clickedOrder.id] = firstLine.id;
            }
        }

        if (clickedOrder && clickedOrder.create_date) {
            const creationDate = new Date(clickedOrder.create_date);
            const today = new Date();
            const isToday = creationDate.toDateString() === today.toDateString();

            this.state.voidButtonDisabled = !isToday;
            console.log("Void button disabled:", this.state.voidButtonDisabled);
        }
    },

    async voidTransaction() {
    const selectedOrder = this.getSelectedOrder();
    console.log("Attempting to void transaction for order:", selectedOrder);

    if (!selectedOrder) {
        console.warn("No order selected for void transaction.");
        return;
    }

    const creationDate = new Date(selectedOrder.create_date);
    const today = new Date();
    const isToday = creationDate.toDateString() === today.toDateString();

    const amountPaid = selectedOrder.amount_paid;
    const uuid = selectedOrder.uuid;

    console.log("Order creation date:", creationDate);
    console.log("Amount paid:", amountPaid);
    console.log("Transaction UUID:", uuid);
    console.log("Is order from today?", isToday);

    //  Only allow voiding if this was a refund (amount_paid < 0)
    if (amountPaid >= 0) {
        console.warn("This is not a refund. Only refunded transactions can be voided.");
        this.dialog.add(ConfirmationDialog, {
            title: _t("Action Not Allowed"),
            body: _t("Only previously refunded transactions can be voided."),
        });
        return;
    }

    if (!isToday) {
        console.warn("Cannot void transactions from previous days.");
        this.dialog.add(ConfirmationDialog, {
            title: _t("Action Not Allowed"),
            body: _t("Only today's transactions can be voided."),
        });
        return;
    }

    try {
        const response = await this.pos.data.silentCall(
            "pos.payment.method",
            "void_sale_by_record_number",
            [[], uuid, amountPaid] 
        );

        console.log("Void sale response:", response);

        if (response?.RStream?.CmdStatus === "Approved") {
            this.dialog.add(ConfirmationDialog, {
                title: _t("Success"),
                body: _t("Refund voided successfully."),
            });
        } else {
            const errorText = response?.RStream?.TextResponse || _t("Void failed. No further details.");
            this.dialog.add(ConfirmationDialog, {
                title: _t("Void Failed"),
                body: errorText,
            });
        }
    } catch (error) {
        console.error("Exception during void request:", error);
        this.dialog.add(ConfirmationDialog, {
            title: _t("Error"),
            body: _t("An error occurred while processing the void request: ") + error.message,
        });
    }
},
});