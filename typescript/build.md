# 角色与任务
你是一名资深 TypeScript 工程师和教育内容创作者。请在 `typescript/` 目录下生成一份 **《TypeScript 入门教程项目》**。

## 项目定位
- 面向已经具备少量 JavaScript 基础、希望系统入门 TypeScript 的学习者。
- 目标不是堆砌语法清单，而是通过可运行示例让学习者理解 TypeScript 如何提升代码可维护性。
- 教程应覆盖环境搭建、类型系统、函数与对象建模、模块化、工程配置、常见工具链和小型实战项目。
- 所有示例代码必须可以在本地通过 `npm` 脚本运行或类型检查。

---

## 一、推荐项目结构

```text
typescript/
├── build.md                         # 本文档：给后续 agent 的构建说明
├── README.md                        # 教程首页、学习路径、运行方式
├── package.json                     # npm 脚本与开发依赖
├── tsconfig.json                    # TypeScript 编译配置
├── .gitignore                       # 忽略 node_modules、dist 等产物
│
├── docs/                            # Markdown 教程章节
│   ├── 01_getting_started.md        # 环境准备与第一个 TS 程序
│   ├── 02_basic_types.md            # 基础类型
│   ├── 03_functions.md              # 函数类型
│   ├── 04_objects_interfaces.md     # 对象、接口与类型别名
│   ├── 05_unions_narrowing.md       # 联合类型与类型收窄
│   ├── 06_generics.md               # 泛型
│   ├── 07_classes.md                # 类与访问修饰符
│   ├── 08_modules_tooling.md        # 模块化、tsconfig、工程工具
│   └── 09_project_todo_cli.md       # 综合实战：Todo CLI
│
├── src/                             # 可运行示例源码
│   ├── 01_getting_started.ts
│   ├── 02_basic_types.ts
│   ├── 03_functions.ts
│   ├── 04_objects_interfaces.ts
│   ├── 05_unions_narrowing.ts
│   ├── 06_generics.ts
│   ├── 07_classes.ts
│   ├── 08_modules_tooling.ts
│   └── todo-cli/
│       ├── index.ts
│       ├── model.ts
│       ├── store.ts
│       └── commands.ts
│
└── exercises/                       # 练习与参考答案
    ├── README.md                    # 练习索引
    ├── 01_getting_started.md
    ├── 02_basic_types.md
    ├── ...
    └── answers/
        ├── 01_getting_started.ts
        ├── 02_basic_types.ts
        └── ...
```

> 如果时间有限，至少完成 `README.md`、`package.json`、`tsconfig.json`、`docs/01~06`、`src/01~06` 和 `exercises/README.md`。

---

## 二、技术选型

| 方向 | 建议 |
|------|------|
| 运行环境 | Node.js LTS |
| 包管理器 | 优先使用 `npm`，避免引入 pnpm/yarn 作为强依赖 |
| TypeScript | 使用当前稳定版 `typescript` |
| 运行 TS | 使用 `tsx` 运行示例，降低初学者成本 |
| 类型检查 | `tsc --noEmit` |
| 构建输出 | `tsc` 编译到 `dist/` |
| 代码风格 | 保持示例短小、中文注释清晰，不强制引入 ESLint/Prettier |

`package.json` 至少提供以下脚本：

```json
{
  "scripts": {
    "dev": "tsx src/01_getting_started.ts",
    "check": "tsc --noEmit",
    "build": "tsc",
    "start": "node dist/01_getting_started.js",
    "todo": "tsx src/todo-cli/index.ts"
  },
  "devDependencies": {
    "tsx": "latest",
    "typescript": "latest",
    "@types/node": "latest"
  }
}
```

`tsconfig.json` 建议使用严格模式：

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "rootDir": "src",
    "outDir": "dist",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src/**/*.ts"]
}
```

---

## 三、学习路线图

```text
环境准备
  ↓
基础类型
  ↓
函数类型
  ↓
对象建模：interface / type
  ↓
联合类型与类型收窄
  ↓
泛型
  ↓
类与面向对象
  ↓
模块化与工程配置
  ↓
