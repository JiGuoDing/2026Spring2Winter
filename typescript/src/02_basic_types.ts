import { printChapter, printStep, printTip, printValue } from "./example-utils";

const username: string = "Ada";
const age: number = 28;
const isActive: boolean = true;
const deletedAt: null = null;
let lastLoginAt: string | undefined;

const tags: string[] = ["typescript", "beginner"];
const scores: Array<number> = [95, 88, 100];
const coordinate: [number, number] = [120.16, 30.25];

let a: number = NaN;
let b: number = Infinity;

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

printChapter("02 基础类型");

printStep("基本值类型");
printValue("string 用户名", username);
printValue("number 年龄", age);
printValue("boolean 是否激活", isActive);
printValue("null 删除时间", deletedAt);
printValue("undefined 最近登录时间", lastLoginAt);

printStep("数组、元组和特殊 number");
printValue("string[] 标签", tags);
printValue("Array<number> 分数", scores);
printValue("[number, number] 坐标", coordinate);
printValue("NaN 示例", a);
printValue("Infinity 示例", b);

printStep("字面量类型与 unknown");
printValue("TodoStatus 只能是 pending 或 done", status);
printValue("parseInput(\" hello \")", parseInput(" hello "));
printValue("parseInput(123)", parseInput(123));
printTip("unknown 使用前要先判断类型；any 会绕过检查，入门阶段尽量少用。");

// fail("这会中断程序，所以示例中不执行。");
printTip("never 常见于 fail 这种永远不会正常返回的函数。");

export {};
