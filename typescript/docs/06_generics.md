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

泛型接口：

```ts
interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}
```

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

## 常见错误

错误示例：

```ts
function getId<T>(value: T): string {
  return value.id;
}
```

普通 `T` 不保证一定有 `id`。应写成 `T extends { id: string }`。

## 练习题

1. 定义 `ApiResponse<T>`。
2. 实现 `getProperty<T, K extends keyof T>`。
3. 实现一个 `MemoryCache<T extends { id: string }>`。
4. 使用 `Partial` 定义商品更新参数。
