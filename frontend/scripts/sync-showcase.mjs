import { cp, mkdir, stat } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = resolve(fileURLToPath(new URL("..", import.meta.url)));
const source = resolve(frontendRoot, "../artifacts/showcase");
const target = resolve(frontendRoot, "public/showcase");

async function isDirectory(path) {
  try {
    return (await stat(path)).isDirectory();
  } catch {
    return false;
  }
}

if (!(await isDirectory(source))) {
  if (await isDirectory(target)) {
    console.warn("Using the existing generated public/showcase bundle.");
    process.exit(0);
  }
  throw new Error(
    "No showcase bundle found. From the repository root run `midfielders-eye showcase-build`, then retry.",
  );
}

await mkdir(target, { recursive: true });
await cp(source, target, { recursive: true, force: true });
console.log(`Synchronized generated showcase data from ${source}`);
