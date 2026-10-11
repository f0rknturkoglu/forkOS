import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { writeStored } from "@/core/storage";
import type { components } from "@/generated/api-schema";

type S = components["schemas"];
export type Experience = Omit<S["ExperienceOut"], "onboarding" | "feed"> & {
  onboarding: OnboardingState;
  feed: FeedPreferences;
};
export type OnboardingState = Required<S["OnboardingState"]>;
export type FeedPreferences = Required<Omit<S["FeedPreferences"], "bundles">> & { bundles: FeedBundle[] };
export type FeedBundle = Required<S["FeedBundle"]>;
export const EXPERIENCE_KEY = ["settings", "experience"];
export function useExperience() {
  return useQuery({
    queryKey: EXPERIENCE_KEY,
    queryFn: async () => {
      const data = await api.get<Experience>("/system/experience");
      if (
        !data ||
        typeof data.first_run !== "boolean" ||
        typeof data.revision !== "string" ||
        !data.onboarding ||
        !data.feed ||
        !Array.isArray(data.feed.providers) ||
        !Array.isArray(data.feed.bundles)
      )
        throw new Error("Başlangıç tercihleri okunamadı");
      return data;
    },
    staleTime: 60_000,
    retry: false,
  });
}
export function useSaveExperience() {
  const query = useExperience();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (change: { revision?: string; onboarding?: OnboardingState; feed?: FeedPreferences }) => {
      if (!query.data) throw new Error("Tercihler okunamadı; yeniden dene");
      return api.put<Experience>("/system/experience", { revision: query.data.revision, ...change });
    },
    onSuccess: (data) => {
      invalidateAfter("settings.write");
      client.setQueryData(EXPERIENCE_KEY, data);
      writeStored("experience.revision", data.revision);
    },
    onError: () => void query.refetch(),
  });
}
export function useRepairExperience() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (revision: string) => api.post<Experience>("/system/experience/repair", { revision }),
    onSuccess: (data) => {
      invalidateAfter("settings.write");
      client.setQueryData(EXPERIENCE_KEY, data);
      writeStored("experience.revision", data.revision);
    },
  });
}
export function openGuide() {
  window.dispatchEvent(new Event("forkos:guide"));
}
export function openSourceDiscovery() {
  window.dispatchEvent(new Event("forkos:feed-discovery"));
}
