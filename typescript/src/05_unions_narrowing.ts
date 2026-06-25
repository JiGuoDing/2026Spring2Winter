import { printChapter, printStep, printTip, printValue } from "./example-utils";

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

printChapter("05 联合类型与类型收窄");

printStep("普通联合类型");
printValue("printId(\"u_001\")", printId("u_001"));
printValue("printId(42)", printId(42));
printTip("typeof input === \"string\" 之后，TypeScript 知道 input 可以调用字符串方法。");

printStep("判别联合");
printValue("renderState(success)", renderState(state));
printValue("renderState(error)", renderState({ status: "error", error: "网络超时" }));
printTip("status 是判别字段，switch 每个分支里都能拿到对应字段。");

printStep("自定义类型守卫");
printValue("hasEmail({ email: \"ada@example.com\" })", hasEmail({ email: "ada@example.com" }));
printValue("hasEmail({ name: \"Ada\" })", hasEmail({ name: "Ada" }));

export {};
