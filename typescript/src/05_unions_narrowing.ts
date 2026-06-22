type ApiState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "error"; error: string };

interface UserProfile {
  id: string;
  name: string;
}

function renderState(state: ApiState<UserProfile>): string {
  switch (state.status) {
    case "idle":
      return "等待请求";
    case "loading":
      return "加载中";
    case "success":
      return `用户：${state.data.name}`;
    case "error":
      return `错误：${state.error}`;
    default: {
      const exhaustiveCheck: never = state;
      return exhaustiveCheck;
    }
  }
}

function printId(input: string | number): string {
  if (typeof input === "string") {
    return input.toUpperCase();
  }

  return input.toFixed(0);
}

function hasEmail(value: unknown): value is { email: string } {
  return (
    typeof value === "object" &&
    value !== null &&
    "email" in value &&
    typeof value.email === "string"
  );
}

const state: ApiState<UserProfile> = {
  status: "success",
  data: { id: "u_001", name: "Ada" },
};

console.log(renderState(state));
console.log(printId(42));
console.log(hasEmail({ email: "ada@example.com" }));

export {};
