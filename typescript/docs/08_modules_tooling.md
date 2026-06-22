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

本项目的关键脚本：

- `npm run dev`：用 `tsx` 直接运行 TS。
- `npm run check`：用 `tsc --noEmit` 做类型检查。
- `npm run build`：编译到 `dist/`。
- `npm run start`：运行编译后的 JS。

## 可运行示例

对应文件：`src/08_modules_tooling.ts` 和 `src/order-utils.ts`

```bash
npm run example:08
```

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
