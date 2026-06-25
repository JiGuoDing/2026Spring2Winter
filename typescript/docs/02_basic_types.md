# 02 基础类型

## 本章目标

- 掌握常见基础类型标注。
- 理解数组、元组、字面量类型。
- 知道 `unknown`、`any`、`never` 的边界。

## 核心概念

常用类型：

```ts
const name: string = "Ada";
const age: number = 28;
const active: boolean = true;
const tags: string[] = ["ts"];
const point: [number, number] = [120.16, 30.25];
```

`number` 同时表示整数和小数，也可以表示 `NaN`、`Infinity` 这类 JavaScript 数字值。TypeScript 不会新增运行时数字类型，它主要在编译阶段检查你的赋值和调用是否合理。

字面量类型适合表达有限状态：

```ts
type TodoStatus = "pending" | "done";
```

`unknown` 表示暂时不知道类型，使用前必须判断。`any` 会关闭类型检查，入门阶段应尽量避免。`never` 表示永远不会正常返回，常见于抛错函数或穷尽性检查。

## 可运行示例

对应文件：`src/02_basic_types.ts`

```bash
npm run example:02
```

也可以运行全部章节：

```bash
npm run example
```

示例会分组展示字符串、数字、布尔值、数组、元组、字面量类型、`unknown` 的安全解析，以及 `never` 的使用边界。控制台里的“观察点”会提示当前代码主要在说明哪条类型规则。

## 常见错误

错误示例：

```ts
let status: "pending" | "done" = "deleted";
```

`"deleted"` 不在允许的字面量集合中。把状态限制在有限集合里，可以减少业务代码中的非法状态。

另一个常见错误是把 `unknown` 当成已知类型直接使用：

```ts
function trimInput(input: unknown): string {
  return input.trim();
}
```

`unknown` 必须先判断，例如 `typeof input === "string"`，然后才能调用字符串方法。

## 练习题

1. 为用户资料补充 `id`、`name`、`age`、`isActive` 类型。
2. 使用元组表示经纬度坐标。
3. 用字面量类型定义订单状态：`created`、`paid`、`shipped`。
4. 写一个函数，把 `unknown` 输入安全转成字符串。
