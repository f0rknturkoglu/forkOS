import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  BookOpen,
  CalendarClock,
  ExternalLink,
  FileCheck,
  FileText,
  GraduationCap,
  Landmark,
  Plus,
  ScrollText,
} from "lucide-react";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { sourceLabel } from "@/core/labels";
import { navigate } from "@/app/router";
import { RelatedPanel } from "@/core/RelatedPanel";
import { useSaveToLibrary } from "@/core/SaveToLibrary";
import { planDayForToday } from "@/core/tasks";
import { Button, Chip, Empty, Input, Section, Tabs, relativeTime, useToast } from "@/core/ui";
import type { Document, Opportunity } from "@/core/types";
import { useOnline } from "@/lib/hooks";
import { captureVaultNote } from "@/core/obsidian";
import { OpportunityKnowledgeSection, RequirementsSection } from "./OpportunityDetailSections";
import { STATUS_TONES, announcementCategoryLabel, daysLeft, kindLabel, statusLabel } from "./labels";

type AnnouncementTab = "ozet" | "tarihler" | "kontenjan" | "belgeler" | "notlar";

const TAB_ITEMS = [
  { id: "ozet", label: "Özet" },
  { id: "tarihler", label: "Tarihler ve Aşamalar" },
  { id: "kontenjan", label: "Kontenjan ve Koşullar" },
  { id: "belgeler", label: "Belgeler" },
  { id: "notlar", label: "Notlar ve İlişkiler" },
] as const;

const TAB_LABELS: Record<AnnouncementTab, string> = {
  ozet: "Özet",
  tarihler: "Tarihler ve Aşamalar",
  kontenjan: "Kontenjan ve Koşullar",
  belgeler: "Belgeler",
  notlar: "Notlar ve İlişkiler",
};

/** Duyuruya ozel not sablonu (sirket arastirmasi degil, duyuru takibi). */
const noteTemplate = (item: Opportunity) =>
  [
    `# ${item.organization ?? "Kurum"} — ${item.title}`,
    "",
    `- **Kurum:** ${item.organization ?? "—"}`,
    `- **Duyuru:** ${item.guide_url ?? item.url ?? "—"}`,
    `- **Durum:** ${statusLabel(item.status)}`,
    "",
    "## Notlar",
    "- ",
  ].join("\n");

/**
 * Duyuru detayi (YLSY/ÖSYM/kamu). Is ilani yuzeylerinden KESIN olarak ayrilir:
 * maas, calisma bicimi, warm intro, sirket arastirma notu ve gorusmeler burada
 * hicbir kosulda render edilmez; bilinmeyen degerler `—` olarak gosterilir.
 */
