function formatPrice(amount: number, currency = "CNY"): string {
  return `${currency} ${amount.toFixed(2)}`;
}

function sum(...numbers: number[]): number {
  return numbers.reduce((total, value) => total + value, 0);
}

function mapValues<T, R>(values: T[], mapper: (value: T) => R): R[] {
  return values.map(mapper);
}

function toArray<T>(value: T): T[];
function toArray<T>(value: T[]): T[];
function toArray<T>(value: T | T[]): T[] {
  return Array.isArray(value) ? value : [value];
}

console.log(formatPrice(19.9), sum(1, 2, 3), mapValues([1, 2], String), toArray("ts"));

export {};
