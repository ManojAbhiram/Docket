import type { NoticeSpec } from "@/components/Notice";
import { ApiError } from "@/lib/api";

export interface SignInOutcome {
  notice: NoticeSpec;
  /** Seconds the button stays off, when the server asked for a wait. */
  blockedFor?: number;
}

function rateLimited(error: ApiError): SignInOutcome {
  const seconds = error.retryAfter ?? 60;
  return {
    notice: { title: "Too many attempts.", body: `Try again in ${String(seconds)} seconds.` },
    blockedFor: seconds,
  };
}

/** What to tell the person when creating an account did not work. */
export function registerOutcome(error: unknown): SignInOutcome {
  if (error instanceof ApiError) {
    if (error.status === 409) {
      return { notice: { title: "That username is taken.", body: "Choose another." } };
    }
    if (error.status === 422) {
      return {
        notice: {
          title: "Check the form.",
          body: "Use 3 or more letters, digits, dots, dashes or underscores for the username, and at least 10 characters for the password.",
        },
      };
    }
    if (error.status === 429) {
      return rateLimited(error);
    }
    if (error.code === "network") {
      return {
        notice: { tone: "info", title: "You are offline.", body: "Connect and try again." },
      };
    }
  }
  return {
    notice: { title: "Docket cannot reach its server.", body: "Try again in a minute." },
  };
}

/** What to tell the person when a sign-in did not work, and whether to make them wait. */
export function signInOutcome(error: unknown): SignInOutcome {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return {
        notice: {
          title: "That username and password do not match.",
          body: "Check them and try again.",
        },
      };
    }
    if (error.status === 429) {
      return rateLimited(error);
    }
    if (error.code === "network") {
      return {
        notice: { tone: "info", title: "You are offline.", body: "Connect and try again." },
      };
    }
  }
  return {
    notice: { title: "Docket cannot reach its server.", body: "Try again in a minute." },
  };
}
