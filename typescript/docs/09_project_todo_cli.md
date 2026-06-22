# 09 综合实战：Todo CLI

## 本章目标

- 使用 TypeScript 拆分一个小型命令行项目。
- 用接口建模数据，用联合类型建模命令。
- 用类型收窄处理不同命令分支。

## 项目结构

```text
src/todo-cli/
├── index.ts
├── model.ts
├── store.ts
└── commands.ts
```

- `model.ts`：定义 `Todo`、`TodoStatus`、`TodoCommand`。
- `store.ts`：负责读取、保存、增删改查 Todo。
- `commands.ts`：把命令行参数解析为判别联合。
- `index.ts`：入口，根据命令调用 store。

## 运行方式

```bash
npm run todo -- add "learn typescript"
npm run todo -- list
npm run todo -- done <id>
npm run todo -- remove <id>
```

数据保存在 `.todo-data.json`，该文件不会提交到版本库。

## 核心概念

命令使用判别联合建模：

```ts
type TodoCommand =
  | { kind: "add"; title: string }
  | { kind: "list" }
  | { kind: "done"; id: string }
  | { kind: "remove"; id: string }
  | { kind: "help" };
```

入口文件中使用 `switch (command.kind)` 后，每个分支都能获得精确类型。

## 常见错误

错误示例：

```ts
if (command.kind === "list") {
  console.log(command.id);
}
```

`list` 命令没有 `id`。TypeScript 会阻止你访问不存在的字段。

## 练习题

1. 为 Todo 增加 `priority: "low" | "medium" | "high"`。
2. 增加 `clear-done` 命令，删除所有已完成任务。
3. 修改 `list`，让已完成任务显示完成时间。
4. 为 `store.ts` 增加简单的数据校验错误提示。
