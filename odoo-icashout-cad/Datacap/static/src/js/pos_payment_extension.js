/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

const PosPayment = registry.category("pos_available_models").get("pos.payment");

patch(PosPayment.prototype, {
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        result.receipt_lines = this.receipt_lines;
        result.card_no = this.card_no;
        return result;
    },
    is_done() {
        return this.get_payment_status()
            ? this.get_payment_status() === "done" || this.get_payment_status() === "reversed"|| this.get_payment_status() === "Approved"
            : true;
    },

});
