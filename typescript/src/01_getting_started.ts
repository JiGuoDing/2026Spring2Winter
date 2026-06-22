function hello(name: string): string {
  return `Hello, ${name}. Welcome to TypeScript.`;
}

const message = hello("Ada");
console.log(message);

// 取消下面一行的注释，再运行 npm run check，可以看到类型错误。
// hello(42);

export {};
