import { StandardAnswerCategory } from "@/lib/types";
import { fetchSS } from "@/lib/utilsSS";

export interface StandardAnswerCategoryResponse {
  error?: {
    message: string;
  };
  categories?: StandardAnswerCategory[];
}

/**
 * Renamed from `getStandardAnswerCategoriesIfEE`: standard answers are no longer an
 * Enterprise-gated feature, so there is no "if EE" any more. The old return type was a
 * discriminated union with a `paidEnterpriseFeaturesEnabled: false` variant that the
 * caller had to narrow on; that variant is now unreachable and is gone.
 */
export async function getStandardAnswerCategories(): Promise<StandardAnswerCategoryResponse> {
  const standardAnswerCategoriesResponse = await fetchSS(
    "/nexus/admin/standard-answer/category"
  );
  if (!standardAnswerCategoriesResponse.ok) {
    return {
      error: {
        message: await standardAnswerCategoriesResponse.text(),
      },
    };
  }

  const categories =
    (await standardAnswerCategoriesResponse.json()) as StandardAnswerCategory[];

  return { categories };
}
