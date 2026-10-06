import type { NoticeSpec } from "@/components/Notice";
import { ApiError } from "@/lib/api";

/** What went wrong with an import, and the next step. No cell value is ever part of it. */
export function importNotice(error: unknown): NoticeSpec {
  if (error instanceof ApiError) {
    if (error.status === 413) {
      return {
        title: "That file is too large.",
        body: "Split it into smaller files and import them one at a time.",
      };
    }
    if (error.status === 415) {
      return { title: "That is not a CSV file.", body: "Choose a .csv file and try again." };
    }
    if (error.status === 422) {
      return {
        title: "That file cannot be read.",
        body: "Check that it is UTF-8 text with every required column, then try again.",
      };
    }
    if (error.status === 403) {
      return { title: "Only staff can import applications." };
    }
    if (error.code === "network") {
      return { tone: "info", title: "You are offline.", body: "Connect and try again." };
    }
  }
  return {
    title: "The import did not finish.",
    body: "Check the applications list before you import again. Rows already created are skipped.",
  };
}
