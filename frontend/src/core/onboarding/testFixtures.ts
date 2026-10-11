import type { Experience } from "./experience";
// Shared explicit choices: fixture consent is never inferred from mocked empty settings.
export function experienceFixture(
  providers: Experience["feed"]["providers"] = ["hn", "gh", "reddit"],
  rss = true,
): Experience {
  return {
    version: 1,
    revision: "a".repeat(64),
    first_run: false,
    counts: {},
    canonical_actions: {},
    invalid_feed_ids: [],
    warnings: [],
    updated_at: null,
    onboarding: {
      version: 1,
      status: "dismissed",
      phase: "welcome",
      journey: null,
      active_tour: null,
      active_step: null,
      visited_steps: [],
      skipped_steps: [],
      dismissed_hints: [],
      feed_setup: "pending",
    },
    feed: { providers, rss_enabled: rss, subreddits: ["programming"], bundles: [] },
  };
}
