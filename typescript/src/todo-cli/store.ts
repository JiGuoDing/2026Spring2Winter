import { randomUUID } from "node:crypto";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { Todo } from "./model";

const DATA_FILE = join(process.cwd(), ".todo-data.json");

function isTodo(value: unknown): value is Todo {
  return (
    typeof value === "object" &&
    value !== null &&
    "id" in value &&
    "title" in value &&
    "status" in value &&
    "createdAt" in value
  );
}

export class TodoStore {
  private todos: Todo[];

  public constructor() {
    this.todos = this.load();
  }

  public add(title: string): Todo {
    const todo: Todo = {
      id: randomUUID(),
      title,
      status: "pending",
      createdAt: new Date().toISOString(),
    };

    this.todos.push(todo);
    this.save();
    return todo;
  }

  public list(): Todo[] {
    return [...this.todos];
  }

  public done(id: string): Todo | undefined {
    const todo = this.todos.find((item) => item.id === id);
    if (!todo) {
      return undefined;
    }

    todo.status = "done";
    todo.completedAt = new Date().toISOString();
    this.save();
    return todo;
  }

  public remove(id: string): Todo | undefined {
    const todo = this.todos.find((item) => item.id === id);
    if (!todo) {
      return undefined;
    }

    this.todos = this.todos.filter((item) => item.id !== id);
    this.save();
    return todo;
  }

  private load(): Todo[] {
    if (!existsSync(DATA_FILE)) {
      return [];
    }

    const raw = readFileSync(DATA_FILE, "utf8");
    const parsed: unknown = JSON.parse(raw);

    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed.filter(isTodo);
  }

  private save(): void {
    writeFileSync(DATA_FILE, JSON.stringify(this.todos, null, 2));
  }
}
