import { printChapter, printStep, printTip, printValue } from "./example-utils";

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

printChapter("06 泛型");

printStep("泛型函数保留输入输出关系");
printValue("identity(\"typescript\")", identity("typescript"));
printValue("identity(2026)", identity(2026));

printStep("泛型接口和泛型约束");
printValue("ApiResponse<Product>", response);
printValue("getById([response.data], \"p_001\")", getById([response.data], "p_001"));
printValue("getById([response.data], \"missing\")", getById([response.data], "missing"));
printTip("T extends Entity 保证传入的数据一定有 id 字段。");

printStep("keyof 和工具类型");
printValue("getProperty(response.data, \"name\")", getProperty(response.data, "name"));
printValue("cache.get(\"p_001\")", cache.get("p_001"));
printValue("ProductPatch", patch);
printTip("Partial<Pick<Product, ...>> 可以表达只更新部分字段。");

export {};
