import { useState } from "react";
import { Button, Checkbox, useToast } from "@/core/ui";
import { readStored, writeStored } from "@/core/storage";
import { useOnline } from "@/lib/hooks";
import { useExperience, useSaveExperience, type OnboardingState } from "./experience";

export function freshTutorial(state: OnboardingState): OnboardingState {
  return {
    ...state,
    status: "in_progress",
    phase: "welcome",
    journey: "general",
    active_tour: null,
    active_step: null,
    visited_steps: [],
    skipped_steps: [],
    dismissed_hints: [],
    feed_setup: "pending",
  };
}

/** Yalnız rehber ilerlemesini sıfırlar; içerik ve kaynak tercihleri korunur. */
export function TutorialTestMode() {
  const [enabled, setEnabled] = useState(() => readStored("tutorial.testMode.v1") === "true");
  const query = useExperience();
  const save = useSaveExperience();
  const online = useOnline();
  const toast = useToast();
  return (
    <div className="flex flex-wrap items-center gap-3 border-t border-subtle pt-3">
      <Checkbox
        label="Tutorial deneme modu"
        checked={enabled}
        onChange={(value) => {
          setEnabled(value);
          writeStored("tutorial.testMode.v1", String(value));
        }}
      />
      {enabled && (
        <Button
          size="sm"
          disabled={!online || !query.data || save.isPending}
          onClick={() => {
            if (!query.data) return;
            void save
              .mutateAsync({ onboarding: freshTutorial(query.data.onboarding) })
              .then(() => {
                window.dispatchEvent(new Event("forkos:tutorial-restart"));
              })
              .catch((error: Error) => toast.push(error.message || "Rehber sıfırlanamadı", { tone: "danger" }));
          }}
        >
          {save.isPending ? "Sıfırlanıyor…" : "Tutorialı sıfırdan başlat"}
        </Button>
      )}
    </div>
  );
}
