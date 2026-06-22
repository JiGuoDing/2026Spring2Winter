type Priority = "low" | "medium" | "high";

interface Todo {
  id: string;
  title: string;
  status: "pending" | "done";
  priority: Priority;
}

type Command =
  | { kind: "add"; title: string; priority: Priority }
  | { kind: "clear-done" }
  | { kind: "list" };

function handle(command: Command, todos: Todo[]): Todo[] {
  switch (command.kind) {
    case "add":
      return [
        ...todos,
        {
          id: String(Date.now()),
          title: command.title,
          status: "pending",
          priority: command.priority,
        },
      ];
    case "clear-done":
      return todos.filter((todo) => todo.status !== "done");
    case "list":
      console.log(todos);
      return todos;
    default: {
      const exhaustiveCheck: never = command;
      return exhaustiveCheck;
    }
  }
}

console.log(handle({ kind: "add", title: "learn ts", priority: "high" }, []));

export {};
