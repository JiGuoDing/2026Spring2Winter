import type { TodoCommand } from "./model";

export function parseCommand(args: string[]): TodoCommand {
  const [command, ...rest] = args;

  switch (command) {
    case "add": {
      const title = rest.join(" ").trim();
      return title ? { kind: "add", title } : { kind: "help" };
    }
    case "list":
      return { kind: "list" };
    case "done": {
      const [id] = rest;
      return id ? { kind: "done", id } : { kind: "help" };
    }
    case "remove": {
      const [id] = rest;
      return id ? { kind: "remove", id } : { kind: "help" };
    }
    default:
      return { kind: "help" };
  }
}

export function helpText(): string {
  return [
    "用法：",
    "  npm run todo -- add \"learn typescript\"",
    "  npm run todo -- list",
    "  npm run todo -- done <id>",
    "  npm run todo -- remove <id>",
  ].join("\n");
}
