# 07 类与访问修饰符

## 本章目标

- 掌握类、构造函数、实例方法。
- 理解 `public`、`private`、`protected`、`readonly`。
- 使用 `implements` 约束类必须实现某个接口。

## 核心概念

类可以封装状态和行为：

```ts
class UserService {
  public constructor(private readonly repository: Repository<User>) {}

  public register(name: string): User {
    const user = { id: `u_${Date.now()}`, name };
    this.repository.create(user);
    return user;
  }
}
```

访问修饰符用于控制成员的可见性：

- `public`：默认可见，类内外都能访问。
- `private`：只能在当前类内部访问。
- `protected`：当前类和子类内部可访问。
- `readonly`：初始化后不能重新赋值。

入门阶段要知道类的语法，但业务建模不一定都要用继承。多数场景下，组合比继承更容易维护。

## 可运行示例

对应文件：`src/07_classes.ts`

```bash
npm run example:07
```

也可以运行全部章节：

```bash
npm run example
```

本章输出会展示注册用户、通过仓储查询用户、通过 getter 读取统计信息。重点观察 `UserService` 如何通过构造函数接收 `Repository<User>`，而不是自己直接管理数据结构。

## 常见错误

错误示例：

```ts
class UserService {
  private repository: Repository<User>;
}

const service = new UserService();
console.log(service.repository);
```

`private` 成员只能在类内部访问。它适合隐藏实现细节。

## 练习题

1. 实现 `MemoryRepository<T>`。
2. 实现 `UserService.register`。
3. 给类增加只读配置项。
4. 使用 getter 暴露统计信息。
