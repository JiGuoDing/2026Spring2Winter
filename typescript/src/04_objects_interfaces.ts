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

console.log(user);
console.log(productPage);

export {};
