// The JavaScript and Vue linting baseline for every Boreas project.
//
// Boreas owns this file. `linting/javascript/install.py` copies it to
// .boreas/eslint.config.mjs inside a project, and the project's own
// eslint.config.mjs imports the copy and spreads it first:
//
//     import boreas from "./.boreas/eslint.config.mjs";
//     export default [...boreas, { /* this project's rules */ }];
//
// The copy is overwritten on every install, so nothing here may be edited
// inside a project. Rules belonging to one project only go in its own file,
// after the spread, where they override what is here.
//
// The copy sits in .boreas/ rather than at the project root because ESLint 10
// reads the config file nearest each linted file. A root eslint.config.mjs is
// the project's whole configuration, so a copy there would leave no place for
// the project's own rules.
//
// No environment is set: no globals, and no sourceType for .js files. A Vue
// app runs in the browser as ES modules, a hook script runs in Node as
// CommonJS, and only the project knows which it is. install.py derives both
// from package.json when it writes a project's first eslint.config.mjs.

import { existsSync } from "node:fs";
import { join } from "node:path";

import { includeIgnoreFile } from "@eslint/compat";
import js from "@eslint/js";
import vue from "eslint-plugin-vue";

// Ruff and rumdl both skip what .gitignore names, and ESLint does not.
// Measured: without this, ESLint lints every copy of the code under a
// gitignored worktree directory.
const gitignore = join(import.meta.dirname, "..", ".gitignore");

const SOURCE = ["**/*.{js,mjs,cjs,vue}"];
const TESTS = ["**/*.{test,spec}.{js,mjs,cjs}", "**/tests/**", "**/__tests__/**"];

export default [
  ...(existsSync(gitignore) ? [includeIgnoreFile(gitignore)] : []),
  // Build output that atlas and meridian both ignored on their own.
  { ignores: ["**/dist/", "**/build/", "**/coverage/"] },

  js.configs.recommended,
  // Atlas and meridian each chose flat/recommended independently, which is
  // the evidence that it is not one project's preference.
  ...vue.configs["flat/recommended"],

  {
    files: SOURCE,
    rules: {
      // Size and shape limits (Sandi Metz style), the same thresholds the
      // Python baseline sets through C901, PLR0913, and PLR0915.
      complexity: ["error", 8],
      "max-params": ["error", 4],
      "max-statements": ["error", 8],

      // The ruff selections that have an ESLint equivalent. Measured against
      // atlas and meridian, these reported one finding between them.
      eqeqeq: ["error", "always", { null: "ignore" }], // B: a loose == hides a type bug
      "no-var": "error", // UP: modern syntax
      "prefer-const": "error", // UP: modern syntax
      "no-eval": "error", // S: security
      "no-implied-eval": "error", // S: security
      "no-new-func": "error", // S: security
      "no-else-return": ["error", { allowElseIf: false }], // RET505
    },
  },

  {
    // The one rule a test file is exempt from. A describe() callback holds
    // one statement per test case, so max-statements there counts cases, not
    // size. Measured: 17 of the 36 max-statements findings in atlas and
    // meridian test files were describe() callbacks. A long it() callback
    // loses its finding too, which is the accepted cost.
    files: TESTS,
    rules: { "max-statements": "off" },
  },
];