export function AnnouncementDetail({ item }: { item: Opportunity }) {
  const online = useOnline();
  const toast = useToast();
  const [tab, setTab] = useState<AnnouncementTab>("ozet");
  const [taskTitle, setTaskTitle] = useState("");
  const [requirementName, setRequirementName] = useState("");
  const { save } = useSaveToLibrary();

  const transition = useMutation({
    mutationFn: (to: string) => api.post(`/opportunities/${item.id}/transition`, { to }),
    onSuccess: () => invalidateAfter("opportunity.write"),
  });

  const addTask = useMutation({
    mutationFn: () =>
      api.post(`/opportunities/${item.id}/todos`, { title: taskTitle.trim(), plan_day: planDayForToday() }),
    onSuccess: () => {
      setTaskTitle("");
      invalidateAfter("opportunity.write", "todo.write");
      toast.push("Görev oluşturuldu", { tone: "ok" });
    },
  });

  const addRequirement = useMutation({
    mutationFn: () => api.post(`/opportunities/${item.id}/requirements`, { name: requirementName.trim() }),
    onSuccess: () => {
      setRequirementName("");
      invalidateAfter("opportunity.write");
      toast.push("Belge gereksinimi eklendi", { tone: "ok" });
    },
  });

  const allowed = item.allowed_transitions ?? [];
  const applicationEnd = item.application_end_at ?? item.deadline_at;
  const left = daysLeft(applicationEnd);
  const officialLabel =
    item.official === true ? "Resmî kaynak" : item.official === false ? "İkincil kaynak" : "Kaynak türü —";
  const officialPage = item.guide_url ?? item.apply_url ?? item.url;
  const bookmarkUrl = item.url;

  return (
    <div className="flex flex-col gap-4">
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-1.5">
          <Chip>{kindLabel(item.kind)}</Chip>
          <Chip tone="accent">{announcementCategoryLabel(item.category)}</Chip>
          <Chip tone={STATUS_TONES[item.status] ?? "neutral"}>{statusLabel(item.status)}</Chip>
          <Chip tone={item.official === true ? "ok" : item.official === false ? "neutral" : "neutral"}>
            {officialLabel}
          </Chip>
        </div>
        <p className="text-meta text-muted">{[item.organization, item.stage].filter(Boolean).join(" · ") || "—"}</p>
        <div className="flex flex-wrap items-center gap-2">
          {officialPage && (
            <a
              href={officialPage}
              target="_blank"
              rel="noreferrer"
              className="flex h-control items-center gap-1.5 rounded-control border border-subtle bg-surface px-3 text-meta font-medium text-primary transition hover:bg-surface-hover"
            >
              <ExternalLink size={13} /> Resmî sayfayı aç
            </a>
          )}
          {bookmarkUrl && (
            <Button
              variant="secondary"
              size="sm"
              disabled={!online}
              title="Yer imlerine kaydet"
              onClick={() =>
                void save({ url: bookmarkUrl, title: item.title, collection: "reference", entity_id: item.id })
              }
            >
              <BookOpen size={13} /> Yer imlerine kaydet
            </Button>
          )}
          {allowed.includes("watching") && (
            <Button
              variant="secondary"
              size="sm"
              disabled={!online || transition.isPending}
              onClick={() => transition.mutate("watching")}
            >
              Takibe al
            </Button>
          )}
          {allowed.includes("reviewed") && (
            <Button
              variant="secondary"
              size="sm"
              disabled={!online || transition.isPending}
              onClick={() => transition.mutate("reviewed")}
            >
              Okundu işaretle
            </Button>
          )}
          {allowed.includes("archived") && (
            <Button
              variant="ghost"
              size="sm"
              disabled={!online || transition.isPending}
              onClick={() => transition.mutate("archived")}
            >
              Arşivle
            </Button>
          )}
          <Button variant="ghost" size="sm" onClick={() => setTab("notlar")}>
            <FileText size={13} /> Not oluştur
          </Button>
          {left !== null && (
            <span className={`text-meta font-medium tabular-nums ${left <= 7 ? "text-warn" : "text-muted"}`}>
              {left < 0 ? `${Math.abs(left)} gün önce doldu` : `Son tarihe ${left} gün`}
            </span>
          )}
        </div>
      </div>

      <Tabs<AnnouncementTab> ariaLabel="Duyuru sekmeleri" value={tab} onChange={setTab} items={[...TAB_ITEMS]} />
      <div role="tabpanel" aria-label={TAB_LABELS[tab]} id={`announcement-tabpanel-${tab}`}>
        {tab === "ozet" && (
          <div className="space-y-4">
            <Section title="Duyuru künyesi">
              <dl className="grid grid-cols-[10rem_1fr] gap-x-4 gap-y-2 text-meta">
                <Row label="Kurum" value={item.organization || "—"} />
                <Row label="Program / Başlık" value={item.title} />
                <Row label="Kategori" value={announcementCategoryLabel(item.category)} />
                <Row label="Kaynak türü" value={officialLabel} />
                <Row label="Kaynak" value={sourceLabel(item.source)} />
                <Row
                  label="Yayın tarihi"
                  value={item.published_at ? new Date(item.published_at).toLocaleDateString("tr-TR") : "—"}
                />
                <Row
                  label="Son başvuru"
                  value={applicationEnd ? new Date(applicationEnd).toLocaleDateString("tr-TR") : "—"}
                />
                <Row label="Aşama" value={item.stage || "—"} />
              </dl>
            </Section>

            <Section title="Bağlantılar">
              <div className="flex flex-wrap gap-2">
                {item.apply_url ? (
                  <LinkButton href={item.apply_url} label="Başvuru adresi" icon={<ExternalLink size={13} />} />
                ) : (
                  <span className="text-meta text-muted">Başvuru adresi —</span>
                )}
                {item.guide_url ? (
                  <LinkButton href={item.guide_url} label="Kılavuz" icon={<ScrollText size={13} />} />
                ) : (
                  <span className="text-meta text-muted">Kılavuz —</span>
                )}
                {item.parent_id && (
                  <Button size="sm" onClick={() => navigate(`/opportunities?focus=${item.parent_id}`)}>
                    <GraduationCap size={13} /> Ana kılavuza git
                  </Button>
                )}
              </div>
            </Section>

            <Section title="Hızlı aksiyonlar" hint="tümü yerelde">
              <div className="space-y-3">
                <form
                  className="flex gap-2"
                  onSubmit={(event) => {
                    event.preventDefault();
                    if (taskTitle.trim()) addTask.mutate();
                  }}
                >
                  <Input
                    value={taskTitle}
                    onChange={setTaskTitle}
                    placeholder="Görev başlığı (örn. belgeleri tamamla)"
                    ariaLabel="Yeni görev"
                    className="flex-1"
                  />
                  <Button type="submit" size="sm" disabled={!online || !taskTitle.trim() || addTask.isPending}>
                    <Plus size={13} /> Görev oluştur
                  </Button>
                </form>
                <form
                  className="flex gap-2"
                  onSubmit={(event) => {
                    event.preventDefault();
                    if (requirementName.trim()) addRequirement.mutate();
                  }}
                >
                  <Input
                    value={requirementName}
                    onChange={setRequirementName}
                    placeholder="Belge gereksinimi (örn. transkript)"
                    ariaLabel="Yeni belge gereksinimi"
                    className="flex-1"
                  />
                  <Button
                    type="submit"
                    size="sm"
                    disabled={!online || !requirementName.trim() || addRequirement.isPending}
                  >
                    <FileCheck size={13} /> Belge gereksinimi ekle
                  </Button>
                </form>
              </div>
            </Section>
          </div>
        )}

        {tab === "tarihler" && (
          <div className="space-y-4">
            <Section title="Tarihler" hint="bilinmeyen tarihler —">
              <ol className="space-y-3">
                <DateRow icon={<CalendarClock size={13} />} label="Yayın" value={item.published_at} />
                <DateRow
                  icon={<CalendarClock size={13} />}
                  label="Başvuru başlangıcı"
                  value={item.application_start_at}
                />
                <DateRow icon={<CalendarClock size={13} />} label="Başvuru bitişi" value={applicationEnd} />
                <DateRow icon={<GraduationCap size={13} />} label="Sınav" value={item.exam_at} />
                <DateRow icon={<FileCheck size={13} />} label="Sonuç" value={item.result_at} />
              </ol>
            </Section>
            <Section title="Aşama">
              <div className="flex flex-wrap items-center gap-2">
                <Chip tone={STATUS_TONES[item.status] ?? "neutral"}>{statusLabel(item.status)}</Chip>
                <span className="text-meta text-secondary">{item.stage || "Aşama belirtilmemiş."}</span>
              </div>
            </Section>
          </div>
        )}

        {tab === "kontenjan" && (
          <div className="space-y-4">
            <Section title="Kontenjan">
              {item.quota_total == null ? (
                <Empty>Kontenjan bilgisi bu duyuruda yer almıyor.</Empty>
              ) : (
                <div className="flex flex-wrap items-center gap-3">
                  <span className="numeral text-numeral-xl leading-none text-primary">{item.quota_total}</span>
                  <span className="text-meta text-secondary">kişilik kontenjan</span>
                </div>
              )}
            </Section>
            <Section title="Koşullar" hint="duyurudan gelen alanlar">
              {!item.fields || item.fields.length === 0 ? (
                <Empty>Alan / koşul bilgisi bu duyuruda yer almıyor.</Empty>
              ) : (
                <div className="flex flex-wrap gap-1.5">
                  {item.fields.map((field) => (
                    <Chip key={field}>{field}</Chip>
                  ))}
                </div>
              )}
              <dl className="mt-4 grid grid-cols-[10rem_1fr] gap-x-4 gap-y-2 text-meta">
                <Row label="Kategori" value={announcementCategoryLabel(item.category)} />
                <Row label="Kaynak türü" value={officialLabel} />
                <Row label="Aşama" value={item.stage || "—"} />
              </dl>
            </Section>
          </div>
        )}

        {tab === "belgeler" && <AnnouncementDocuments item={item} online={online} />}

        {tab === "notlar" && (
          <div className="space-y-4">
            <OpportunityKnowledgeSection
              id={item.id}
              online={online}
              canonical={false}
              title="Duyuru Notu"
              description="Duyuru notları Obsidian Vault'unda yaşar; takip ettiğin tarihleri ve hazırlık adımlarını orada yönet."
              searchQuery={item.organization ?? item.title}
              createLabel="Duyuru notu oluştur"
              emptyTitle="Henüz Duyuru Notu Oluşturulmadı"
              emptyText="Bu duyuru için Vault'ta şablon bir bilgi notu oluştur ve gereksinimlerini oraya yaz."
              create={() =>
                captureVaultNote({
                  body: noteTemplate(item),
                  relate_to: item.id,
                  tags: ["duyuru"],
                })
              }
            />
            <Section title="İlişkili kayıtlar ve duyurular">
              <RelatedPanel entityId={item.id} title="İlişkili kayıtlar ve duyurular" />
            </Section>
          </div>
        )}
      </div>
    </div>
  );
}