Todo CLI 综合实战
```

| 阶段 | 章节 | 学习目标 |
|------|------|----------|
| 入门篇 | 01 | 能安装依赖、运行 TS 文件、理解编译和类型检查 |
| 基础篇 | 02~04 | 能为变量、函数、对象建立基本类型模型 |
| 进阶篇 | 05~07 | 能使用联合类型、类型收窄、泛型和类表达真实业务约束 |
| 工程篇 | 08 | 能理解 `tsconfig`、模块系统、构建输出和 npm 脚本 |
| 实战篇 | 09 | 能完成一个有模块划分的小型命令行项目 |

---

## 四、章节内容要求

### 01_getting_started — 环境准备与第一个 TS 程序
- 说明 TypeScript 与 JavaScript 的关系：TS 是 JS 的超集，最终会编译为 JS。
- 指导初始化项目：`npm init -y`、安装 `typescript`、`tsx`、`@types/node`。
- 演示 `tsc --init` 或手写 `tsconfig.json`。
- 编写第一个 `hello(name: string): string` 示例。
- 解释类型错误只在开发期阻止错误，运行时仍是 JavaScript。
- 练习：修改函数参数类型、观察 `npm run check` 的报错。

### 02_basic_types — 基础类型
- 覆盖 `string`、`number`、`boolean`、`null`、`undefined`。
- 覆盖数组：`string[]` 与 `Array<string>`。
- 覆盖元组：例如 `[number, string]`。
- 覆盖字面量类型：`"pending" | "done"`。
- 解释 `any`、`unknown`、`never` 的使用边界。
- 强调：初学阶段不要用 `any` 逃避建模。
- 练习：为用户资料、订单状态、坐标元组补充类型。

### 03_functions — 函数类型
- 函数参数与返回值类型标注。
- 可选参数、默认参数、剩余参数。
- 函数类型表达式：`(input: string) => number`。
- 回调函数类型。
- 简要说明函数重载，给一个轻量示例即可。
- 练习：实现 `mapValues`、`formatPrice`、`retry` 等小函数。

### 04_objects_interfaces — 对象、接口与类型别名
- 对象类型字面量。
- `interface` 定义对象结构。
- `type` 定义类型别名。
- 可选属性、只读属性、索引签名。
- `interface` 与 `type` 的常见选择：
  - 对象模型优先 `interface`。
  - 联合类型、工具组合优先 `type`。
- 练习：为商品、用户、分页结果建模。

### 05_unions_narrowing — 联合类型与类型收窄
- 联合类型：`string | number`。
- 字面量联合：`"idle" | "loading" | "success" | "error"`。
- 判别联合：使用 `kind` 或 `status` 字段表达不同状态。
- 类型收窄方式：`typeof`、`in`、相等判断、自定义类型守卫。
- 用 `never` 做穷尽性检查。
- 练习：建模 API 请求状态、支付结果、表单校验结果。

### 06_generics — 泛型
- 泛型函数：`identity<T>`。
- 泛型接口：`ApiResponse<T>`。
- 泛型约束：`T extends { id: string }`。
- `keyof` 与索引访问类型：实现安全的 `pick` 或 `getProperty`。
- 常用工具类型：`Partial`、`Required`、`Readonly`、`Pick`、`Omit`、`Record`。
- 练习：实现通用缓存、分页响应、对象字段选择函数。

### 07_classes — 类与访问修饰符
- 类、构造函数、实例属性、方法。
- `public`、`private`、`protected`、`readonly`。
- getter / setter。
- `implements` 接口。
- 继承与组合的取舍：教程中建议优先组合，继承只作基础演示。
- 练习：实现 `UserService`、`MemoryRepository<T>`。

### 08_modules_tooling — 模块化与工程配置
- ES Module 的 `import` / `export`。
- 解释 `module`、`moduleResolution`、`target`、`strict`、`rootDir`、`outDir`。
- 说明 `tsx`、`tsc --noEmit`、`tsc`、`node dist/...` 的区别。
- 简述 `.d.ts` 类型声明文件的作用。
- 说明从 JavaScript 迁移到 TypeScript 的基本策略。
- 练习：拆分模块并导出复用函数。

### 09_project_todo_cli — 综合实战：Todo CLI
- 实现一个命令行 Todo 管理器，数据可先保存在内存中，进阶可保存到 JSON 文件。
- 必须拆分模块：
  - `model.ts`：定义 `Todo`、`TodoStatus`、命令类型。
  - `store.ts`：实现增删改查。
  - `commands.ts`：解析命令并调用 store。
  - `index.ts`：入口文件。
- 支持命令：
  - `npm run todo -- add "learn typescript"`
  - `npm run todo -- list`
  - `npm run todo -- done <id>`
  - `npm run todo -- remove <id>`
- 实战重点：
  - 使用接口建模数据。
  - 使用联合类型建模命令。
  - 使用类型收窄处理不同命令。
  - 使用泛型或工具类型减少重复类型定义。

---

## 五、文档写作规范

- 所有文档使用中文。
- 每章结构建议保持一致：
  1. 本章目标
  2. 核心概念
  3. 可运行示例
  4. 常见错误
  5. 练习题
- 示例代码要短，但必须完整可运行。
- 对类型错误要给出“错误示例 + 正确写法 + 为什么”的解释。
- 不要只展示高级类型技巧，要优先解释初学者最常见的真实场景。
- 每章结尾提供 3~5 道练习，难度从简单标注类型到小型建模任务递进。
- 参考答案放到 `exercises/answers/`，不要和题目混在一起。

---

## 六、验收标准

后续 agent 完成教程项目后，必须满足：

- `npm install` 能成功安装依赖。
- `npm run check` 能通过类型检查。
- `npm run build` 能生成 `dist/`。
- `npm run dev` 能运行第一个示例。
- `npm run todo -- add "learn typescript"` 等 Todo CLI 命令能正常执行。
- `README.md` 中包含清晰的学习顺序、安装命令、运行命令。
- 每个 `docs/*.md` 都能对应至少一个 `src/*.ts` 示例。
- 所有示例和练习都避免无意义使用 `any`。

---

## 七、实现建议

- 优先创建最小可运行项目，再逐步补充章节内容。
- 每新增一章，立刻运行 `npm run check` 验证示例没有类型错误。
- 示例变量和业务场景尽量统一，例如用户、商品、订单、Todo，不要每章随机换领域。
- 对初学者不友好的高级主题，如条件类型、映射类型、模板字面量类型，可以放在附录或后续进阶教程，不作为入门主线。
- 如果需要压缩范围，优先保证基础类型、函数、对象建模、联合类型、泛型这五块内容完整。
