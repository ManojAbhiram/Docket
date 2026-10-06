import { z } from "zod";

import { ApiError, apiFetch } from "@/lib/api";

import { userSchema, type Credentials, type User } from "./schemas";

/** login starts a session. The API sets the session and anti-forgery cookies. */
export function login(credentials: Credentials): Promise<User> {
  return apiFetch("/api/auth/login", userSchema, {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

/** logout ends the session on the server. */
export function logout(): Promise<undefined> {
  return apiFetch("/api/auth/logout", z.undefined(), { method: "POST" });
}

/** fetchMe is the signed-in user, or null when there is no live session. */
export async function fetchMe(init: Pick<RequestInit, "signal"> = {}): Promise<User | null> {
  try {
    return await apiFetch("/api/auth/me", userSchema, init);
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return null;
    }
    throw error;
  }
}
