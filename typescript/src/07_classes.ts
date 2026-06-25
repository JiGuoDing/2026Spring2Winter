import { printChapter, printStep, printTip, printValue } from "./example-utils";

interface Repository<T extends { id: string }> {
  create(value: T): void;
  findById(id: string): T | undefined;
  list(): T[];
}

class MemoryRepository<T extends { id: string }> implements Repository<T> {
  private readonly records = new Map<string, T>();

  create(value: T): void {
    this.records.set(value.id, value);
  }

  findById(id: string): T | undefined {
    return this.records.get(id);
  }

  list(): T[] {
    return [...this.records.values()];
  }
}

interface User {
  id: string;
  name: string;
}

let userSequence = 1;

class UserService {
  public constructor(private readonly repository: Repository<User>) {}

  public register(name: string): User {
    const user: User = {
      id: `u_${String(userSequence).padStart(3, "0")}`,
      name,
    };

    userSequence += 1;
    this.repository.create(user);
    return user;
  }

  public get total(): number {
    return this.repository.list().length;
  }
}

const repository = new MemoryRepository<User>();
const userService = new UserService(repository);

printChapter("07 类与访问修饰符");

printStep("创建服务并注册用户");
const ada = userService.register("Ada");
const grace = userService.register("Grace");
printValue("register(\"Ada\")", ada);
printValue("register(\"Grace\")", grace);

printStep("通过 Repository 查询数据");
printValue("findById(ada.id)", repository.findById(ada.id));
printValue("list()", repository.list());

printStep("getter 暴露只读统计信息");
printValue("userService.total", userService.total);
printTip("repository 是 private readonly，只能在 UserService 内部读取，外部通过方法和 getter 使用它。");

export {};
