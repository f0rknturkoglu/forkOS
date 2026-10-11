import { useRef, useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Plus, Check, ArrowUp, ArrowDown, Trash2 } from "lucide-react";
import { api } from "@/core/api";
import { Button, Checkbox, Field, Input, Modal, SkeletonRows, useToast } from "@/core/ui";
import { invalidateAfter } from "@/core/invalidation";
import { enabledModules } from "@/core/registry";
import { requestNavigation } from "@/core/navigationGuard";
import { navigate } from "@/app/router";
import { useOnline } from "@/lib/hooks";
import { SOURCE_CATALOG, PRESET_BUNDLES } from "./catalog";
import { useExperience, useSaveExperience, type FeedPreferences, type Experience, type FeedBundle } from "./experience";

type Feed = { id: string; title: string | null; url: string };
export function SourceDiscovery({
  onClose,
  onSaved,
  onboarding = false,
  onSkip,
  onBack,
}: {
  onClose: () => void;
  onSaved?: (value: Experience) => void;
  onboarding?: boolean;
  onSkip?: () => void;
  onBack?: () => void;
}) {
  const experience = useExperience();
  if (experience.isPending)
    return (
      <Modal open onClose={onClose} title="Kaynaklar">
        <SkeletonRows rows={3} />
      </Modal>
    );
  if (!experience.data || experience.isError)
    return (
      <Modal open onClose={onClose} title="Kaynaklar">
        <p role="alert">Tercihler okunamadı.</p>
        <Button onClick={() => void experience.refetch()}>Yeniden dene</Button>
      </Modal>
    );
  return (
    <SourceEditor
      initial={experience.data}
      onClose={onClose}
      onSaved={onSaved}
      onboarding={onboarding}
      onSkip={onSkip}
      onBack={onBack}
    />
  );
}
function SourceEditor({
  initial,
  onClose,
  onSaved,
  onboarding,
  onSkip,
  onBack,
}: {
  initial: Experience;
  onClose: () => void;
  onSaved?: (value: Experience) => void;
  onboarding: boolean;
  onSkip?: () => void;
  onBack?: () => void;
}) {
  const baseline = useRef(initial);
  const [draft, setDraft] = useState<FeedPreferences>(() => structuredClone(initial.feed));
  const [subredditText, setSubredditText] = useState(initial.feed.subreddits.join(", "));
  const [url, setUrl] = useState("");
  const [bundleTitle, setBundleTitle] = useState("");
  const [activeBundle, setActiveBundle] = useState<string | null>(null);
  const [error, setError] = useState("");
  const online = useOnline();
  const toast = useToast();
  const save = useSaveExperience();
  const feeds = useQuery({ queryKey: ["feeds"], queryFn: () => api.get<Feed[]>("/rss/feeds"), retry: false });
  const addFeed = useMutation({
    mutationFn: () => api.post<Feed>("/rss/feeds", { url: url.trim(), probe: false }),
    onSuccess: () => {
      invalidateAfter("rss.write");
      setUrl("");
      setDraft((value) => ({ ...value, rss_enabled: true }));
      toast.push("RSS aboneliği eklendi");
    },
    onError: (e) => setError(e.message),
  });
  const selected = (id: string) =>
    id === "rss" ? draft.rss_enabled : draft.providers.includes(id as FeedPreferences["providers"][number]);
  const toggle = (id: string) =>
    setDraft((value) =>
      id === "rss"
        ? { ...value, rss_enabled: !value.rss_enabled }
        : {
            ...value,
            providers: selected(id)
              ? value.providers.filter((provider) => provider !== id)
              : [...value.providers, id as FeedPreferences["providers"][number]],
          },
    );
  const changeBundle = (id: string, change: Partial<FeedBundle>) =>
    setDraft((value) => ({
      ...value,
      bundles: value.bundles.map((bundle) => (bundle.id === id ? { ...bundle, ...change } : bundle)),
    }));
  const addBundle = (title: string, channels: FeedBundle["channels"] = []) => {
    if (!title.trim() || draft.bundles.length >= 12) return;
    const id = crypto.randomUUID();
    setDraft((value) => ({
      ...value,
      providers: [
        ...new Set([
          ...value.providers,
          ...channels.filter((id): id is FeedPreferences["providers"][number] => id !== "rss"),
        ]),
      ],
      rss_enabled: value.rss_enabled || channels.includes("rss"),
      bundles: [...value.bundles, { id, title: title.trim().slice(0, 60), channels, feed_ids: [] }],
    }));
    setActiveBundle(id);
    setBundleTitle("");
  };
  const bundle = draft.bundles.find((item) => item.id === activeBundle);
  const commit = async () => {
    setError("");
    try {
      const data = await save.mutateAsync({
        revision: baseline.current.revision,
        feed: draft,
        ...(onboarding ||
        (baseline.current.onboarding.status === "in_progress" && baseline.current.onboarding.feed_setup === "pending")
          ? {
              onboarding: {
                ...baseline.current.onboarding,
                status: "in_progress",
                phase: onboarding ? "tour" : baseline.current.onboarding.phase,
                feed_setup: "chosen",
              },
            }
          : {}),
      });
      toast.push("Akış tercihleri kaydedildi");
      if (onSaved) onSaved(data);
      else onClose();
    } catch (e) {
      setError((e as Error).message);
    }
  };
  return (
    <Modal
      open
      onClose={onClose}
      title="Akışını oluştur"
      className="sm:max-w-3xl"
      footer={
        <div className="flex flex-wrap justify-end gap-2">
          {onBack && <Button onClick={onBack}>Geri</Button>}
          {onboarding ? (
            <Button onClick={onSkip}>Kaynakları şimdilik geç</Button>
          ) : (
            <Button onClick={onClose}>Vazgeç</Button>
          )}
          <Button variant="primary" disabled={!online || save.isPending} onClick={() => void commit()}>
            {save.isPending ? "Kaydediliyor…" : "Seçimleri kaydet"}
          </Button>
        </div>
      }
    >
      <div className="stack-y-5">
        <div className="grid gap-3 sm:grid-cols-2">
          {SOURCE_CATALOG.map((source) => {
            const Icon = source.icon;
            const checked = selected(source.id);
            return (
              <div key={source.id} className="rounded-card border border-subtle bg-surface p-4 stack-y-2">
                <div className="flex items-center gap-3">
                  <Icon size={22} className={source.skin} />
                  <h3 className="flex-1 text-heading">{source.title}</h3>
                  <button
                    type="button"
                    aria-label={`${source.title} ${checked ? "çıkar" : "ekle"}`}
                    aria-pressed={checked}
                    onClick={() => toggle(source.id)}
                    className="flex h-8 w-8 items-center justify-center rounded-control border border-subtle hover:bg-surface-hover"
                  >
                    {checked ? <Check size={16} className="text-accent" /> : <Plus size={16} />}
                  </button>
                </div>
                <p className="text-meta text-secondary">{source.description}</p>
                <p className="text-micro text-muted">{source.detail}</p>
              </div>
            );
          })}
        </div>
        {selected("reddit") && (
          <Field label="Subreddit'ler">
            <Input
              ariaLabel="Subreddit'ler"
              className="w-full"
              placeholder="programming, MachineLearning"
              value={subredditText}
              onChange={(value) => {
                setSubredditText(value);
                setDraft((old) => ({
                  ...old,
                  subreddits: value
                    .split(",")
                    .map((s) => s.trim().replace(/^r\//, ""))
                    .filter(Boolean),
                }));
              }}
            />
          </Field>
        )}
        <section className="stack-y-3">
          <h3 className="text-heading">RSS abonelikleri</h3>
          <div className="flex flex-wrap gap-2">
            <Input
              ariaLabel="RSS adresi"
              placeholder="https://…/feed.xml"
              className="min-w-0 flex-1"
              value={url}
              onChange={setUrl}
            />
            <Button disabled={!online || !url.trim() || addFeed.isPending} onClick={() => addFeed.mutate()}>
              RSS ekle
            </Button>
            <Button
              onClick={() => {
                const path = enabledModules().find((m) => m.id === "rss")?.routes[1]?.path;
                if (path && requestNavigation(path)) {
                  onClose();
                  navigate(path);
                }
              }}
            >
              OPML / abonelikler
            </Button>
          </div>
          <p className="text-meta text-muted">
            {feeds.isError ? "Abonelikler alınamadı" : `${feeds.data?.length ?? 0} mevcut abonelik`}
          </p>
        </section>
        <section className="stack-y-3">
          <h3 className="text-heading">Seçkilerim</h3>
          <div className="flex flex-wrap gap-2">
            {PRESET_BUNDLES.map((preset) => (
              <Button
                key={preset.title}
                disabled={draft.bundles.length >= 12}
                onClick={() => addBundle(preset.title, preset.channels)}
              >
                <Plus size={14} />
                {preset.title}
              </Button>
            ))}
          </div>
          <div className="flex gap-2">
            <Input
              ariaLabel="Yeni seçki adı"
              placeholder="Yeni seçki"
              className="min-w-0 flex-1"
              value={bundleTitle}
              onChange={setBundleTitle}
            />
            <Button disabled={!bundleTitle.trim() || draft.bundles.length >= 12} onClick={() => addBundle(bundleTitle)}>
              Oluştur
            </Button>
          </div>
          {draft.bundles.map((item, index) => (
            <div key={item.id} className="flex items-center gap-2">
              <Button onClick={() => setActiveBundle(item.id)} className="min-w-0 flex-1 justify-start">
                {item.title}
              </Button>
              <Button
                ariaLabel={`${item.title} yukarı`}
                disabled={index === 0}
                onClick={() =>
                  setDraft((value) => {
                    const bundles = [...value.bundles];
                    [bundles[index - 1], bundles[index]] = [bundles[index], bundles[index - 1]];
                    return { ...value, bundles };
                  })
                }
              >
                <ArrowUp size={14} />
              </Button>
              <Button
                ariaLabel={`${item.title} aşağı`}
                disabled={index === draft.bundles.length - 1}
                onClick={() =>
                  setDraft((value) => {
                    const bundles = [...value.bundles];
                    [bundles[index + 1], bundles[index]] = [bundles[index], bundles[index + 1]];
                    return { ...value, bundles };
                  })
                }
              >
                <ArrowDown size={14} />
              </Button>
              <Button
                ariaLabel={`${item.title} seçkisini sil`}
                onClick={() =>
                  setDraft((value) => ({ ...value, bundles: value.bundles.filter((b) => b.id !== item.id) }))
                }
              >
                <Trash2 size={14} />
              </Button>
            </div>
          ))}
          {bundle && (
            <div className="rounded-card border border-subtle p-3 stack-y-3">
              <Field label="Seçki adı">
                <Input
                  value={bundle.title}
                  onChange={(title) => changeBundle(bundle.id, { title: title.slice(0, 60) })}
                />
              </Field>
              <div className="flex flex-wrap gap-3">
                {SOURCE_CATALOG.map((source) => (
                  <Checkbox
                    key={source.id}
                    label={source.title}
                    checked={bundle.channels.includes(source.id)}
                    onChange={(checked) =>
                      changeBundle(bundle.id, {
                        channels: checked
                          ? [...bundle.channels, source.id]
                          : bundle.channels.filter((id) => id !== source.id),
                      })
                    }
                  />
                ))}
              </div>
              <div className="grid gap-2">
                {(feeds.data ?? []).map((feed) => (
                  <Checkbox
                    key={feed.id}
                    label={feed.title || feed.url}
                    checked={bundle.feed_ids.includes(feed.id)}
                    onChange={(checked) =>
                      changeBundle(bundle.id, {
                        feed_ids: checked
                          ? [...bundle.feed_ids, feed.id]
                          : bundle.feed_ids.filter((id) => id !== feed.id),
                      })
                    }
                  />
                ))}
              </div>
              <p className="text-micro text-muted">
                Seçki, yalnız takip ettiğin kaynakları gösterir. Seçkiyi silmek abonelikleri silmez.
              </p>
            </div>
          )}
        </section>
        {error && (
          <p role="alert" className="text-meta text-danger">
            {error}
            <Button onClick={onClose}>Güncel seçimleri yeniden aç</Button>
          </p>
        )}
      </div>
    </Modal>
  );
}
