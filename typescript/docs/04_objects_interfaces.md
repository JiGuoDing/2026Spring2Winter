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

经验规则：

- 对象模型优先使用 `interface`。
- 联合类型、工具类型组合优先使用 `type`。

## 可运行示例

对应文件：`src/04_objects_interfaces.ts`

```bash
npm run example:04
```

## 常见错误

错误示例：

```ts
const user: User = { id: "u_001" };
```

如果 `name` 不是可选属性，创建对象时必须提供。TypeScript 会帮助你发现缺字段问题。

## 练习题

1. 定义 `Product` 接口，包含 `id`、`name`、`price`。
2. 定义 `User` 接口，`email` 为可选属性。
3. 定义通用分页类型 `PageResult<T>`。
4. 使用 `Record<string, string>` 表示商品元信息。
