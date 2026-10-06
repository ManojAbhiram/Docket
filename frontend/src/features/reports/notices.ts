import type { NoticeSpec } from "@/components/Notice";
import { ApiError } from "@/lib/api";

const SIGNED_OUT: NoticeSpec = {
  tone: "info",
  title: "You were signed out.",
  body: "Sign in to continue.",
};

const OFFLINE: NoticeSpec = {
  tone: "info",
  title: "You are offline.",
  body: "Connect and try again.",
};

const UNAVAILABLE: NoticeSpec = {
  title: "Docket cannot reach its database.",
  body: "Try again in a minute.",
  action: "Try again",
};

/** What to tell the person when the dashboard counts did not load. */
export function dashboardNotice(error: unknown): NoticeSpec {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return SIGNED_OUT;
    }
    if (error.code === "network") {
      return OFFLINE;
    }
    if (error.status === 503) {
      return UNAVAILABLE;
    }
  }
  return {
    title: "The counts did not load.",
    body: "Reload the page, and tell the engineering team if it keeps happening.",
    action: "Reload",
  };
}

/** What to tell the person when the export did not finish. */
export function exportNotice(error: unknown): NoticeSpec {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return SIGNED_OUT;
    }
    if (error.status === 403) {
      return { title: "Only staff can export the verified list." };
    }
    if (error.code === "network") {
      return OFFLINE;
    }
    if (error.status === 503) {
      return UNAVAILABLE;
    }
  }
  return {
    title: "The export did not finish.",
    body: "Try again, and tell the engineering team if it keeps happening.",
    action: "Try again",
  };
}
