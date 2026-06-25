# 04 对象、接口与类型别名

## 本章目标

- 使用对象类型、`interface` 和 `type` 建模业务数据。
- 理解可选属性、只读属性、索引签名。
- 知道 `interface` 和 `type` 的常见选择。

## 核心概念

对象结构可以直接写：

```ts
const user: { id: string; name: string } = {
  id: "u_001",
  name: "Ada",
};
```

更常见的方式是抽出接口：

```ts
interface User {
  readonly id: string;
  name: string;
  email?: string;
}
```

接口里的属性可以细分：

- `readonly id: string`：对象创建后不能重新赋值。
- `email?: string`：可选属性，可以存在，也可以不存在。
- `metadata: Record<string, string>`：索引结构，适合表达一组字符串键值对。

经验规则：

- 对象模型优先使用 `interface`。
- 联合类型、工具类型组合优先使用 `type`。

## 可运行示例

对应文件：`src/04_objects_interfaces.ts`

```bash
npm run example:04
```

也可以运行全部章节：

```bash
npm run example
```

本章输出会展示一个 `User` 对象和一个 `PageResult<Product>` 分页对象。重点观察接口如何约束对象字段，以及泛型分页类型如何复用在不同业务模型上。

## 常见错误

错误示例：

```ts
const user: User = { id: "u_001" };
```

如果 `name` 不是可选属性，创建对象时必须提供。TypeScript 会帮助你发现缺字段问题。

只读属性也只能在创建对象时赋值：

```ts
user.id = "u_002";
```

上面代码会报错，因为 `id` 被声明为 `readonly`。

## 练习题

1. 定义 `Product` 接口，包含 `id`、`name`、`price`。
2. 定义 `User` 接口，`email` 为可选属性。
3. 定义通用分页类型 `PageResult<T>`。
4. 使用 `Record<string, string>` 表示商品元信息。
