interface Product {
  id: string;
  name: string;
  price: number;
  metadata: Record<string, string>;
}

interface User {
  id: string;
  name: string;
  email?: string;
}

type PageResult<T> = {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
};

const page: PageResult<Product> = {
  items: [{ id: "p_001", name: "Book", price: 59, metadata: { category: "book" } }],
  page: 1,
  pageSize: 10,
  total: 1,
};

const user: User = { id: "u_001", name: "Ada" };

console.log(page, user);

export {};
