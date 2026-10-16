import path from "node:path";

// One place for the ports and paths of the live stack (NOTASK-31). They avoid the dev
// ports (5432, 8080, 5173) and the mocked suite's 4173, so both suites can run side by side.
export const WEB_PORT = 4273;
export const API_PORT = 8090;
export const DB_PORT = 55432;

// `localhost`, not 127.0.0.1: the browser's Origin header must equal an entry of the API's
// ALLOWED_ORIGINS string exactly.
export const WEB_ORIGIN = `http://localhost:${String(WEB_PORT)}`;
export const API_ORIGIN = `http://127.0.0.1:${String(API_PORT)}`;
export const DATABASE_URL = `postgresql+asyncpg://postgres:postgres@localhost:${String(DB_PORT)}/docket`;

export const REPO_ROOT = path.resolve(import.meta.dirname, "..", "..", "..");
export const SEED_DIR = path.join(REPO_ROOT, ".scratch", "e2e-live", "seed");

// The password rules: 8+ characters, a capital, a special character, not the username.
export const PASSWORD = "Correct!Pass1";

export type LiveRole = "staff" | "verifier";

export interface LiveAccount {
  username: string;
  displayName: string;
  password: string;
}

export interface LiveAccounts {
  staff: LiveAccount;
  verifier: LiveAccount;
}

const ACCOUNTS_ENV = "LIVE_E2E_ACCOUNTS";

/** Accounts made by global setup, handed to the workers through the environment. */
export function setAccounts(accounts: LiveAccounts): void {
  process.env[ACCOUNTS_ENV] = JSON.stringify(accounts);
}

export function getAccounts(): LiveAccounts {
  const raw = process.env[ACCOUNTS_ENV];
  if (!raw) {
    throw new Error("global setup did not create the live accounts");
  }
  return JSON.parse(raw) as LiveAccounts;
}
