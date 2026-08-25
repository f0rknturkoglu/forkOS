import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, Plus, Trash2, X } from "lucide-react";
import { api } from "@/core/api";
import { Badge, Button, Empty, Section as Panel, useToast } from "@/core/ui";

interface ScoringConfig { scoring: Record<string, unknown>; balance: Record<string, unknown>; }
interface LinkedProfile { term: string; location?: string; results_wanted?: number; hours_old?: number; is_remote?: boolean; fetch_description?: boolean; }

const WEIGHT_KEYS: [string, string][] = [
  ["base", "Temel puan"],
  ["skill_max", "Yetenek tavanı"],
  ["skill_title_multiplier", "Başlık çarpanı"],
  ["level_bonus", "Seviye bonusu"],
  ["visa_bonus", "Sponsorluk bonusu"],
  ["visa_penalty", "Sponsorluk cezası"],
  ["tr_relocation_penalty", "Taşınma cezası"],
  ["freshness_grace_days", "Tazelik hoşgörü (gün)"],
  ["freshness_penalty_per_day", "Günlük tazelik cezası"],
  ["freshness_max_penalty", "Tazelik ceza tavanı"],
  ["kill_score", "Elendi skoru"],
  ["score_cap", "Skor tavanı"],
]

/** Jobhunter ayar çarkı: uyum profili, LinkedIn profilleri, ortam. */
export function JobhunterSettings({ onClose }: { onClose: () => void }) {
  const toast = useToast();
  const [section, setSection] = useState<"profile" | "linkedin" | "env">("profile");

  const { data: config, refetch: refetchConfig } = useQuery({
    queryKey: ["jobhunter-config"],
    queryFn: () => api.get<ScoringConfig>("/sources/jobhunter/config"),
  });
  const { data: profiles = [], refetch: refetchProfiles } = useQuery({
    queryKey: ["jobhunter-linkedin"],
    queryFn: () => api.get<LinkedProfile[]>("/sources/jobhunter/linkedin-profiles"),
  });
  const { data: env } = useQuery({
    queryKey: ["jobhunter-env"],
    queryFn: () => api.get<{ linkein_allow_direct: string; proxies_file: string }>("/sources/jobhunter/env"),
  });

  /* ── Uyum profili formu ── */
  const [weights, setWeights] = useState<Record<string, string>>({});
  const [skillsText, setSkillsText] = useState("");
  const [roleTerms, setRoleTerms] = useState("");
  const [levelWords, setLevelWords] = useState("");
  const [killWords, setKillWords] = useState("");
  useEffect(() => {
    if (!config) return;
    const s = config.scoring as Record<string, unknown>;
    const next: Record<string, string> = {};
    for (const [key] of WEIGHT_KEYS) next[key] = String(s[key] ?? "");
    setWeights(next);
    const skills = (s.skills ?? []) as { name: string; points: number; aliases?: string[] }[];
    setSkillsText(skills.map((x) => x.name + " | " + x.points + " | " + (x.aliases ?? []).join(", ")).join("\n"));
    setRoleTerms(((s.role_terms ?? []) as string[]).join(", "));
    setLevelWords(((s.level_words ?? []) as string[]).join(", "));
    setKillWords(((s.kill_words ?? []) as string[]).join(", "));
  }, [config]);

  async function saveProfile() {
    if (!config) return;
    const s = config.scoring as Record<string, unknown>;
    const next = { ...s };
    for (const [key] of WEIGHT_KEYS) {
      const value = Number(weights[key]);
      if (Number.isFinite(value)) next[key] = value;
    }
    next.skills = skillsText.split("\n").map((line) => {
      const [name, points, aliases] = line.split("|").map((x) => x.trim());
      return { name, points: Number(points) || 0, aliases: aliases ? aliases.split(",").map((a) => a.trim()).filter(Boolean) : [] };
    }).filter((x) => x.name);
    next.role_terms = roleTerms.split(",").map((x) => x.trim()).filter(Boolean);
    next.level_words = levelWords.split(",").map((x) => x.trim()).filter(Boolean);
    next.kill_words = killWords.split(",").map((x) => x.trim()).filter(Boolean);
    await api.put("/sources/jobhunter/config", { scoring: next, balance: config.balance });
    refetchConfig();
    toast.push("Uyum profili kaydedildi — sıradaki senkron yeni skorlarla hesaplanır.", { tone: "ok" });
  }

  /* ── LinkedIn profilleri formu ── */
  const [editing, setEditing] = useState<LinkedProfile[]>([]);
  useEffect(() => { setEditing(profiles); }, [profiles]);
  function patchProfile(index: number, patch: Partial<LinkedProfile>) {
    setEditing((prev) => prev.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }
  async function saveProfiles() {
    if (editing.some((p) => !p.term.trim())) {
      toast.push("Her profil bir arama terimi ister.", { tone: "warn" });
      return;
    }
    await api.put("/sources/jobhunter/linkedin-profiles", editing);
    refetchProfiles();
    toast.push(editing.length + " LinkedIn profili kaydedildi.", { tone: "ok" });
  }

  const inputCls = "h-8 min-w-0 rounded-control border border-subtle bg-surface px-2 text-meta text-primary outline-none focus:border-accent";
  const labelCls = "mb-1 block text-meta text-muted";
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-canvas/60 p-4" onClick={onClose}>
      <div className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-card border border-subtle bg-surface shadow-overlay" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-subtle px-4 py-3">
          <h2 className="font-serif text-title text-primary">Jobhunter ayarları</h2>
          <button type="button" onClick={onClose} className="text-muted transition hover:text-primary" aria-label="Kapat">
            <X size={16} />
          </button>
        </div>
        <div className="flex flex-wrap gap-1.5 border-b border-subtle px-4 py-2">
          {([["profile", "Uyum profili"], ["linkedin", "LinkedIn profilleri"], ["env", "Ortam"]] as const).map(([id, label]) => (
            <button key={id} type="button" onClick={() => setSection(id)}
              className={section === id ? "h-7 rounded-control border border-accent bg-accent-surface px-2.5 text-meta font-medium text-accent" : "h-7 rounded-control border border-subtle px-2.5 text-meta text-secondary hover:bg-surface-hover"}>
              {label}
            </button>
          ))}
        </div>

        <div className="space-y-4 p-4">
          {section === "profile" && (
            <div className="space-y-4">
              <Panel title="Ağırlıklar">
                <div className="grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-3">
                  {WEIGHT_KEYS.map(([key, label]) => (
                    <label key={key} className="block">
                      <span className={labelCls}>{label}</span>
                      <input type="number" step="0.1" value={weights[key] ?? ""}
                        onChange={(e) => setWeights((prev) => ({ ...prev, [key]: e.target.value }))}
                        className={inputCls + " w-full"} />
                    </label>
                  ))}
                </div>
              </Panel>
              <Panel title="Yetenekler (satır: ad | puan | eş anlamlılar, virgüllü)">
                <textarea value={skillsText} onChange={(e) => setSkillsText(e.target.value)} rows={6}
                  className="w-full resize-y rounded-control border border-subtle bg-surface p-2 font-mono text-meta text-primary outline-none" />
              </Panel>
              <div className="grid gap-4 md:grid-cols-2">
                <Panel title="Rol terimleri (virgüllü)">
                  <textarea value={roleTerms} onChange={(e) => setRoleTerms(e.target.value)} rows={3} className="w-full resize-y rounded-control border border-subtle bg-surface p-2 font-mono text-meta text-primary outline-none" />
                </Panel>
                <Panel title="Seviye kelimeleri (virgüllü)">
                  <textarea value={levelWords} onChange={(e) => setLevelWords(e.target.value)} rows={3} className="w-full resize-y rounded-control border border-subtle bg-surface p-2 font-mono text-meta text-primary outline-none" />
                </Panel>
              </div>
              <Panel title="Elenme kelimeleri (virgüllü)">
                <textarea value={killWords} onChange={(e) => setKillWords(e.target.value)} rows={3} className="w-full resize-y rounded-control border border-subtle bg-surface p-2 font-mono text-meta text-primary outline-none" />
              </Panel>
              <div className="flex justify-end"><Button variant="primary" onClick={saveProfile}><Check size={14} /> Kaydet</Button></div>
            </div>
          )}

          {section === "linkedin" && (
            <Panel title="LinkedIn arama profilleri">
              <p className="mb-2 text-meta text-muted">Varsayılan profiller portallarla birleşir; seninkiler en sona eklenir ve senkron turlarında çalışır.</p>
              <div className="space-y-2">
                {editing.map((row, index) => (
                  <div key={index} className="grid gap-1.5 rounded border border-subtle p-2 sm:grid-cols-[1fr_1fr_5rem_4rem_auto]">
                    <input value={row.term} onChange={(e) => patchProfile(index, { term: e.target.value })} placeholder="Arama terimi" className={inputCls + " w-full"} />
                    <input value={row.location ?? ""} onChange={(e) => patchProfile(index, { location: e.target.value })} placeholder="Konum (ops.)" className={inputCls + " w-full"} />
                    <label className="flex items-center gap-1 text-meta text-muted"><input type="number" value={row.results_wanted ?? 50} onChange={(e) => patchProfile(index, { results_wanted: Number(e.target.value) })} className={inputCls + " w-full"} />sonuç</label>
                    <label className="flex items-center gap-1 text-meta text-muted">
                      <input type="checkbox" checked={Boolean(row.is_remote)} onChange={(e) => patchProfile(index, { is_remote: e.target.checked })} className="h-4 w-4 accent-[var(--accent)]" />
                      <span>Uzak</span>
                    </label>
                    <button type="button" onClick={() => setEditing((prev) => prev.filter((_, i) => i !== index))} title="Profil sil" className="flex h-8 w-8 items-center justify-center rounded-control border border-subtle text-muted transition hover:border-danger hover:text-danger"><Trash2 size={13} /></button>
                  </div>
                ))}
                {editing.length === 0 && <Empty>Henüz profil yok — ekle.</Empty>}
              </div>
              <div className="mt-3 flex items-center justify-between">
                <Button size="sm" onClick={() => setEditing((prev) => [...prev, { term: "" }])}><Plus size={13} /> Profil ekle</Button>
                <Button variant="primary" size="sm" onClick={saveProfiles}><Check size={13} /> Kaydet</Button>
              </div>
            </Panel>
          )}

          {section === "env" && (
            <Panel title="Ortam (container env)">
              <div className="space-y-1.5 text-meta">
                <div className="flex items-center justify-between"><span className="text-muted">LINKEDIN_ALLOW_DIRECT</span><Badge>{env?.linkein_allow_direct ? "açık" : "kapalı"}</Badge></div>
                <div className="flex items-center justify-between"><span className="text-muted">FORKJOB_LINKEDIN_PROXIES_FILE</span><Badge>{env?.proxies_file || "tanımsız"}</Badge></div>
              </div>
              <p className="mt-3 text-meta text-muted">Bu değerler container başlarken okunur — değiştirmek için compose.yaml env bölümünü düzenle, sonra make down && make up.</p>
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
}
