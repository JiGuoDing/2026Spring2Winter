export interface OrderItem {
  name: string;
  price: number;
  quantity: number;
}

export interface Order {
  id: string;
  items: OrderItem[];
}

export function createOrder(id: string, items: OrderItem[]): Order {
  return { id, items };
}

export function calculateOrderTotal(order: Order): number {
  return order.items.reduce((sum, item) => sum + item.price * item.quantity, 0);
}

export function summarizeOrder(order: Order): string {
  const total = calculateOrderTotal(order);
  const itemSummary = order.items
    .map((item) => `${item.name} x ${item.quantity}`)
    .join("，");

  return `订单 ${order.id} 包含 ${itemSummary}，总价 ${total}`;
}
