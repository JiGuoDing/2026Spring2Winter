const examples = [
  "./01_getting_started",
  "./02_basic_types",
  "./03_functions",
  "./04_objects_interfaces",
  "./05_unions_narrowing",
  "./06_generics",
  "./07_classes",
  "./08_modules_tooling",
];

async function main(): Promise<void> {
  for (const example of examples) {
    await import(example);
  }
}

void main();
