interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

interface Entity {
  id: string;
}

function identity<T>(value: T): T {
  return value;
}

function getById<T extends Entity>(items: T[], id: string): T | undefined {
  return items.find((item) => item.id === id);
}

function getProperty<T, K extends keyof T>(value: T, key: K): T[K] {
  return value[key];
}

class MemoryCache<T extends Entity> {
  private readonly records = new Map<string, T>();

  set(value: T): void {
    this.records.set(value.id, value);
  }

  get(id: string): T | undefined {
    return this.records.get(id);
  }
}

interface Product {
  id: string;
  name: string;
  price: number;
}

type ProductPatch = Partial<Pick<Product, "name" | "price">>;

const response: ApiResponse<Product> = {
  code: 0,
  message: "ok",
  data: { id: "p_001", name: "Keyboard", price: 199 },
};

const cache = new MemoryCache<Product>();
cache.set(response.data);

const patch: ProductPatch = { price: 179 };

console.log(identity("typescript"));
console.log(getById([response.data], "p_001"));
console.log(getProperty(response.data, "name"));
console.log(cache.get("p_001"));
console.log(patch);

export {};
