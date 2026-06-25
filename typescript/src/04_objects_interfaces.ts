import { printChapter, printStep, printTip, printValue } from "./example-utils";

interface User {
  readonly id: string;
  name: string;
  email?: string;
}

type ProductStatus = "draft" | "published";

interface Product {
  id: string;
  name: string;
  price: number;
  status: ProductStatus;
  metadata: Record<string, string>;
}

type PageResult<T> = {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
};

const user: User = {
  id: "u_001",
  name: "Ada",
  email: "ada@example.com",
};

const productPage: PageResult<Product> = {
  items: [
    {
      id: "p_001",
      name: "TypeScript Handbook",
      price: 59,
      status: "published",
      metadata: {
        category: "book",
      },
    },
  ],
  page: 1,
  pageSize: 10,
  total: 1,
};

printChapter("04 对象、接口与类型别名");

printStep("interface 描述对象结构");
printValue("User 对象", user);
printTip("id 是 readonly，创建后不能再重新赋值；email 是可选属性。");

printStep("type 组合泛型对象");
printValue("PageResult<Product>", productPage);
printValue("第一页商品数量", productPage.items.length);
printValue("商品元信息 category", productPage.items[0]?.metadata.category);
printTip("interface 适合对象模型，type 适合联合类型、工具类型和组合类型。");

export {};
