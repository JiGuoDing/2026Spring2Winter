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

export function summarizeOrder(order: Order): string {
  const total = order.items.reduce(
    (sum, item) => sum + item.price * item.quantity,
    0,
  );

  return `订单 ${order.id} 共 ${order.items.length} 件商品，总价 ${total}`;
}
