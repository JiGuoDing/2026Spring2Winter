import { helpText, parseCommand } from "./commands";
import type { Todo } from "./model";
import { TodoStore } from "./store";

function formatTodo(todo: Todo): string {
  const marker = todo.status === "done" ? "x" : " ";
  return `[${marker}] ${todo.id} ${todo.title}`;
}

function main(): void {
  const command = parseCommand(process.argv.slice(2));
  const store = new TodoStore();

  switch (command.kind) {
    case "add": {
      const todo = store.add(command.title);
      console.log(`已添加：${formatTodo(todo)}`);
      return;
    }
    case "list": {
      const todos = store.list();
      if (todos.length === 0) {
        console.log("暂无 Todo。");
        return;
      }

      console.log(todos.map(formatTodo).join("\n"));
      return;
    }
    case "done": {
      const todo = store.done(command.id);
      console.log(todo ? `已完成：${formatTodo(todo)}` : `未找到：${command.id}`);
      return;
    }
    case "remove": {
      const todo = store.remove(command.id);
      console.log(todo ? `已删除：${formatTodo(todo)}` : `未找到：${command.id}`);
      return;
    }
    case "help":
      console.log(helpText());
      return;
    default: {
      const exhaustiveCheck: never = command;
      throw new Error(`未知命令：${String(exhaustiveCheck)}`);
    }
  }
}

main();
