import { printChapter, printStep, printTip, printValue } from "./example-utils";

function hello(name: string): string {
  return `Hello, ${name}. Welcome to TypeScript.`;
}

const message = hello("Ada");

printChapter("01 环境准备与第一个 TS 程序");
printStep("调用带类型标注的函数");
printValue("hello(\"Ada\") 的返回值", message);
printTip("name 被声明为 string，所以调用 hello 时只能传入字符串。");

// 取消下面一行的注释，再运行 npm run check，可以看到类型错误。
// hello(42);

export {};
