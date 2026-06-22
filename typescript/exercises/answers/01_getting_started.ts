function hello(firstName: string, lastName: string): string {
  return `Hello, ${firstName} ${lastName}`;
}

function square(n: number): number {
  return n * n;
}

console.log(hello("Ada", "Lovelace"));
console.log(square(4));

export {};
