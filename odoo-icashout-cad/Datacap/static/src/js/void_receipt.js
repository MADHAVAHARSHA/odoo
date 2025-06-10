import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.isVoid = this.props.isVoid || false; // Access the isVoid flag from props
    },

    get receiptDetails() {
        const details = super.receiptDetails || {};
        if (this.isVoid) {
            details.voidMessage = `Transaction Voided - UUID: ${this.props.order.uuid}, Amount: ${this.env.utils.formatCurrency(this.props.order.amount_paid)}`;
        }
        return details;
    },
});