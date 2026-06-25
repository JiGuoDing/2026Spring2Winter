# 06 泛型

## 本章目标

- 理解泛型解决的是“类型可变但关系稳定”的问题。
- 掌握泛型函数、泛型接口、泛型约束。
- 使用常见工具类型减少重复。

## 核心概念

泛型函数：

```ts
function identity<T>(value: T): T {
  return value;
}
```

这里的 `T` 不是某个具体类型，而是调用时由输入决定的类型。传入字符串时返回字符串，传入数字时返回数字。

泛型接口：

```ts
interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}
```

`ApiResponse<T>` 把响应外壳固定下来，把 `data` 的具体类型留给使用方决定。

泛型约束：

```ts
function getById<T extends { id: string }>(items: T[], id: string): T | undefined {
  return items.find((item) => item.id === id);
}
```

## 可运行示例

对应文件：`src/06_generics.ts`

```bash
npm run example:06
```

也可以运行全部章节：

```bash
npm run example
```

本章输出会展示泛型函数、泛型接口、`extends` 约束、`keyof` 和工具类型。重点观察泛型如何保留“输入类型”和“输出类型”之间的关系。

## 常见错误

错误示例：

```ts
function getId<T>(value: T): string {
  return value.id;
}
```

普通 `T` 不保证一定有 `id`。应写成 `T extends { id: string }`。

`keyof` 也常和泛型一起使用：

```ts
function getProperty<T, K extends keyof T>(value: T, key: K): T[K] {
  return value[key];
}
```

这样 `key` 只能传对象真实存在的字段名。

## 练习题

1. 定义 `ApiResponse<T>`。
2. 实现 `getProperty<T, K extends keyof T>`。
3. 实现一个 `MemoryCache<T extends { id: string }>`。
4. 使用 `Partial` 定义商品更新参数。
