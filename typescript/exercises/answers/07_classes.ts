interface Repository<T extends { id: string }> {
  create(value: T): void;
  list(): T[];
}

class MemoryRepository<T extends { id: string }> implements Repository<T> {
  private readonly records = new Map<string, T>();

  create(value: T): void {
    this.records.set(value.id, value);
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

  register(name: string): User {
    const user = { id: `u_${Date.now()}`, name };
    this.repository.create(user);
    return user;
  }

  get total(): number {
    return this.repository.list().length;
  }
}

const service = new UserService(new MemoryRepository<User>());
console.log(service.register("Ada"), service.total);

export {};
