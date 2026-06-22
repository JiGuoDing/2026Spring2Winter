export type TodoStatus = "pending" | "done";

export interface Todo {
  id: string;
  title: string;
  status: TodoStatus;
  createdAt: string;
  completedAt?: string;
}

export type TodoCommand =
  | { kind: "add"; title: string }
  | { kind: "list" }
  | { kind: "done"; id: string }
  | { kind: "remove"; id: string }
  | { kind: "help" };
