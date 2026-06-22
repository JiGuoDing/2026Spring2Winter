# TypeScript 入门教程项目

这是一份面向 TypeScript 初学者的教程项目。项目包含中文教程、可运行示例、练习题和一个 Todo CLI 综合实战。

## 学习前提

- 已经了解 JavaScript 的变量、函数、对象和数组。
- 本机已安装 Node.js LTS。
- 使用 `npm` 安装依赖和运行脚本。

## 快速开始

```bash
npm install
npm run check
npm run dev
```

常用命令：

```bash
npm run example:02
npm run build
npm run start
npm run todo -- add "learn typescript"
npm run todo -- list
npm run todo -- done <id>
npm run todo -- remove <id>
```

Todo CLI 会在项目根目录生成 `.todo-data.json` 保存数据，该文件已加入 `.gitignore`。

## 学习路径

| 顺序 | 文档 | 示例 |
|------|------|------|
| 01 | `docs/01_getting_started.md` | `src/01_getting_started.ts` |
| 02 | `docs/02_basic_types.md` | `src/02_basic_types.ts` |
| 03 | `docs/03_functions.md` | `src/03_functions.ts` |
| 04 | `docs/04_objects_interfaces.md` | `src/04_objects_interfaces.ts` |
| 05 | `docs/05_unions_narrowing.md` | `src/05_unions_narrowing.ts` |
| 06 | `docs/06_generics.md` | `src/06_generics.ts` |
| 07 | `docs/07_classes.md` | `src/07_classes.ts` |
| 08 | `docs/08_modules_tooling.md` | `src/08_modules_tooling.ts` |
| 09 | `docs/09_project_todo_cli.md` | `src/todo-cli/` |

## 项目结构

```text
typescript/
├── README.md
├── package.json
├── tsconfig.json
├── docs/
├── src/
│   └── todo-cli/
└── exercises/
    └── answers/
```

## 建议学习方式

1. 按顺序阅读 `docs/` 中的章节。
2. 每读一章，运行对应的 `npm run example:xx`。
3. 修改源码，故意制造类型错误，然后运行 `npm run check` 观察提示。
4. 完成 `exercises/` 中的练习，再对照 `exercises/answers/`。
5. 最后阅读并运行 Todo CLI，理解类型如何帮助拆分模块。
