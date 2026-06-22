import { createOrder, summarizeOrder } from "./order-utils";

const order = createOrder("o_001", [
  { name: "TypeScript Book", price: 59, quantity: 1 },
  { name: "Keyboard", price: 199, quantity: 1 },
]);

console.log(summarizeOrder(order));
