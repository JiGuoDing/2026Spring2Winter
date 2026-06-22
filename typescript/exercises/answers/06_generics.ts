interface ApiResponse<T> {
  code: number;
  data: T;
}

function getProperty<T, K extends keyof T>(value: T, key: K): T[K] {
  return value[key];
}

class MemoryCache<T extends { id: string }> {
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

type ProductPatch = Partial<Omit<Product, "id">>;

const response: ApiResponse<Product> = {
  code: 0,
  data: { id: "p_001", name: "Book", price: 59 },
};

const cache = new MemoryCache<Product>();
cache.set(response.data);

const patch: ProductPatch = { price: 49 };

console.log(getProperty(response.data, "name"), cache.get("p_001"), patch);

export {};
