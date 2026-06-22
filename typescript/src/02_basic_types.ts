const username: string = "Ada";
const age: number = 28;
const isActive: boolean = true;
const deletedAt: null = null;
let lastLoginAt: string | undefined;

const tags: string[] = ["typescript", "beginner"];
const scores: Array<number> = [95, 88, 100];
const coordinate: [number, number] = [120.16, 30.25];

type TodoStatus = "pending" | "done";
const status: TodoStatus = "pending";

function parseInput(input: unknown): string {
  if (typeof input === "string") {
    return input.trim();
  }

  return String(input);
}

function fail(message: string): never {
  throw new Error(message);
}

console.log({
  username,
  age,
  isActive,
  deletedAt,
  lastLoginAt,
  tags,
  scores,
  coordinate,
  status,
  parsed: parseInput(" hello "),
});

// fail("这会中断程序，所以示例中不执行。");

export {};
