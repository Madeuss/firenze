import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  // The browser never talks to FastAPI. Everything goes through the route
  // handler in src/app/api, which is the only place that knows where the API
  // lives — and the place a session will go when T-11 is closed.
  env: {},
};

export default config;
