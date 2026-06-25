import { inspect } from "node:util";

export function printChapter(title: string): void {
  console.log(`\n=== ${title} ===`);
}

export function printStep(title: string): void {
  console.log(`\n-- ${title}`);
}

export function printValue(label: string, value: unknown): void {
  const formatted =
    typeof value === "string"
      ? value
      : inspect(value, { colors: false, depth: null });

  console.log(`${label}: ${formatted}`);
}

export function printTip(message: string): void {
  console.log(`观察点：${message}`);
}
