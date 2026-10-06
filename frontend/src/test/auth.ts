import { http, HttpResponse } from "msw";

import type { Role, User } from "@/features/auth/schemas";
import { server } from "@/test/msw";

export function userWith(role: Role): User {
  return {
    id: "0192b1c0-aaaa-7c4e-9a1b-2c3d4e5f6a7b",
    display_name: role === "verifier" ? "Demo Verifier" : "Demo Staff",
    role,
  };
}

/**
 * A fake session: `/auth/me` answers 401 until a sign-in succeeds, and answers 401 again after
 * a sign-out. `startAs` begins already signed in. Returns the requests the app made.
 */
export function fakeSession(options: { startAs?: Role; loginAs?: Role } = {}) {
  let current: User | null = options.startAs ? userWith(options.startAs) : null;
  const calls: string[] = [];
  server.use(
    http.get("*/api/auth/me", () => {
      calls.push("me");
      return current
        ? HttpResponse.json(current)
        : HttpResponse.json(
            { error: { code: "unauthorized", message: "sign in" } },
            { status: 401 },
          );
    }),
    http.post("*/api/auth/login", () => {
      calls.push("login");
      current = userWith(options.loginAs ?? "staff");
      return HttpResponse.json(current);
    }),
    http.post("*/api/auth/logout", () => {
      calls.push("logout");
      current = null;
      return new HttpResponse(null, { status: 204 });
    }),
  );
  return { calls };
}
