import { describe, expect, it } from "vitest";

import { userWith } from "@/test/auth";

import { ApiError } from "./api";
import { createQueryClient } from "./query-client";

function retryOf(client: ReturnType<typeof createQueryClient>) {
  const retry = client.getDefaultOptions().queries?.retry;
  if (typeof retry !== "function") {
    throw new Error("retry should be a function");
  }
  return retry;
}

describe("createQueryClient", () => {
  it("never retries a 4xx", () => {
    const retry = retryOf(createQueryClient());
    expect(retry(0, new ApiError("http", 404, "GET /x: 404"))).toBe(false);
  });

  it("retries a 5xx or network error once", () => {
    const retry = retryOf(createQueryClient());
    expect(retry(0, new ApiError("http", 503, "GET /x: 503"))).toBe(true);
    expect(retry(1, new ApiError("network", 0, "GET /x: network error"))).toBe(false);
  });
});

describe("a session that ends", () => {
  async function failWith(
    client: ReturnType<typeof createQueryClient>,
    key: string[],
    status: number,
  ) {
    await client
      .query({
        queryKey: key,
        queryFn: () => Promise.reject(new ApiError("http", status, "GET /x")),
        retry: false,
      })
      .catch(() => undefined);
  }

  it("forgets who was signed in when any other request answers 401", async () => {
    const client = createQueryClient();
    client.setQueryData(["auth", "me"], userWith("staff"));

    await failWith(client, ["applications", "list"], 401);

    expect(client.getQueryData(["auth", "me"])).toBeNull();
  });

  it("keeps the user when the failure is not a 401", async () => {
    const client = createQueryClient();
    client.setQueryData(["auth", "me"], userWith("staff"));

    await failWith(client, ["applications", "list"], 500);

    expect(client.getQueryData(["auth", "me"])).toEqual(userWith("staff"));
  });

  it("leaves the session check alone, which answers 401 for a visitor", async () => {
    const client = createQueryClient();
    client.setQueryData(["auth", "me"], userWith("staff"));

    await failWith(client, ["auth", "me"], 401);

    expect(client.getQueryData(["auth", "me"])).toEqual(userWith("staff"));
  });
});
