import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Building2, Check, Megaphone } from "lucide-react";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { Button, Chip, Empty, Field, Input, Section, Textarea, cx, useToast } from "@/core/ui";
import type { Application, Opportunity } from "@/core/types";
import { applicationStatusLabel, kindLabel, statusLabel } from "./labels";
import { normalizeCompany } from "./careerUtils";

interface CompanyBucket {
  key: string;
  label: string;
  jobs: Opportunity[];
}

/**
 * Şirket araştırması: gerçek başvuru kayıtlarının kurumları üzerinden ortak
 * şirket notu. Not `application.company_research` alanındadır ve aynı kurumun
 * tüm başvurularına birlikte yazılır; ilana özel not ayrı alanda (`note`) kalır.
 * Duyurular bu bölüme karışmaz — onların notu asla "Şirket Notu" değildir.
 */
export function CompanyResearchPanel({ jobKinds }: { jobKinds: string[] }) {
  const toast = useToast();
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [companyDraft, setCompanyDraft] = useState("");
  const [jobDraft, setJobDraft] = useState("");
  const { data: items = [], isLoading } = useQuery({
    queryKey: ["opportunities"],
    queryFn: () => api.get<Opportunity[]>("/opportunities?limit=1000"),
  });

  const companies = useMemo(() => {
    const buckets = new Map<string, CompanyBucket>();
    for (const item of items) {
      if (!jobKinds.includes(item.kind) || !item.application_status) continue;
      const key = normalizeCompany(item.organization);
      if (!key) continue;
      const bucket = buckets.get(key);
      if (bucket) {
        bucket.jobs.push(item);
        if (!bucket.label && item.organization) bucket.label = item.organization;
      } else {
        buckets.set(key, { key, label: item.organization ?? key, jobs: [item] });
      }
    }
    return [...buckets.values()].sort((left, right) => left.label.localeCompare(right.label, "tr"));
  }, [items, jobKinds]);
  const announcements = items.filter((item) => !jobKinds.includes(item.kind) && item.organization);
  const selected = companies.find((company) => company.key === selectedKey) ?? companies[0] ?? null;
  const selectedJob = (selected && selected.jobs.find((job) => job.id === selectedJobId)) ?? selected?.jobs[0] ?? null;

  const application = useQuery({
    queryKey: ["application", selectedJob?.id],
    queryFn: () => api.get<Application>(`/opportunities/${selectedJob?.id}/application`),
    enabled: Boolean(selectedJob?.id),
    retry: false,
  });

  useEffect(() => {
    setCompanyDraft(application.data?.company_research ?? "");
    setJobDraft(application.data?.note ?? "");
  }, [application.data]);

  const saveCompany = useMutation({
    mutationFn: (value: string) =>
      Promise.all(
        (selected?.jobs ?? []).map((job) =>
          api.put<Application>(`/opportunities/${job.id}/application`, { company_research: value }),
        ),
      ),
    onSuccess: () => {
      invalidateAfter("opportunity.write");
      toast.push("Şirket notu bu kurumun tüm başvurularına yazıldı.", { tone: "ok" });
    },
    onError: (error: Error) => toast.push(`Şirket notu kaydedilemedi: ${error.message}`, { tone: "danger" }),
  });
  const saveJob = useMutation({
    mutationFn: (value: string) =>
      api.put<Application>(`/opportunities/${selectedJob?.id}/application`, { note: value }),
    onSuccess: () => {
      invalidateAfter("opportunity.write");
      toast.push("İlana özel not kaydedildi.", { tone: "ok" });
    },
    onError: (error: Error) => toast.push(`İlana özel not kaydedilemedi: ${error.message}`, { tone: "danger" }),
  });

  return (
    <Section title="Şirket araştırması" hint="Notlar yerel; dış ağ çağrısı yok">
      {isLoading ? (
        <div className="h-24 animate-pulse rounded-card bg-surface-sunken" />
      ) : companies.length === 0 ? (
        <Empty title="Not tutulacak şirket yok">
          Başvuru kaydı olan bir iş ilanı oluştuğunda kurum burada listelenir.
        </Empty>
      ) : (
        <div className="stack-y-4">
          <div className="grid gap-3 md:grid-cols-[16rem_minmax(0,1fr)]">
            <div className="stack-y-1">
              <span className="text-meta font-medium text-secondary">Kurum</span>
              <div className="max-h-64 stack-y-1 overflow-y-auto">
                {companies.map((company) => (
                  <button
                    key={company.key}
                    type="button"
                    onClick={() => {
                      setSelectedKey(company.key);
                      setSelectedJobId(company.jobs[0]?.id ?? null);
                    }}
                    className={cx(
                      "w-full rounded-control border p-2 text-left transition",
                      selected?.key === company.key
                        ? "border-accent-border bg-accent-surface"
                        : "border-subtle bg-surface hover:bg-surface-hover",
                    )}
                  >
                    <span className="flex items-center gap-1 text-body text-primary">
                      <Building2 size={13} /> {company.label}
                    </span>
                    <span className="mt-0.5 block text-micro text-muted">
                      {company.jobs.length} başvuru · normalize: {company.key}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {selected && (
              <div className="stack-y-4 rounded-card border border-subtle bg-surface-sunken p-4">
                <Field label="Şirket Notu" hint="Bu kurumun tüm başvurularıyla paylaşılır.">
                  <Textarea value={companyDraft} onChange={setCompanyDraft} rows={5} />
                </Field>
                <Button
                  variant="primary"
                  disabled={saveCompany.isPending}
                  onClick={() => saveCompany.mutate(companyDraft)}
                >
                  <Check size={14} /> Şirket notunu kaydet
                </Button>

                <div>
                  <span className="text-meta font-medium text-secondary">Bu notu paylaşan ilanlar</span>
                  <ul className="mt-1 stack-y-1">
                    {selected.jobs.map((job) => (
                      <li key={job.id}>
                        <button
                          type="button"
                          onClick={() => setSelectedJobId(job.id)}
                          className={cx(
                            "w-full rounded-control border px-2 py-1 text-left text-meta transition",
                            selectedJob?.id === job.id
                              ? "border-accent-border bg-accent-surface text-primary"
                              : "border-subtle bg-surface text-secondary hover:bg-surface-hover",
                          )}
                        >
                          <span className="text-primary">{job.title}</span>
                          <span className="ml-2 text-muted">
                            {statusLabel(job.status)}
                            {job.application_status ? ` · ${applicationStatusLabel(job.application_status)}` : ""}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>

                {selectedJob && (
                  <Field label="İlana özel not" hint={`Yalnızca "${selectedJob.title}" ilanını bağlar.`}>
                    <Textarea value={jobDraft} onChange={setJobDraft} rows={3} />
                    <span className="mt-2 block">
                      <Button disabled={saveJob.isPending} onClick={() => saveJob.mutate(jobDraft)}>
                        İlana özel notu kaydet
                      </Button>
                    </span>
                  </Field>
                )}
              </div>
            )}
          </div>

          {announcements.length > 0 && (
            <div className="rounded-card border border-subtle bg-surface p-4">
              <span className="flex items-center gap-1 text-meta font-medium text-secondary">
                <Megaphone size={13} /> Duyurular
              </span>
              <p className="mt-1 text-meta text-muted">
                Duyuru kayıtları şirket notuna karışmaz; duyuru notu ilan detayında ayrı tutulur.
              </p>
              <ul className="mt-2 stack-y-1">
                {announcements.slice(0, 20).map((item) => (
                  <li key={item.id} className="flex flex-wrap items-center gap-2 text-meta text-secondary">
                    <span className="text-primary">{item.title}</span>
                    <Chip>{kindLabel(item.kind)}</Chip>
                    <Chip>{statusLabel(item.status)}</Chip>
                    <span className="text-muted">Duyuru notu</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </Section>
  );
}
