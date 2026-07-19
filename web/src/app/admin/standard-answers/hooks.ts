import { errorHandlingFetcher } from "@/lib/fetcher";
import { StandardAnswer, StandardAnswerCategory } from "@/lib/types";
import useSWR, { mutate } from "swr";
import { StandardAnswerConfig } from "./lib";

const ANSWERS_URL = "/api/nexus/admin/standard-answer";
const CATEGORIES_URL = "/api/nexus/admin/standard-answer/category";
const CONFIG_URL = "/api/nexus/admin/standard-answer/config";

export const useStandardAnswers = () => {
  const swr = useSWR<StandardAnswer[]>(ANSWERS_URL, errorHandlingFetcher);
  return { ...swr, refreshStandardAnswers: () => mutate(ANSWERS_URL) };
};

export const useStandardAnswerCategories = () => {
  const swr = useSWR<StandardAnswerCategory[]>(
    CATEGORIES_URL,
    errorHandlingFetcher
  );
  return {
    ...swr,
    refreshStandardAnswerCategories: () => mutate(CATEGORIES_URL),
  };
};

export const useStandardAnswerConfig = () => {
  const swr = useSWR<StandardAnswerConfig>(CONFIG_URL, errorHandlingFetcher);
  return { ...swr, refreshStandardAnswerConfig: () => mutate(CONFIG_URL) };
};
