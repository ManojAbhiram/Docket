import { z } from "zod";

import type { DashboardCounts } from "@/features/applications/types";

export type { DashboardCounts };

/** The API's counts, renamed the way the screens say them. `needs_review` includes the rejected. */
export const dashboardSchema = z
  .object({
    verified: z.number().int().min(0),
    needs_review: z.number().int().min(0),
    missing_documents: z.number().int().min(0),
    rejected: z.number().int().min(0),
  })
  .transform((counts): DashboardCounts => ({
    verified: counts.verified,
    needsReview: counts.needs_review,
    missingDocuments: counts.missing_documents,
    rejected: counts.rejected,
  }));
