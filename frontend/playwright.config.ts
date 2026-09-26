import { defineConfig, devices } from "@playwright/test";

const BACKEND_PORT = 8001;
const FRONT_PORT = 4174;

export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  expect: { timeout: 15_000 },
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${FRONT_PORT}`,
    trace: "retain-on-failure",
    launchOptions: process.env.PW_CHROMIUM_PATH ? { executablePath: process.env.PW_CHROMIUM_PATH } : {},
  },
  projects: [{ name: "mobile", use: { ...devices["Pixel 5"] } }],
  webServer: [
    {
      command: `E2E_BACKEND_PORT=${BACKEND_PORT} bash ../scripts/e2e-backend.sh`,
      url: `http://127.0.0.1:${BACKEND_PORT}/api/health/`,
      timeout: 180_000,
      reuseExistingServer: false,
    },
    {
      command: `npx vite build && BACKEND_URL=http://127.0.0.1:${BACKEND_PORT} npx vite preview --port ${FRONT_PORT} --strictPort`,
      url: `http://127.0.0.1:${FRONT_PORT}`,
      timeout: 180_000,
      reuseExistingServer: false,
    },
  ],
});
