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

class UserService {
  public constructor(private readonly repository: Repository<User>) {}

  public register(name: string): User {
    const user: User = {
      id: `u_${Date.now()}`,
      name,
    };

    this.repository.create(user);
    return user;
  }

  public get total(): number {
    return this.repository.list().length;
  }
}

const repository = new MemoryRepository<User>();
const userService = new UserService(repository);

console.log(userService.register("Ada"));
console.log(userService.total);

export {};
