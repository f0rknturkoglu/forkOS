import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Check, Plus, Trash2, X } from "lucide-react";
import { api } from "@/core/api";
import { confirmDialog } from "@/core/dialog";
import { invalidateAfter } from "@/core/invalidation";
import {
  Button,
  Checkbox,
  Chip,
  Empty,
  Field,
  IconButton,
  Input,
  Modal,
  NumberInput,
  Section,
  Select,
  Tabs,
  useToast,
} from "@/core/ui";

interface JobhunterConfig {
  scoring: Record<string, unknown>;
  balance: Record<string, unknown>;
}

interface LinkedProfile {
  term: string;
  location?: string;
  results_wanted?: number;
  hours_old?: number;
  is_remote?: boolean;
  fetch_description?: boolean;
}

interface CareerProfile {
  current_location: string;
  authorized_countries: string[];
  willing_to_relocate: boolean;
  preferred_work_mode?: string;
}

interface SkillRow {
  name: string;
  points: number;
  aliases: string;
}

/** Basit/Advanced sayısal alanlar; etiket kullanıcıya doğrudan görünür. */
const WEIGHT_FIELDS: { key: string; label: string; group: "weights" | "penalties" | "freshness" }[] = [
  { key: "base", label: "Temel puan", group: "weights" },
  { key: "skill_max", label: "Yetenek tavanı", group: "weights" },
  { key: "skill_title_multiplier", label: "Başlık çarpanı", group: "weights" },
  { key: "level_bonus", label: "Seviye bonusu", group: "weights" },
  { key: "kill_score", label: "Elendi skoru", group: "weights" },
  { key: "score_cap", label: "Skor tavanı", group: "weights" },
  { key: "score_floor", label: "Skor tabanı", group: "weights" },
  { key: "visa_bonus", label: "Sponsorluk bonusu", group: "penalties" },
  { key: "visa_penalty", label: "Sponsorluk cezası", group: "penalties" },
  { key: "role_mismatch_penalty", label: "Rol uyumsuzluğu cezası", group: "penalties" },
  { key: "tr_relocation_penalty", label: "Taşınma cezası", group: "penalties" },
  { key: "freshness_grace_days", label: "Tazelik hoşgörü (gün)", group: "freshness" },
  { key: "freshness_penalty_per_day", label: "Günlük tazelik cezası", group: "freshness" },
  { key: "freshness_max_penalty", label: "Tazelik ceza tavanı", group: "freshness" },
];

const WORK_MODES = [
  ["", "Belirtilmemiş"],
  ["remote", "Uzaktan"],
  ["hybrid", "Hibrit"],
  ["onsite", "Ofisten"],
] as const;

function asStringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function asNumber(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function TokenListField({
  label,
  values,
  onChange,
  placeholder,
}: {
  label: string;
  values: string[];
  onChange: (next: string[]) => void;
  placeholder: string;
}) {
  const [draft, setDraft] = useState("");
  function add() {
    const value = draft.trim();
    if (!value || values.includes(value)) {
      setDraft("");
      return;
    }
    onChange([...values, value]);
    setDraft("");
  }
  return (
    <Field label={label}>
      <div className="flex flex-wrap items-center gap-1">
        {values.map((value) => (
          <span key={value} className="flex items-center gap-1">
            <Chip>{value}</Chip>
            <IconButton title={`${value} kaldır`} onClick={() => onChange(values.filter((item) => item !== value))}>
              <X size={11} />
            </IconButton>
          </span>
        ))}
      </div>
      <div className="mt-2 flex items-center gap-2">
        <Input
          value={draft}
          onChange={setDraft}
          placeholder={placeholder}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              add();
            }
          }}
          className="w-full"
        />
        <Button size="sm" onClick={add}>
          <Plus size={12} /> Ekle
        </Button>
      </div>
    </Field>
  );
}

/** Jobhunter ayar çarkı: uyum profili, LinkedIn profilleri, ortam, veri temizliği.
 *  `onClose` verilirse modal katmanında, verilmezse çalışma alanı sekmesinde
 *  gömülü olarak çizilir. */
