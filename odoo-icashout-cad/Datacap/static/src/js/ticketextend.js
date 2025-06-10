import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";


patch(TicketScreen.prototype, {
    getStatus(order) {
        if (
            order.uiState?.locked &&
            (order.get_screen_data().name === "" || this.state.filter === "SYNCED")
        ) {
            const firstPayment = order.payment_ids?.[0];
            const status = firstPayment?.payment_status;

            switch (status) {
                case "Voided":
                    return _t("Voided");
                case "refunded":
                    return _t("Refunded");
                case "Approved":
                    return _t("Approved");
                case "pending":
                    return _t("Pending");
                case "done":
                    return _t("Paid");
                default:
                    return _t("Paid");
            }
        } else {
            const screen = order.get_screen_data();
            return this._getOrderStates().get(this._getScreenToStatusMap()[screen.name])?.text;
        }
    }
});


export class CustomTicketScreen extends TicketScreen {
    static template = "Custom.TicketScreen";

    get paymentSummary() {
        if (!this.currentOrder) {
            console.warn("No current order found.");
            return [];
        }

        console.log("Current Order:", this.currentOrder);
        console.log("Current Order Payment Lines:", this.currentOrder.paymentlines);

        // Ensure paymentlines exist, otherwise return an empty array
        return this.currentOrder.paymentlines ?? [];
    }

    mounted() {
        console.log("Custom Ticket Screen Mounted");
    }
}
