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

console.log(formatPrice(19.9));
console.log(joinNames("Ada"));
console.log(sum(1, 2, 3));
console.log(countText("typescript"));
console.log(mapValues([1, 2, 3], (value) => value * 2));
console.log(normalize(["  TS ", " Node "]));

export {};
