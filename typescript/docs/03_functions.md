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

默认参数会参与类型推断，上面的 `currency = "CNY"` 会被推断为 `string`，调用时可以不传。

可选参数用 `?` 表示，剩余参数用数组类型表示：

```ts
function joinNames(firstName: string, lastName?: string): string {
  return lastName ? `${firstName} ${lastName}` : firstName;
}

function sum(...numbers: number[]): number {
  return numbers.reduce((total, current) => total + current, 0);
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

也可以运行全部章节：

```bash
npm run example
```

本章输出会按“默认参数”“可选参数”“剩余参数”“回调”“函数重载”分组。你可以对照输出看同一个函数在不同输入下的返回值。

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
