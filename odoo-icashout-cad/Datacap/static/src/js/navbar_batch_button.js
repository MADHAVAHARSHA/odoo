/** @odoo-module **/

import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";


patch(Navbar.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
        this.notification = useService("notification");
    },

    async callBatchSummary() {
        try {
            const response = await this.pos.data.silentCall(
                "pos.payment.method",
                "batch_summary",
                []
            );
            this.notification.add(_t("Batch Summary Success"), {
                type: "success",
                message: response?.params?.message || "Operation completed.",
            });
        } catch (error) {
            console.error("Batch Summary failed", error);
            this.notification.add(_t("Batch Summary Failed"), {
                type: "danger",
                message: error.message,
            });
        }
    },

    async callBatchClose() {
        try {
            const response = await this.pos.data.silentCall(
                "pos.payment.method",
                "batch_close",
                []
            );
this.notification.add(_t("Batch Close Success"), {
                type: "success",
                message: response?.params?.message || "Batch closed successfully.",
            });
        } catch (error) {
            console.error("Batch Close failed", error);
            this.notification.add(_t("Batch Close Failed"), {
                type: "danger",
                message: error.message,
            });
        }
    },
});
