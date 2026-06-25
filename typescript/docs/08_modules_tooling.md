# 08 模块化与工程配置

## 本章目标

- 使用 `import` 和 `export` 拆分模块。
- 理解 `tsconfig.json` 中几个关键字段。
- 区分运行、类型检查和构建。

## 核心概念

模块导出：

```ts
export interface Order {
  id: string;
}

export function createOrder(id: string): Order {
  return { id };
}
```

模块导入：

```ts
import { createOrder } from "./order-utils";
```

拆分模块时建议按职责划分：

- 类型定义和纯函数可以放到工具模块，例如 `src/order-utils.ts`。
- 示例入口只负责准备数据、调用函数和打印结果，例如 `src/08_modules_tooling.ts`。
- 导出的类型和函数会被 TypeScript 跨文件检查。

本项目的关键脚本：

- `npm run dev`：用 `tsx` 直接运行 TS。
- `npm run example`：运行 01 到 08 的全部示例。
- `npm run check`：用 `tsc --noEmit` 做类型检查。
- `npm run build`：编译到 `dist/`。
- `npm run start`：运行编译后的 JS。

## 可运行示例

对应文件：`src/08_modules_tooling.ts` 和 `src/order-utils.ts`

```bash
npm run example:08
```

也可以运行全部章节：

```bash
npm run example
```

本章输出会展示从 `order-utils.ts` 导入的 `createOrder` 和 `summarizeOrder` 如何协作。重点观察模块导入导出不会改变运行结果，但会让代码职责更清楚。

## 常见错误

错误示例：

```ts
import { createOrder } from "./missing-file";
```

模块路径错误会在类型检查或运行时暴露。拆分模块时，建议小步运行 `npm run check`。

## 练习题

1. 新建一个工具模块并导出函数。
2. 在另一个文件中导入并调用它。
3. 修改 `outDir`，观察构建输出变化。
4. 解释 `tsx` 和 `tsc` 的区别。
