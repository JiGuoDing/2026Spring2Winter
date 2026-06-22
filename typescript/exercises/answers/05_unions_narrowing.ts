type PaymentResult =
  | { status: "success"; transactionId: string }
  | { status: "failed"; reason: string };

type ApiState<T> =
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "error"; error: string };

function render<T>(state: ApiState<T>): string {
  switch (state.status) {
    case "loading":
      return "加载中";
    case "success":
      return JSON.stringify(state.data);
    case "error":
      return state.error;
    default: {
      const exhaustiveCheck: never = state;
      return exhaustiveCheck;
    }
  }
}

function hasEmail(value: unknown): value is { email: string } {
  return typeof value === "object" && value !== null && "email" in value;
}

const result: PaymentResult = { status: "success", transactionId: "t_001" };

console.log(render({ status: "success", data: result }), hasEmail({ email: "a@example.com" }));

export {};
