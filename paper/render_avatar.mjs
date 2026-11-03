// Bundle repository TypeScript against the existing locked frontend dependencies.
import { createRequire } from "node:module";
import { mkdirSync, rmSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(resolve(root, "frontend/package.json"));
const { buildSync } = require("esbuild");
const cache = resolve(root, "paper/.cache");
mkdirSync(cache, { recursive: true });
const output = resolve(cache, `renderer-${process.pid}.mjs`);
try {
  buildSync({ entryPoints: [resolve(root, "paper/render_avatar.ts")], outfile: output, bundle: true, platform: "node", format: "esm", nodePaths: [resolve(root, "frontend/node_modules")] });
  await import(pathToFileURL(output).href);
} finally { rmSync(output, { force: true }); }
