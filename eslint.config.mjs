import globals from "globals";

import boreas from "./.boreas/eslint.config.mjs";

export default [
  ...boreas,
  // package.json declares no "type": "module", so Node runs .js files as CommonJS.
  { files: ["**/*.js"], languageOptions: { sourceType: "commonjs" } },
  // package.json does not depend on vue, so the code runs in Node.
  { languageOptions: { globals: globals.node } },
];
