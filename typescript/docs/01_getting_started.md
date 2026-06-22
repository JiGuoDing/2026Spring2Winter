# 01 环境准备与第一个 TS 程序

## 本章目标

- 理解 TypeScript 与 JavaScript 的关系。
- 能安装依赖、运行 `.ts` 文件、执行类型检查。
- 写出第一个带参数类型和返回值类型的函数。

## 核心概念

TypeScript 是 JavaScript 的超集。你写的 TypeScript 最终会被编译成 JavaScript，类型主要在开发阶段帮助你发现错误。

本项目使用：

```bash
npm install
npm run dev
npm run check
```

- `tsx`：直接运行 TypeScript 文件。
- `tsc --noEmit`：只检查类型，不生成编译产物。
- `tsc`：将 `src/` 编译到 `dist/`。

## 可运行示例

对应文件：`src/01_getting_started.ts`

```ts
function hello(name: string): string {
  return `Hello, ${name}. Welcome to TypeScript.`;
}

console.log(hello("Ada"));
```

运行：

```bash
npm run example:01
```

预期输出：

```text
Hello, Ada. Welcome to TypeScript.
```

## 常见错误

错误示例：

```ts
hello(42);
```

`hello` 的参数声明为 `string`，传入 `number` 会在 `npm run check` 时被拦截。TypeScript 的价值就在于让这类错误尽早暴露。

## 练习题

1. 将 `hello` 改为接收 `firstName` 和 `lastName` 两个字符串参数。
2. 故意传入数字参数，运行 `npm run check` 观察报错。
3. 新增一个 `square(n: number): number` 函数。
4. 运行 `npm run build`，观察 `dist/` 中生成的 JavaScript 文件。
