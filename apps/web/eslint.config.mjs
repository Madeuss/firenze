import next from "eslint-config-next";
import nextTypescript from "eslint-config-next/typescript";

const config = [
  { ignores: [".next/**", "node_modules/**", "src/lib/contracts.ts"] },
  ...next,
  ...nextTypescript,
];

export default config;
