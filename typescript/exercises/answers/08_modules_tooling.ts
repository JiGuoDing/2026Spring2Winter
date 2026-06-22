export interface CalculatorInput {
  left: number;
  right: number;
}

export function add(input: CalculatorInput): number {
  return input.left + input.right;
}

console.log(add({ left: 1, right: 2 }));
