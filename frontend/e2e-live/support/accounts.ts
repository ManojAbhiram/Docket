import { request } from "@playwright/test";

import { WEB_ORIGIN, type LiveAccount, type LiveRole } from "./stack";

/** Create an account through the real sign-up route, via the preview proxy like a browser. */
export async function registerAccount(role: LiveRole, account: LiveAccount): Promise<void> {
  const api = await request.newContext({
    baseURL: WEB_ORIGIN,
    extraHTTPHeaders: { Origin: WEB_ORIGIN },
  });
  try {
    const response = await api.post("/api/auth/register", {
      data: {
        username: account.username,
        display_name: account.displayName,
        password: account.password,
        role,
      },
    });
    if (response.status() !== 200) {
      const body = await response.text();
      throw new Error(`register ${account.username}: HTTP ${String(response.status())} ${body}`);
    }
  } finally {
    await api.dispose();
  }
}
