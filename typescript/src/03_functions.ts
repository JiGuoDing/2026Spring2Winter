import { printChapter, printStep, printTip, printValue } from "./example-utils";

function formatPrice(amount: number, currency = "CNY"): string {
  return `${currency} ${amount.toFixed(2)}`;
}

function joinNames(firstName: string, lastName?: string): string {
  return lastName ? `${firstName} ${lastName}` : firstName;
}

function sum(...numbers: number[]): number {
  return numbers.reduce((total, current) => total + current, 0);
}

const countText: (input: string) => number = (input) => input.length;

function mapValues<T, R>(values: T[], mapper: (value: T) => R): R[] {
  return values.map(mapper);
}

function normalize(input: string): string;
function normalize(input: string[]): string[];
function normalize(input: string | string[]): string | string[] {
  if (Array.isArray(input)) {
    return input.map((item) => item.trim().toLowerCase());
  }

  return input.trim().toLowerCase();
}

printChapter("03 函数类型");

printStep("参数类型、返回值类型和默认参数");
printValue("formatPrice(19.9)", formatPrice(19.9));
printValue("formatPrice(19.9, \"USD\")", formatPrice(19.9, "USD"));

printStep("可选参数和剩余参数");
printValue("joinNames(\"Ada\")", joinNames("Ada"));
printValue("joinNames(\"Ada\", \"Lovelace\")", joinNames("Ada", "Lovelace"));
printValue("sum(1, 2, 3)", sum(1, 2, 3));

printStep("函数类型、回调和重载");
printValue("countText(\"typescript\")", countText("typescript"));
printValue("mapValues([1, 2, 3], value => value * 2)", mapValues([1, 2, 3], (value) => value * 2));
printValue("normalize(\"  TS \")", normalize("  TS "));
printValue("normalize([\"  TS \", \" Node \"])", normalize(["  TS ", " Node "]));
printTip("函数重载让调用方看到更精确的输入输出关系。");

export {};
