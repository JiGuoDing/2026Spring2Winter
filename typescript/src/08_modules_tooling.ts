import { printChapter, printStep, printTip, printValue } from "./example-utils";
import { createOrder, summarizeOrder } from "./order-utils";

const order = createOrder("o_001", [
  { name: "TypeScript Book", price: 59, quantity: 1 },
  { name: "Keyboard", price: 199, quantity: 1 },
]);

printChapter("08 模块化与工程配置");

printStep("从 order-utils.ts 导入函数");
printValue("createOrder(...) 返回值", order);

printStep("复用模块函数汇总订单");
printValue("summarizeOrder(order)", summarizeOrder(order));
printTip("import/export 让类型和实现可以按职责拆分；npm run check 会检查跨文件类型是否匹配。");
