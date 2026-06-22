# 05 联合类型与类型收窄

## 本章目标

- 使用联合类型表达多种可能。
- 使用判别联合表达业务状态。
- 掌握常见类型收窄方式。

## 核心概念

联合类型表示“可能是 A，也可能是 B”：

```ts
function printId(input: string | number): string {
  if (typeof input === "string") {
    return input.toUpperCase();
  }

  return input.toFixed(0);
}
```

判别联合适合表达 API 状态：

```ts
type ApiState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "error"; error: string };
```

当你判断 `status === "success"` 后，TypeScript 会知道此时一定有 `data`。

## 可运行示例

对应文件：`src/05_unions_narrowing.ts`

```bash
npm run example:05
```

## 常见错误

错误示例：

```ts
function render<T>(state: ApiState<T>): string {
  return String(state.data);
}
```

不是所有状态都有 `data`。必须先根据 `status` 收窄类型。

## 练习题

1. 定义 `PaymentResult`：成功时有 `transactionId`，失败时有 `reason`。
2. 使用 `switch` 渲染 API 状态。
3. 写一个自定义类型守卫 `hasEmail`。
4. 使用 `never` 检查 `switch` 是否覆盖所有状态。
