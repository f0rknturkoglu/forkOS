import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { Button, Chip, Input, Tabs, Textarea } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import type { components } from "@/generated/api-schema";

type Intelligence = components["schemas"]["InterviewIntelligence"];

export function InterviewIntelligencePanel({ interviewId }: { interviewId: string }) {
  const online = useOnline();
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [notes, setNotes] = useState("");
  const [topics, setTopics] = useState("");
  const [gaps, setGaps] = useState("");
  const [occurredAt, setOccurredAt] = useState("");
  const [outcome, setOutcome] = useState("");
  const [employerFeedback, setEmployerFeedback] = useState("");
  const [tab, setTab] = useState<"prepare" | "practice" | "debrief">("prepare");
  const query = useQuery({
    queryKey: ["career-interview-intelligence", interviewId],
    queryFn: () => api.get<Intelligence>(`/career/interviews/${interviewId}/intelligence`),
  });
  const mutation = useMutation({
    mutationFn: async () => {
      if (tab === "prepare") return api.post(`/career/interviews/${interviewId}/prepare`);
      if (tab === "practice")
        return api.post(`/career/interviews/${interviewId}/practice`, { question, candidate_answer: answer });
      return api.post(`/career/interviews/${interviewId}/debrief`, {
        occurred_at: new Date(occurredAt).toISOString(),
        candidate_notes: notes,
        topics: topics
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        perceived_gaps: gaps
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        outcome_if_known: outcome || null,
        employer_feedback: employerFeedback || null,
      });
    },
    onSuccess: () => {
      invalidateAfter("career.write");
    },
  });
  const prep = query.data?.prep;
  const latest = query.data?.practice?.at(-1);
  return (
    <div className="mt-3 stack-y-3 border-t border-subtle pt-3">
      <Tabs
        value={tab}
        onChange={setTab}
        ariaLabel="Görüşme zekâsı sekmeleri"
        items={[
          { id: "prepare", label: "Hazırlık" },
          { id: "practice", label: "Prova" },
          { id: "debrief", label: "Görüşme sonrası" },
        ]}
      />
      {query.isLoading && <p className="text-meta text-muted">Kanıtlar yükleniyor…</p>}
      {query.isError && (
        <p role="alert" className="text-meta text-danger">
          {query.error.message}
        </p>
      )}
      {tab === "prepare" && (
        <>
          <p className="text-meta text-muted">
            Yerel kurallar; geçerli ilan, gerçek CV ve güncel değerlendirme gerekir.
          </p>
          {prep && (
            <div className="stack-y-2">
              <Chip tone={prep.is_stale ? "warn" : "ok"}>
                {prep.is_stale ? "Kanıt değişti; yeniden hazırla" : "Güncel hazırlık"}
              </Chip>
              <p className="text-body text-primary">
                {prep.role_summary} · {prep.interview_stage || "Aşama bilinmiyor"}
              </p>
              <p className="text-meta text-secondary">{prep.focus_areas.join(" · ")}</p>
              {prep.likely_questions.map((q) => (
                <p key={q} className="text-meta text-secondary">
                  {q}
                </p>
              ))}
              {prep.questions_to_ask.map((q) => (
                <p key={q} className="text-meta text-secondary">
                  Sor: {q}
                </p>
              ))}
              {prep.story_recommendations.map((s) => (
                <p key={s.story_id} className="text-meta text-secondary">
                  Hikâye {s.story_id}: {s.why_relevant}
                </p>
              ))}
              <p className="text-meta text-muted">
                {prep.unknowns
                  .map((value) => (value === "missing_story_gap" ? "Eşleşen doğrulanmış hikâye yok." : value))
                  .join(" · ")}
              </p>
            </div>
          )}
        </>
      )}
      {tab === "practice" && (
        <>
          <Input value={question} onChange={setQuestion} placeholder="Prova sorusu" ariaLabel="Prova sorusu" />
          <Textarea value={answer} onChange={setAnswer} placeholder="Yanıtın" ariaLabel="Prova yanıtı" />
          {latest && (
            <div className="text-meta text-secondary">
              <p>Teknik doğruluk: inceleme gerekiyor</p>
              {latest.gaps.map((g) => (
                <p key={g}>{g}</p>
              ))}
              <p>
                {Object.entries(latest.feedback)
                  .map(([k, v]) => `${k}: ${v}`)
                  .join(" · ")}
              </p>
            </div>
          )}
        </>
      )}
      {tab === "debrief" && (
        <>
          <Input
            type="datetime-local"
            value={occurredAt}
            onChange={setOccurredAt}
            ariaLabel="Görüşmenin gerçekleşme zamanı"
          />
          <Textarea value={notes} onChange={setNotes} placeholder="Görüşmede ne oldu?" ariaLabel="Görüşme notları" />
          <Input value={topics} onChange={setTopics} placeholder="Konular, virgülle" ariaLabel="Görüşme konuları" />
          <Input
            value={gaps}
            onChange={setGaps}
            placeholder="Algıladığın açıklar, virgülle"
            ariaLabel="Öz değerlendirme açıkları"
          />
          <Input
            value={outcome}
            onChange={setOutcome}
            placeholder="Biliniyorsa sonuç; boş bırakılabilir"
            ariaLabel="Bildirilen sonuç"
          />
          <p className="text-meta text-muted">
            Kullanıcı raporu olarak saklanır; ret nedeni çıkarılmaz, takip mesajı gönderilmez.
          </p>
          <Textarea
            value={employerFeedback}
            onChange={setEmployerFeedback}
            placeholder="Varsa işverenin açık geri bildirim alıntısı"
            ariaLabel="İşveren geri bildirim alıntısı"
          />
          {query.data?.debrief && (
            <p className="text-meta text-secondary">Kaydedilen not: {query.data.debrief.candidate_notes}</p>
          )}
        </>
      )}
      {mutation.isError && (
        <p role="alert" className="text-meta text-danger">
          {mutation.error.message}
        </p>
      )}
      <Button
        size="sm"
        disabled={
          !online ||
          mutation.isPending ||
          (tab === "practice" && (!question.trim() || !answer.trim() || !prep || prep.is_stale)) ||
          (tab === "debrief" && !occurredAt)
        }
        onClick={() => mutation.mutate()}
      >
        {mutation.isPending ? "İşleniyor…" : tab === "prepare" ? "Hazırla" : "Kaydet"}
      </Button>
    </div>
  );
}
