import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import { PaymentDatacap } from "@Datacap/js/payment_datacap";

console.log("Datacap payment method loaded");
// Register the custom payment method
console.log("PaymentDatacap class:", PaymentDatacap);
register_payment_method("datacap", PaymentDatacap);

console.log("Datacap payment method registered",register_payment_method);