export function JobhunterSettings({ onClose }: { onClose?: () => void }) {
  const toast = useToast();
  const [section, setSection] = useState<"profile" | "linkedin" | "env" | "maintenance">("profile");

  const { data: config } = useQuery({
    queryKey: ["jobhunter-config"],
    queryFn: () => api.get<JobhunterConfig>("/sources/jobhunter/config"),
  });
  const profilesQuery = useQuery({
    queryKey: ["jobhunter-linkedin"],
    queryFn: () => api.get<LinkedProfile[]>("/sources/jobhunter/linkedin-profiles"),
  });
  const profiles = profilesQuery.data ?? [];
  const { data: env } = useQuery({
    queryKey: ["jobhunter-env"],
    queryFn: () => api.get<{ linkein_allow_direct: string; proxies_file: string }>("/sources/jobhunter/env"),
  });
  const { data: settings } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.get<Record<string, unknown>>("/settings"),
  });

  /* ── Uyum profili formu ── */
  const [weights, setWeights] = useState<Record<string, number>>({});
  const [skills, setSkills] = useState<SkillRow[]>([]);
  const [roleTerms, setRoleTerms] = useState<string[]>([]);
  const [killWords, setKillWords] = useState<string[]>([]);
  const [currentLocation, setCurrentLocation] = useState("");
  const [authorizedCountries, setAuthorizedCountries] = useState<string[]>([]);
  const [willingToRelocate, setWillingToRelocate] = useState(false);
  const [workMode, setWorkMode] = useState("");

  useEffect(() => {
    if (!config) return;
    const scoring = config.scoring;
    const nextWeights: Record<string, number> = {};
    for (const { key } of WEIGHT_FIELDS) nextWeights[key] = asNumber(scoring[key], 0);
    setWeights(nextWeights);
    const rawSkills = Array.isArray(scoring.skills) ? (scoring.skills as Record<string, unknown>[]) : [];
    setSkills(
      rawSkills.map((item) => ({
        name: typeof item.name === "string" ? item.name : "",
        points: asNumber(item.points, 0),
        aliases: asStringList(item.aliases).join(", "),
      })),
    );
    setRoleTerms(asStringList(scoring.role_terms));
    setKillWords(asStringList(scoring.kill_words));
  }, [config]);

  useEffect(() => {
    const profile = settings?.["opportunity.career_profile"] as CareerProfile | undefined;
    if (!profile) return;
    setCurrentLocation(profile.current_location ?? "");
    setAuthorizedCountries(profile.authorized_countries ?? []);
    setWillingToRelocate(Boolean(profile.willing_to_relocate));
    setWorkMode(profile.preferred_work_mode ?? "");
  }, [settings]);

  const issues: string[] = [];
  if (!currentLocation.trim()) issues.push("Mevcut konum boş olamaz.");
  if (authorizedCountries.length === 0) issues.push("En az bir çalışma izni ülkesi ekle.");
  if (config) {
    for (const { key, label } of WEIGHT_FIELDS) {
      if (!Number.isFinite(weights[key])) issues.push(`${label} sayısal olmalı.`);
    }
  }
  skills.forEach((skill, index) => {
    if (!skill.name.trim()) issues.push(`${index + 1}. yeteneğin adı boş.`);
  });

  const saveProfile = useMutation({
    mutationFn: async () => {
      if (!config) return;
      const scoring = { ...config.scoring };
      for (const { key } of WEIGHT_FIELDS) scoring[key] = weights[key];
      scoring.skills = skills
        .filter((skill) => skill.name.trim())
        .map((skill) => ({
          name: skill.name.trim(),
          points: skill.points,
          aliases: skill.aliases
            .split(",")
            .map((alias) => alias.trim())
            .filter(Boolean),
        }));
      scoring.role_terms = roleTerms;
      scoring.kill_words = killWords;
      const careerProfile: CareerProfile = {
        current_location: currentLocation.trim(),
        authorized_countries: authorizedCountries,
        willing_to_relocate: willingToRelocate,
        preferred_work_mode: workMode || undefined,
      };
      await Promise.all([
        api.put("/sources/jobhunter/config", { scoring, balance: config.balance }),
        api.put("/settings/opportunity.career_profile", { value: careerProfile }),
      ]);
    },
    onSuccess: () => {
      invalidateAfter("jobhunter.write", "settings.write");
      toast.push("Uyum profili ve çalışma izni kaydedildi.", { tone: "ok" });
    },
    onError: (error: Error) => toast.push(`Kaydedilemedi: ${error.message}`, { tone: "danger" }),
  });

  /* ── LinkedIn profilleri formu ── */
  const [editing, setEditing] = useState<LinkedProfile[]>([]);
  useEffect(() => {
    if (profilesQuery.data) setEditing(profilesQuery.data);
  }, [profilesQuery.data]);
  const saveProfiles = useMutation({
    mutationFn: () => api.put("/sources/jobhunter/linkedin-profiles", editing),
    onSuccess: () => {
      invalidateAfter("jobhunter.write");
      toast.push(`${editing.length} LinkedIn profili kaydedildi.`, { tone: "ok" });
    },
    onError: (error: Error) => toast.push(`Profiller kaydedilemedi: ${error.message}`, { tone: "danger" }),
  });

  /* ── Veri temizliği (iki adımlı: önizleme + onay) ── */
  const [prunePreview, setPrunePreview] = useState<{
    candidates: number;
    protected: number;
    archived: number;
    estimated_bytes: number;
    confirm_token: string;
  } | null>(null);
  const prunePreviewMutation = useMutation({
    mutationFn: () =>
      api.get<{
        candidates: number;
        protected: number;
        archived: number;
        estimated_bytes: number;
        confirm_token: string;
      }>("/opportunities/prune/preview?days=90"),
    onSuccess: setPrunePreview,
    onError: (error: Error) => toast.push(`Önizleme alınamadı: ${error.message}`, { tone: "danger" }),
  });
  const pruneMutation = useMutation({
    mutationFn: (token: string) =>
      api.post<{ pruned: number }>(`/opportunities/prune?days=90&confirm_token=${encodeURIComponent(token)}`),
    onSuccess: (result) => {
      setPrunePreview(null);
      invalidateAfter("opportunity.write");
      toast.push(`${result.pruned} eski ilan temizlendi.`, { tone: "ok" });
    },
    onError: (error: Error) => {
      toast.push(`Temizleme başarısız: ${error.message}`, { tone: "danger" });
      // Jeton bayatladıysa (409) önizlemeyi yenile ki yeni jeton alınsın.
      setPrunePreview(null);
      prunePreviewMutation.mutate();
    },
  });

  async function confirmPrune() {
    if (!prunePreview) return;
    const ok = await confirmDialog({
      title: "Eski ilanlar temizlensin mi?",
      body: `${prunePreview.candidates} sahipsiz ham ilan silinecek; kullanıcı verisi olan ${prunePreview.protected} kayıt korunacak.`,
      confirmLabel: "Temizle",
      tone: "danger",
    });
    if (ok) pruneMutation.mutate(prunePreview.confirm_token);
  }

  function patchProfile(index: number, patch: Partial<LinkedProfile>) {
    setEditing((prev) => prev.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }

  const body = (
    <div className="space-y-4">
      <Tabs
        value={section}
        onChange={setSection}
        ariaLabel="Jobhunter ayar bölümleri"
        items={[
          { id: "profile", label: "Uyum profili" },
          { id: "linkedin", label: "LinkedIn profilleri" },
          { id: "env", label: "Ortam" },
          { id: "maintenance", label: "Veri temizliği" },
        ]}
      />

      {section === "profile" && (
        <div className="space-y-4">
          <Section title="Basit" hint="Sık değişen tercihler">
            <div className="grid gap-3 md:grid-cols-2">
              <Field label="Mevcut konum">
                <Input value={currentLocation} onChange={setCurrentLocation} placeholder="Ankara, Türkiye" />
              </Field>
              <Field label="Tercih edilen çalışma biçimi">
                <Select
                  value={workMode}
                  onChange={setWorkMode}
                  ariaLabel="Tercih edilen çalışma biçimi"
                  className="w-full"
                >
                  {WORK_MODES.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
            <Checkbox
              checked={willingToRelocate}
              onChange={setWillingToRelocate}
              label="Gerekirse taşınabilirim"
              className="mt-3"
            />
            <div className="mt-3 space-y-3">
              <TokenListField
                label="Çalışma izni olan ülkeler"
                values={authorizedCountries}
                onChange={setAuthorizedCountries}
                placeholder="Türkiye, Almanya"
              />
              <TokenListField
                label="Hedef roller"
                values={roleTerms}
                onChange={setRoleTerms}
                placeholder="backend engineer"
              />
            </div>
            <div className="mt-4">
              <span className="text-meta font-medium text-secondary">Yetenekler</span>
              <div className="mt-2 space-y-2">
                {skills.map((skill, index) => (
                  <div key={index} className="grid gap-1.5 sm:grid-cols-[minmax(0,1fr)_6rem_minmax(0,1fr)_auto]">
                    <Input
                      value={skill.name}
                      onChange={(name) =>
                        setSkills((prev) => prev.map((row, i) => (i === index ? { ...row, name } : row)))
                      }
                      placeholder="Yetenek adı"
                      className="w-full"
                    />
                    <NumberInput
                      value={skill.points}
                      onChange={(points) =>
                        setSkills((prev) => prev.map((row, i) => (i === index ? { ...row, points } : row)))
                      }
                      ariaLabel="Yetenek puanı"
                      className="w-full"
                    />
                    <Input
                      value={skill.aliases}
                      onChange={(aliases) =>
                        setSkills((prev) => prev.map((row, i) => (i === index ? { ...row, aliases } : row)))
                      }
                      placeholder="Eş anlamlılar (virgülle)"
                      className="w-full"
                    />
                    <IconButton
                      title="Yeteneği kaldır"
                      tone="danger"
                      onClick={() => setSkills((prev) => prev.filter((_, i) => i !== index))}
                    >
                      <Trash2 size={13} />
                    </IconButton>
                  </div>
                ))}
                {skills.length === 0 && <Empty>Henüz yetenek yok — ekle.</Empty>}
              </div>
              <span className="mt-2 block">
                <Button size="sm" onClick={() => setSkills((prev) => [...prev, { name: "", points: 0, aliases: "" }])}>
                  <Plus size={13} /> Yetenek ekle
                </Button>
              </span>
            </div>
          </Section>

          <Section title="Advanced" hint="Ağırlıklar, cezalar ve tazelik">
            <div>
              <span className="text-meta font-medium text-secondary">Ağırlıklar</span>
              <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-3">
                {WEIGHT_FIELDS.filter((field) => field.group === "weights").map(({ key, label }) => (
                  <Field key={key} label={label}>
                    <NumberInput
                      value={weights[key] ?? 0}
                      onChange={(value) => setWeights((prev) => ({ ...prev, [key]: value }))}
                      ariaLabel={label}
                      className="w-full"
                    />
                  </Field>
                ))}
              </div>
            </div>
            <div className="mt-4">
              <span className="text-meta font-medium text-secondary">Cezalar ve bonuslar</span>
              <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-3">
                {WEIGHT_FIELDS.filter((field) => field.group === "penalties").map(({ key, label }) => (
                  <Field key={key} label={label}>
                    <NumberInput
                      value={weights[key] ?? 0}
                      onChange={(value) => setWeights((prev) => ({ ...prev, [key]: value }))}
                      ariaLabel={label}
                      className="w-full"
                    />
                  </Field>
                ))}
              </div>
            </div>
            <div className="mt-4">
              <span className="text-meta font-medium text-secondary">Tazelik</span>
              <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-3">
                {WEIGHT_FIELDS.filter((field) => field.group === "freshness").map(({ key, label }) => (
                  <Field key={key} label={label}>
                    <NumberInput
                      value={weights[key] ?? 0}
                      onChange={(value) => setWeights((prev) => ({ ...prev, [key]: value }))}
                      ariaLabel={label}
                      className="w-full"
                    />
                  </Field>
                ))}
              </div>
            </div>
            <div className="mt-4">
              <TokenListField
                label="Elenme kelimeleri"
                values={killWords}
                onChange={setKillWords}
                placeholder="unpaid, commission only"
              />
            </div>
          </Section>

          <div className="rounded-card border border-subtle bg-surface-sunken p-3">
            <span className="text-meta font-medium text-secondary">Doğrulama</span>
            {issues.length === 0 ? (
              <p className="mt-1 text-meta text-ok">Kayda hazır: alanlar tutarlı.</p>
            ) : (
              <ul className="mt-1 list-disc space-y-0.5 pl-4 text-meta text-danger">
                {issues.map((issue) => (
                  <li key={issue}>{issue}</li>
                ))}
              </ul>
            )}
          </div>

          <div className="flex justify-end">
            <Button
              variant="primary"
              disabled={issues.length > 0 || saveProfile.isPending}
              onClick={() => saveProfile.mutate()}
            >
              <Check size={14} /> Kaydet
            </Button>
          </div>
        </div>
      )}

      {section === "linkedin" && (
        <Section title="LinkedIn arama profilleri">
          <p className="mb-2 text-meta text-muted">
            Varsayılan profiller portallarla birleşir; seninkiler en sona eklenir ve senkron turlarında çalışır.
          </p>
          <div className="space-y-2">
            {editing.map((row, index) => (
              <div
                key={index}
                className="grid gap-1.5 rounded-control border border-subtle p-2 sm:grid-cols-[1fr_1fr_5rem_4rem_auto]"
              >
                <Input
                  value={row.term}
                  onChange={(term) => patchProfile(index, { term })}
                  placeholder="Arama terimi"
                  className="w-full"
                />
                <Input
                  value={row.location ?? ""}
                  onChange={(location) => patchProfile(index, { location })}
                  placeholder="Konum (ops.)"
                  className="w-full"
                />
                <NumberInput
                  value={row.results_wanted ?? 50}
                  onChange={(results_wanted) => patchProfile(index, { results_wanted })}
                  ariaLabel="Sonuç sayısı"
                  className="w-full"
                />
                <Checkbox
                  checked={Boolean(row.is_remote)}
                  onChange={(is_remote) => patchProfile(index, { is_remote })}
                  label="Uzak"
                  className="text-meta text-muted"
                />
                <IconButton
                  title="Profili sil"
                  tone="danger"
                  onClick={() => setEditing((prev) => prev.filter((_, i) => i !== index))}
                >
                  <Trash2 size={13} />
                </IconButton>
              </div>
            ))}
            {editing.length === 0 && <Empty>Henüz profil yok — ekle.</Empty>}
          </div>
          <div className="mt-3 flex items-center justify-between">
            <Button size="sm" onClick={() => setEditing((prev) => [...prev, { term: "" }])}>
              <Plus size={13} /> Profil ekle
            </Button>
            <Button
              variant="primary"
              size="sm"
              disabled={editing.some((row) => !row.term.trim()) || saveProfiles.isPending}
              onClick={() => saveProfiles.mutate()}
            >
              <Check size={13} /> Kaydet
            </Button>
          </div>
        </Section>
      )}

      {section === "env" && (
        <Section title="Ortam (container env)">
          <div className="space-y-1.5 text-meta">
            <div className="flex items-center justify-between">
              <span className="text-muted">LINKEDIN_ALLOW_DIRECT</span>
              <Chip>{env?.linkein_allow_direct ? "açık" : "kapalı"}</Chip>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted">FORKJOB_LINKEDIN_PROXIES_FILE</span>
              <Chip>{env?.proxies_file || "tanımsız"}</Chip>
            </div>
          </div>
          <p className="mt-3 text-meta text-muted">
            Bu değerler container başlarken okunur — değiştirmek için compose.yaml env bölümünü düzenle, sonra make down
            &amp;&amp; make up.
          </p>
        </Section>
      )}

      {section === "maintenance" && (
        <Section title="Eski ilanları temizle (90+ gün)">
          <p className="mb-3 text-meta text-muted">
            3 aydan eski ve sahipsiz ham ilanlar veritabanından temizlenir. Başvurusu, notu, ilişkisi, görevi,
            görüşmesi, gereksinimi veya belgesi olan kayıtlar <strong>asla silinmez</strong>. Önce önizleme gösterilir;
            silme yalnızca ikinci onaydan sonra, onay jetonuyla çalışır.
          </p>
          {prunePreview ? (
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2">
                <Chip tone="warn">{prunePreview.candidates} silinecek</Chip>
                <Chip>{prunePreview.protected} korunacak</Chip>
                <Chip>{prunePreview.archived} arşivlenecek</Chip>
                <Chip>{Math.round(prunePreview.estimated_bytes / 1024)} KB boşalacak</Chip>
              </div>
              <div className="flex gap-2">
                <Button variant="danger" size="sm" disabled={pruneMutation.isPending} onClick={confirmPrune}>
                  <Trash2 size={13} /> Onayla ve temizle
                </Button>
                <Button size="sm" onClick={() => setPrunePreview(null)}>
                  Vazgeç
                </Button>
              </div>
            </div>
          ) : (
            <Button size="sm" disabled={prunePreviewMutation.isPending} onClick={() => prunePreviewMutation.mutate()}>
              <Trash2 size={13} /> 90+ günlük ilanları önizle
            </Button>
          )}
        </Section>
      )}
    </div>
  );

  if (!onClose) return body;
  return (
    <Modal open onClose={onClose} title="Jobhunter ayarları" hint="config.yaml · yalnızca yerel">
      {body}
    </Modal>
  );
}