function AnnouncementDocuments({ item, online }: { item: Opportunity; online: boolean }) {
  const { data: documents = [] } = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.get<Document[]>("/documents"),
  });

  return (
    <div className="space-y-4">
      <Section title="Resmî belgeler">
        <div className="flex flex-wrap gap-2">
          {item.guide_url ? (
            <LinkButton href={item.guide_url} label="Kılavuz / PDF" icon={<ScrollText size={13} />} />
          ) : (
            <span className="text-meta text-muted">Kılavuz bağlantısı —</span>
          )}
          {item.apply_url ? (
            <LinkButton href={item.apply_url} label="Başvuru sayfası" icon={<Landmark size={13} />} />
          ) : (
            <span className="text-meta text-muted">Başvuru bağlantısı —</span>
          )}
        </div>
      </Section>
      <Section title="Belge gereksinimleri" hint="yüklediğin belgelerle eşleştir">
        <RequirementsSection id={item.id} online={online} documents={documents} showAdd={false} />
      </Section>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="contents">
      <dt className="font-medium text-muted">{label}</dt>
      <dd className="font-medium text-primary">{value}</dd>
    </div>
  );
}

function DateRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | null | undefined }) {
  return (
    <li className="flex items-center gap-3">
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-surface-sunken text-accent">
        {icon}
      </span>
      <span className="min-w-0 flex-1 text-body text-primary">{label}</span>
      <span className={`shrink-0 text-meta tabular-nums ${value ? "text-primary" : "text-muted"}`}>
        {value ? `${new Date(value).toLocaleDateString("tr-TR")} · ${relativeTime(value)}` : "—"}
      </span>
    </li>
  );
}

function LinkButton({ href, label, icon }: { href: string; label: string; icon: React.ReactNode }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="flex h-control items-center gap-1.5 rounded-control border border-subtle bg-surface px-3 text-meta font-medium text-primary transition hover:bg-surface-hover"
    >
      {icon} {label}
    </a>
  );
}
