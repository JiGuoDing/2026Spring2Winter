# 03 函数类型

## 本章目标

- 为函数参数和返回值添加类型。
- 掌握可选参数、默认参数、剩余参数。
- 理解回调函数和函数重载。

## 核心概念

函数类型标注通常写在参数和返回值上：

```ts
function formatPrice(amount: number, currency = "CNY"): string {
  return `${currency} ${amount.toFixed(2)}`;
}
```

回调函数也可以精确建模：

```ts
function mapValues<T, R>(values: T[], mapper: (value: T) => R): R[] {
  return values.map(mapper);
}
```

函数重载适合表达“同一个函数，不同输入对应不同输出”的场景。

## 可运行示例

对应文件：`src/03_functions.ts`

```bash
npm run example:03
```

## 常见错误

错误示例：

```ts
function sum(...numbers: number[]): number {
  return numbers.join(",");
}
```

函数声明返回 `number`，实际返回 `string`，类型检查会直接指出不一致。

## 练习题

1. 实现 `formatPrice(amount, currency)`。
2. 实现 `sum(...numbers)`。
3. 实现 `mapValues(values, mapper)`。
4. 使用函数重载实现 `toArray`：传入单个值返回单元素数组，传入数组则原样返回。
