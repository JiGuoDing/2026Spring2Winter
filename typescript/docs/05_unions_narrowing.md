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

拿到联合类型后，不能直接当成某一种类型使用。你需要先通过 `typeof`、`in`、`Array.isArray`、判别字段或自定义类型守卫缩小范围。

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

也可以运行全部章节：

```bash
npm run example
```

本章输出会分三组：普通联合类型、判别联合、自定义类型守卫。重点观察判断条件出现后，代码里能访问的属性和方法会变得更精确。

## 常见错误

错误示例：

```ts
function render<T>(state: ApiState<T>): string {
  return String(state.data);
}
```

不是所有状态都有 `data`。必须先根据 `status` 收窄类型。

推荐写法是：

```ts
if (state.status === "success") {
  return String(state.data);
}
```

## 练习题

1. 定义 `PaymentResult`：成功时有 `transactionId`，失败时有 `reason`。
2. 使用 `switch` 渲染 API 状态。
3. 写一个自定义类型守卫 `hasEmail`。
4. 使用 `never` 检查 `switch` 是否覆盖所有状态。
