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
npm run example
npm run check
```

- `tsx`：直接运行 TypeScript 文件。
- `tsc --noEmit`：只检查类型，不生成编译产物。
- `tsc`：将 `src/` 编译到 `dist/`。
- `npm run example`：按顺序运行 01 到 08 的所有入门示例。

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

也可以运行全部章节：

```bash
npm run example
```

预期输出会带有章节标题、步骤标题和观察点，例如：

```text
=== 01 环境准备与第一个 TS 程序 ===
-- 调用带类型标注的函数
hello("Ada") 的返回值: Hello, Ada. Welcome to TypeScript.
观察点：name 被声明为 string，所以调用 hello 时只能传入字符串。
```

这类输出不是为了展示最终业务结果，而是帮助你把“代码写法”和“类型约束”对应起来。

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
