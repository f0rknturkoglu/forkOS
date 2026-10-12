import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { BookOpen, Check, ChevronLeft, ChevronRight, Play, X } from "lucide-react";
import { useHashRoute, navigate } from "@/app/router";
import { enabledModules, moduleForPath, titleForPath } from "@/core/registry";
import { requestNavigation } from "@/core/navigationGuard";
import { Button, Input, Modal, cx } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import { JOURNEYS, TOUR_IDS, helpForModule, pageNotes, tourSteps } from "./catalog";
import { useExperience, useSaveExperience, type OnboardingState, type Experience } from "./experience";
import { SourceDiscovery } from "./SourceDiscovery";

export function OnboardingHost() {
  const query = useExperience();
  const save = useSaveExperience();
  const route = useHashRoute();
  const [guide, setGuide] = useState(false);
  const [sources, setSources] = useState(false);
  const [tourOpen, setTourOpen] = useState(false);
  const [welcomeClosed, setWelcomeClosed] = useState(false);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const online = useOnline();
  const state = query.data?.onboarding;
  const tour = tourSteps(state?.active_tour || state?.journey || "general");
  const index = Math.max(
    0,
    tour.findIndex((step) => step.id === state?.active_step),
  );
  const step = tour[index];
  const inProgress = state?.status === "in_progress";
  const welcome =
    !welcomeClosed &&
    online &&
    !query.isError &&
    Boolean(query.data?.first_run || (inProgress && ["welcome", "journey", "sources"].includes(state?.phase ?? "")));
  const modal = guide || sources || welcome;
  const evidence = useQuery({
    queryKey: ["onboarding-evidence"],
    queryFn: async () => (await api.get<Experience>("/system/experience")).canonical_actions,
    enabled: Boolean(inProgress && ["tour", "checklist"].includes(state?.phase ?? "")),
    staleTime: 30_000,
    retry: false,
  });
  const actionDone = !step?.actionType || Boolean(evidence.data?.[step.actionType]);
  const module = moduleForPath(route.path);
  const title = titleForPath(route.path) || "forkOS";
  const [targetReady, setTargetReady] = useState(false);
  const panel = useRef<HTMLElement>(null);
  const requestedTarget = useRef<string | null>(null);
  const collapse = () => {
    setTourOpen(false);
    document.querySelector<HTMLElement>('[aria-label="Bu sayfa hakkında bilgi ve rehberler"]')?.focus();
  };
  useEffect(() => {
    const showGuide = () => {
      setGuide(true);
      setSearch("");
    };
    const showSources = () => setSources(true);
    const restart = () => {
      setWelcomeClosed(false);
      setGuide(false);
      setSources(false);
      setTourOpen(false);
      setError("");
    };
    const sync = (event: StorageEvent) => {
      if (event.key === "forkos.experience.revision") void query.refetch();
    };
    window.addEventListener("forkos:tutorial-restart", restart);
    window.addEventListener("forkos:guide", showGuide);
    window.addEventListener("forkos:feed-discovery", showSources);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("forkos:tutorial-restart", restart);
      window.removeEventListener("forkos:guide", showGuide);
      window.removeEventListener("forkos:feed-discovery", showSources);
      window.removeEventListener("storage", sync);
    };
  }, [query.refetch]);
  useEffect(() => {
    if (inProgress && state?.phase === "tour") setTourOpen(true);
  }, [inProgress, state?.phase]);
  useEffect(() => {
    if (inProgress && state?.phase === "checklist") void query.refetch();
  }, [route.path, inProgress, state?.phase]);
  useEffect(() => {
    if (!tourOpen || !step || modal) return;
    let marked: HTMLElement | null = null;
    const find = () => {
      marked?.removeAttribute("data-tour-active");
      const atStep = route.path === step.path.split("?")[0];
      marked = atStep ? document.querySelector<HTMLElement>(`[data-onboarding="${step.target}"]`) : null;
      setTargetReady(Boolean(marked));
      marked?.setAttribute("data-tour-active", "true");
      if (marked && requestedTarget.current === step.target) {
        requestedTarget.current = null;
        marked.scrollIntoView?.({ block: "center", behavior: "instant" });
        const control = marked.matches("button,a,input,select,textarea,[tabindex]")
          ? marked
          : marked.querySelector<HTMLElement>("button,a,input,select,textarea,[tabindex]");
        control?.focus();
      }
    };
    find();
    const observer = new MutationObserver((records) => {
      if (records.some((record) => record.type === "childList")) find();
    });
    observer.observe(document.getElementById("main-content") || document.body, { childList: true, subtree: true });
    return () => {
      observer.disconnect();
      marked?.removeAttribute("data-tour-active");
    };
  }, [tourOpen, step?.id, route.path, modal]);
  const update = async (patch: Partial<OnboardingState>) => {
    if (!state) return false;
    setError("");
    try {
      await save.mutateAsync({ onboarding: { ...state, ...patch } });
      return true;
    } catch (e) {
      setError((e as Error).message);
      return false;
    }
  };
  const go = (path: string) => {
    if (!requestNavigation(path)) {
      setError("Açık düzenlemeyi tamamladıktan sonra adıma gidebilirsin.");
      return false;
    }
    navigate(path);
    return true;
  };
  const start = async (id: string, journey: OnboardingState["journey"] = "general") => {
    const first = tourSteps(id)[0];
    if (!first) return;
    if (!requestNavigation(first.path)) {
      setError("Açık düzenlemeyi tamamladıktan sonra rehberi başlatabilirsin.");
      return;
    }
    if (await update({ status: "in_progress", phase: "tour", journey, active_tour: id, active_step: first.id })) {
      setGuide(false);
      setWelcomeClosed(true);
      setTourOpen(true);
      navigate(first.path);
    }
  };
  const advance = async (skip = false) => {
    if (!step || !state) return;
    const visited = !skip && targetReady ? [...new Set([...state.visited_steps, step.id])] : state.visited_steps;
    const skipped = skip ? [...new Set([...state.skipped_steps, step.id])] : state.skipped_steps;
    const next = tour[index + 1];
    if (next && !requestNavigation(next.path)) {
      setError("Açık düzenlemeyi tamamla; ilerlemen korunuyor.");
      return;
    }
    if (
      await update({
        visited_steps: visited,
        skipped_steps: skipped,
        phase: next ? "tour" : "checklist",
        active_step: next?.id ?? null,
      })
    ) {
      if (next) navigate(next.path);
    }
  };
  const selectJourney = async (journey: OnboardingState["journey"]) => {
    await update({
      status: "in_progress",
      phase: "sources",
      journey,
      active_tour: journey || "general",
      active_step: tourSteps(journey || "general")[0]?.id ?? null,
    });
  };
  const closeWelcome = async () => {
    if (await update({ status: "dismissed" })) setWelcomeClosed(true);
  };
  const isChecklist = inProgress && state?.phase === "checklist";
  const journeyType = { goal: "goal", planning: "todo", learning: "study_topic", career: "opportunity", general: "" }[
    state?.journey || "general"
  ];
  const canonicalDone = !journeyType || Boolean(evidence.data?.[journeyType]);
  const canonicalSkipped = Boolean(state?.journey && state.skipped_steps.includes(state.journey));
  const feedDone = state?.feed_setup !== "pending";
  const tours = TOUR_IDS.map((id) => ({ id, steps: tourSteps(id) }))
    .filter((item) => item.steps.length)
    .filter((item) =>
      (item.id === "general" ? "Genel tur" : item.steps[0].title + " " + item.steps[0].moduleTitle)
        .toLocaleLowerCase("tr-TR")
        .includes(search.toLocaleLowerCase("tr-TR")),
    );
  return (
    <>
      {welcome && state?.phase !== "sources" && (
        <Modal
          open
          onClose={() => void closeWelcome()}
          title={state?.phase === "journey" ? "Nereden başlayalım?" : "forkOS’a hoş geldin"}
          className="sm:max-w-2xl"
        >
          <div className="stack-y-5">
            {state?.phase === "journey" ? (
              <>
                <div className="grid gap-3 sm:grid-cols-2">
                  {JOURNEYS.filter((journey) => enabledModules().some((m) => m.id === journey.module)).map(
                    (journey) => {
                      const Icon = journey.icon;
                      return (
                        <button
                          key={journey.id}
                          type="button"
                          disabled={save.isPending}
                          onClick={() => void selectJourney(journey.id)}
                          className="flex items-center gap-3 rounded-card border border-subtle p-4 text-left text-heading hover:border-accent hover:bg-accent-surface"
                        >
                          <Icon size={22} className="text-accent" />
                          {journey.title}
                        </button>
                      );
                    },
                  )}
                </div>
                <div className="flex flex-wrap justify-between gap-2">
                  <Button disabled={save.isPending} onClick={() => void update({ phase: "welcome" })}>
                    <ChevronLeft size={14} />
                    Geri
                  </Button>
                  <Button disabled={save.isPending} onClick={() => void selectJourney("general")}>
                    Önce etrafı keşfet
                  </Button>
                </div>
              </>
            ) : (
              <>
                <div className="rounded-card bg-surface-sunken p-6 stack-y-3">
                  <span className="text-meta text-accent">Planla · Öğren · İlerle</span>
                  <h1 className="font-serif text-title">Kendi ritminde bir çalışma alanı.</h1>
                  <p className="max-w-lg text-body text-secondary">
                    Hedeflerini, projelerini ve öğrendiklerini bir araya getir.
                  </p>
                </div>
                <div className="flex flex-wrap justify-end gap-2">
                  <Button disabled={save.isPending} onClick={() => void closeWelcome()}>
                    Sonra keşfederim
                  </Button>
                  <Button
                    variant="primary"
                    disabled={save.isPending}
                    onClick={() => void update({ status: "in_progress", phase: "journey" })}
                  >
                    Başlayalım
                    <ChevronRight size={16} />
                  </Button>
                </div>
              </>
            )}
            {error && (
              <p role="alert" className="text-danger text-meta">
                {error}
              </p>
            )}
          </div>
        </Modal>
      )}
      {welcome && state?.phase === "sources" && (
        <SourceDiscovery
          onboarding
          onBack={() => void update({ phase: "journey" })}
          onSkip={async () => {
            if (await update({ phase: "tour", feed_setup: "skipped" })) {
              setWelcomeClosed(true);
              setTourOpen(true);
              if (tour[0]) go(tour[0].path);
            }
          }}
          onClose={() => void closeWelcome()}
          onSaved={() => {
            setWelcomeClosed(true);
            setTourOpen(true);
            if (tour[0]) go(tour[0].path);
          }}
        />
      )}
      {sources && !welcome && <SourceDiscovery onClose={() => setSources(false)} />}
      {guide && (
        <Modal open onClose={() => setGuide(false)} title={`${title} · Bilgi ve rehber`} className="sm:max-w-2xl">
          <div className="stack-y-4">
            <p className="text-body text-secondary">
              {module?.description || "Kayıtlarını, planını ve kaynaklarını tek çalışma alanında yönet."}
            </p>
            {module &&
              pageNotes(module.id).map((text) => (
                <p key={text} className="text-meta text-secondary">
                  {text}
                </p>
              ))}
            {module &&
              helpForModule(module.id).map((item) => (
                <div key={item.id}>
                  <h3 className="text-heading">{item.title}</h3>
                  <p className="mt-1 text-meta text-secondary">{item.text}</p>
                </div>
              ))}
            <div className="border-t border-subtle pt-4 stack-y-3">
              <Input
                ariaLabel="Rehber ara"
                placeholder="Rehber ara…"
                className="w-full"
                value={search}
                onChange={setSearch}
              />
              <div className="grid gap-2 sm:grid-cols-2">
                {tours.map((item) => (
                  <Button
                    key={item.id}
                    disabled={!online || !query.data || save.isPending}
                    onClick={() =>
                      void start(item.id, JOURNEYS.find((journey) => journey.id === item.id)?.id || "general")
                    }
                  >
                    <Play size={14} />
                    {item.id === "general"
                      ? "Genel tur"
                      : item.id === "rss" || item.id === "feed"
                        ? item.steps[0].title
                        : item.steps[0].moduleTitle}
                  </Button>
                ))}
              </div>
              {!tours.length && <p className="text-meta text-muted">Rehber bulunamadı.</p>}
              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={() => {
                    setGuide(false);
                    setSources(true);
                  }}
                >
                  Akış kaynaklarını seç
                </Button>
                <Button
                  disabled={!online || save.isPending}
                  onClick={async () => {
                    if (
                      await update({ status: "in_progress", phase: "journey", active_step: null, active_tour: null })
                    ) {
                      setGuide(false);
                      setWelcomeClosed(false);
                    }
                  }}
                >
                  Başlangıcı yeniden aç
                </Button>
              </div>
            </div>
            {query.isError && (
              <p role="alert">
                Rehber tercihi alınamadı. <Button onClick={() => void query.refetch()}>Yeniden dene</Button>
              </p>
            )}
            {(query.data?.warnings ?? []).map((warning) => (
              <p key={warning} role="status" className="text-meta text-warn">
                {warning}
              </p>
            ))}
            {error && (
              <p role="alert" className="text-meta text-danger">
                {error}
              </p>
            )}
          </div>
        </Modal>
      )}
      {inProgress &&
        ["tour", "checklist"].includes(state?.phase ?? "") &&
        !modal &&
        (tourOpen ? (
          <aside
            ref={panel}
            aria-label="Başlangıç rehberi"
            tabIndex={-1}
            className="fixed bottom-3 right-3 z-popover w-[min(24rem,calc(100vw-1.5rem))] max-h-[60vh] overflow-y-auto rounded-overlay border border-strong bg-surface p-4 shadow-overlay stack-y-3"
            onKeyDown={(event) => {
              if ((event.target as HTMLElement).matches("input,textarea,select")) return;
              if (event.key === "Escape") {
                event.stopPropagation();
                collapse();
              }
            }}
          >
            <div className="flex items-center gap-2">
              <BookOpen size={15} className="text-accent" />
              <span className="flex-1 text-meta text-secondary">
                {isChecklist ? "Başlangıcın" : `${index + 1} / ${tour.length} · Rehber`}
              </span>
              <Button size="sm" ariaLabel="Rehberi küçült" onClick={collapse}>
                <X size={14} />
              </Button>
            </div>
            {isChecklist ? (
              <>
                <h2 className="text-heading">İlk adımlar</h2>
                <div className="stack-y-3">
                  <ChecklistItem
                    done={Boolean(state?.visited_steps.length)}
                    skipped={Boolean(!state?.visited_steps.length && state?.skipped_steps.length)}
                    title="Çalışma alanı keşfi"
                  />
                  <ChecklistItem
                    done={state?.feed_setup === "chosen"}
                    skipped={state?.feed_setup === "skipped"}
                    title="Kaynak seçimi"
                  />
                  <ChecklistItem
                    done={canonicalDone}
                    skipped={!canonicalDone && canonicalSkipped}
                    title={journeyType ? "Kanonik kayıt" : "Çalışma alanın hazır"}
                  />
                </div>
                {!canonicalDone && (
                  <Button
                    onClick={() => {
                      const first = tourSteps(state?.journey || "general")[0];
                      if (first) go(first.path);
                    }}
                  >
                    Çalışma alanına git
                  </Button>
                )}
                {!feedDone && (
                  <div className="flex gap-2">
                    <Button onClick={() => setSources(true)}>Kaynak seç</Button>
                    <Button disabled={save.isPending} onClick={() => void update({ feed_setup: "skipped" })}>
                      Şimdilik geç
                    </Button>
                  </div>
                )}
                <div className="flex gap-2">
                  <Button disabled={!online || save.isPending} onClick={() => void query.refetch()}>
                    İlerlemeyi kontrol et
                  </Button>
                  <Button
                    variant="primary"
                    disabled={
                      !online ||
                      save.isPending ||
                      (!canonicalDone && !canonicalSkipped) ||
                      !feedDone ||
                      !(state?.visited_steps.length || state?.skipped_steps.length)
                    }
                    onClick={async () => {
                      if (await update({ status: "completed" })) setTourOpen(false);
                    }}
                  >
                    Tamamla
                  </Button>
                </div>
                <Button variant="ghost" disabled={save.isPending} onClick={() => void update({ status: "dismissed" })}>
                  Sonra devam ederim
                </Button>
              </>
            ) : step ? (
              <>
                <h2 className="text-heading">{step.title}</h2>
                <p className="text-body text-secondary">{step.text}</p>
                <p className={cx("text-meta", step.actionType && actionDone ? "text-ok" : "text-muted")}>
                  {step.actionType
                    ? evidence.isError
                      ? "Kayıt kontrolü alınamadı"
                      : actionDone
                        ? "Mevcut kayıt doğrulandı"
                        : "Kayıt bekleniyor"
                    : "Keşif adımı"}
                </p>
                {step.actionType && !actionDone && (
                  <Button size="sm" disabled={evidence.isFetching} onClick={() => void evidence.refetch()}>
                    Kaydı kontrol et
                  </Button>
                )}
                {!targetReady && (
                  <p role="status" className="text-meta text-muted">
                    {route.path === step.path.split("?")[0]
                      ? "Bu görünümde adımın kontrolü bulunamadı; sayfadan ilerleyebilir veya adımı geçebilirsin."
                      : "Adım başka bir çalışma alanında."}
                  </p>
                )}
                <div className="flex flex-wrap gap-2">
                  <Button
                    disabled={!online || save.isPending}
                    onClick={() => {
                      requestedTarget.current = step.target;
                      if (go(step.path)) {
                        const target = document.querySelector<HTMLElement>(`[data-onboarding="${step.target}"]`);
                        if (target) {
                          requestedTarget.current = null;
                          target.scrollIntoView?.({ block: "center", behavior: "instant" });
                          (target.matches("button,a,input,select,textarea,[tabindex]")
                            ? target
                            : target.querySelector<HTMLElement>("button,a,input,select,textarea,[tabindex]")
                          )?.focus();
                        }
                      } else requestedTarget.current = null;
                    }}
                  >
                    Adıma git
                  </Button>
                  {index > 0 && (
                    <Button
                      disabled={!online || save.isPending}
                      onClick={async () => {
                        const previous = tour[index - 1];
                        if (requestNavigation(previous.path) && (await update({ active_step: previous.id })))
                          navigate(previous.path);
                      }}
                    >
                      <ChevronLeft size={14} />
                      Geri
                    </Button>
                  )}
                  <Button disabled={!online || save.isPending} onClick={() => void advance(true)}>
                    Geç
                  </Button>
                  <Button
                    variant="primary"
                    disabled={!online || save.isPending || !targetReady || !actionDone}
                    onClick={() => void advance()}
                  >
                    {index === tour.length - 1 ? "İlk adımlar" : "Sonraki"}
                    <ChevronRight size={14} />
                  </Button>
                </div>
              </>
            ) : (
              <>
                <p>Bu rehberin modülü kapalı.</p>
                <Button onClick={() => setGuide(true)}>Başka rehber seç</Button>
              </>
            )}
            {error && (
              <p role="alert" className="text-meta text-danger">
                {error}
              </p>
            )}
          </aside>
        ) : (
          <div className="fixed bottom-20 right-5 z-popover">
            <button
              type="button"
              aria-label="Rehbere devam et"
              title="Rehbere devam et"
              onClick={() => setTourOpen(true)}
              className="flex h-11 w-11 items-center justify-center rounded-full border border-strong bg-surface text-primary shadow-overlay transition hover:bg-surface-hover"
            >
              <BookOpen size={18} />
            </button>
          </div>
        ))}
    </>
  );
}
function ChecklistItem({ done, skipped = false, title }: { done: boolean; skipped?: boolean; title: string }) {
  return (
    <p className={cx("flex items-center gap-2 text-body", done ? "text-ok" : "text-secondary")}>
      <span className="flex h-5 w-5 items-center justify-center rounded-full border border-subtle">
        {done && <Check size={12} />}
      </span>
      {title}
      {skipped && <span className="text-meta text-muted">· Geçildi</span>}
    </p>
  );
}
