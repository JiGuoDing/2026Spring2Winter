type OrderStatus = "created" | "paid" | "shipped";

interface UserProfile {
  id: string;
  name: string;
  age: number;
  isActive: boolean;
}

const user: UserProfile = {
  id: "u_001",
  name: "Ada",
  age: 28,
  isActive: true,
};

const status: OrderStatus = "paid";
const coordinate: [number, number] = [120.16, 30.25];

function stringify(value: unknown): string {
  return typeof value === "string" ? value : JSON.stringify(value);
}

console.log(user, status, coordinate, stringify({ ok: true }));

export {};
