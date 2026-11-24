import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import ts from 'typescript';

const require = createRequire(import.meta.url);

// Exercise the actual small transport/store modules with controlled browser edges.
// TypeScript is already a build dependency; the Node runner needs no new packages.
export function loadTypeScript(relativePath, overrides = {}) {
  const source = readFileSync(new URL(`../${relativePath}`, import.meta.url), 'utf8');
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const module = { exports: {} };
  const resolve = (name) => Object.hasOwn(overrides, name) ? overrides[name] : require(name);
  new Function('require', 'exports', 'module', compiled)(resolve, module.exports, module);
  return module.exports;
}
