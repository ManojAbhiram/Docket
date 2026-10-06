import type { NoticeSpec } from "@/components/Notice";
import { ApiError } from "@/lib/api";

/**
 * What to tell a verifier when a decision did not go through. A 409 is either a stale page or an
 * application that left review, and only the fresh status tells them apart, so the caller passes
 * the status it found after reloading the application.
 */
export function decisionNotice(error: unknown, statusAfterReload?: string): NoticeSpec {
  if (error instanceof ApiError) {
    if (error.status === 409 && error.serverCode === "verification_not_allowed") {
      return {
        title: "This application cannot be approved yet.",
        body: "A required document is missing or a field has not been checked. Open the documents, then try again.",
      };
    }
    if (error.status === 409) {
      return statusAfterReload !== undefined && statusAfterReload !== "needs_review"
        ? {
            title: "This application is no longer in review.",
            body: "Someone else decided it. The latest version is now shown.",
          }
        : {
            title: "This application changed while you were looking at it.",
            body: "The latest version is now shown. Check it, then decide again.",
          };
    }
    if (error.status === 403) {
      return { title: "Only a verifier can decide.", body: "Sign in as a verifier to continue." };
    }
    if (error.status === 422) {
      return { title: "The decision was not accepted.", body: "Check the fields and try again." };
    }
    if (error.code === "network") {
      return { tone: "info", title: "You are offline.", body: "Connect and save again." };
    }
  }
  return { title: "The decision was not saved.", body: "Try again in a minute." };
}
