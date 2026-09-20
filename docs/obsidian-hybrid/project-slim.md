# forkOS — Project Slim Design: Operational Execution vs Project Knowledge

Bu doküman, Proje modülünün gelecekteki sınırlarını ve hangi yeteneklerin forkOS'ta kalıp hangilerinin Obsidian Vault'a devredileceğini tanımlar.

> [!NOTE]
> **PHASE 3 (uygulandı).** Aşağıdaki kararlar hayata geçti: proje bilgi notu
> `20 Projects/<Proje>/<Proje>.md`, proje günlüğü
> `20 Projects/<Proje>/Journal/YYYY-MM-DD.md` olarak private f0rknbrain Vault'unda
> yaşar. forkOS proje sayfası operasyonel kabuk + salt-okunur
> `ProjectActivityTimeline` + `ProjectJournalBridge` sunar; gövde düzenleme
> Obsidian'da yapılır. Devrin sözleşmesi:
> `docs/obsidian-hybrid/phase3-cutover.md`.

---

## 1. Temel Soru ve Ayrım Kriteri

> **"Bu bilgi operasyonel bir yürütme durumu mu, yoksa düşünsel/uzun vadeli bir bilgi mi?"**

- **Operasyonel (forkOS):** Durumlar, teslim tarihleri, açık görevler, GitHub PR/issue tetikleyicileri, günlük ajanda ve çalışma ritmi.
- **Bilgi (Obsidian Vault):** Projenin vizyonu, mimari kararları, teknik araştırmalar, toplantı notları, serbest günlükler, RFC'ler ve kılavuzlar.

---

## 2. Yetenek Bazında İnceleme ve Kararlar

| Proje Yeteneği | Tür | Sahip (PHASE 3'te uygulandı) | Karar | Gerekçe |
|---|---|---|---|---|
| **Project Identity & Title** | Operasyonel | forkOS (`project` + `Entity`) | `KEEP` | Görevlerin, harcamaların, kilometre taşlarının ve durumların bağlanacağı ana çekirdek kimlik. |
| **Project Status (`active/paused/done/idea`)** | Operasyonel | forkOS (`project.status`) | `KEEP` | Today paneli, filtreler ve odak algoritmaları bu duruma göre dinamik iş listesi üretir. |
| **Milestones & Deadlines** | Operasyonel | forkOS (`milestone` table) | `KEEP` | Takvim, `/api/deadlines` sözleşmesi ve zaman çizelgesi yürütmenin parçasıdır. |
| **Project Todos (`Todo.project_id`)** | Operasyonel | forkOS (`todo` table) | `KEEP` | Görev yürütme, önceliklendirme, tamamlanma ve rutinler forkOS'un en güçlü alanıdır. |
| **GitHub Integration (`GithubPanel.tsx`)** | Operasyonel | forkOS (`project.github_repo`) | `KEEP` | Depo durumu izleme, issue'ları tek tıkla forkOS görevine dönüştürme operasyonel akıştır. |
| **Project Activity (`last_activity_at`, commits)** | Operasyonel | forkOS (`github_activity`) | `KEEP` | Projenin ne kadar süredir hareketsiz olduğunu ölçer; pasif projeleri yüzeye çıkarır. |
| **Today Project Widget & Context** | Operasyonel | forkOS (`ProjectsWidget.tsx`) | `KEEP` | Günlük odak sırasında hangi projede olduğunun farkında olmayı sağlar. |
| **CaptureDialog Project Selection** | Operasyonel | forkOS | `KEEP` | Hızlı yakalama sırasında görevi projeye atama kritik operasyonel ergonomidir. |
| **Project Knowledge Note (`20 Projects/<Name>/<Name>.md`)** | Bilgi (Knowledge) | Obsidian Vault | `BRIDGE` | Proje vizyonu, mimari kararlar, araştırma linkleri tek tıkla açılan Vault notunda yaşar. |
| **Project Journal (`Note.journal_day` + `project_id`)** | Bilgi (Knowledge) | Obsidian Vault (`.../Journal/`) | `MOVE_TO_VAULT` | Proje günlükleri serbest metindir; Obsidian'ın arama, backlink ve günlük takviminde çok daha etkindir. |
| **Long Descriptions & Ad-hoc Notes** | Bilgi (Knowledge) | Obsidian Vault | `MOVE_TO_VAULT` | Proje içi dev metin kutuları yerine Obsidian editörü kullanılır. |
| **Knowledge Graph (Project Relations)** | Bilgi (Knowledge) | Obsidian Vault | `MOVE_TO_VAULT` | Proje notunun diğer notlarla ve kaynaklarla ilişkisi Obsidian grafında görselleştirilir. |

---

## 3. Slimmed Project Sayfası Mimarisi

Uygulanan sadeleştirilmiş Projeler ekranı (PHASE 3):

```text
+------------------------------------------------------------------------+
| PROJE: forkOS Core                             [Aktif] [Obsidian'da Aç]|
+------------------------------------------------------------------------+
| Bilgi Notu: 20 Projects/forkOS Core/forkOS Core.md                     |
| Sıradaki Aksiyon: Obsidian köprüsü testlerini tamamla                 |
+------------------------------------------------------------------------+
| KİLOMETRE TAŞLARI (Milestones)                                         |
| [✓] Faz 1: Envanter ve Temel (Bugün)                                  |
| [ ] Faz 2: Migration Motoru (25 Eylül)                                 |
+------------------------------------------------------------------------+
| GÖREVLER (Project Todos)                                               |
| - [ ] Vault index testlerini yaz                                       |
| - [ ] Settings Obsidian bileşenini bağla                               |
+------------------------------------------------------------------------+
| GITHUB ENTEGRASYONU                                                    |
| Açık PR'lar (2) · Açık Issue'lar (4) · Son commit: 2 saat önce        |
+------------------------------------------------------------------------+
| AKTİVİTE (salt okunur olay zaman çizelgesi: [{day, events}])           |
| + GÜNLÜK KÖPRÜSÜ: [Tarih seç] [Bugünün günlüğünü Obsidian'da aç]       |
+------------------------------------------------------------------------+
```

### Ne Kaldırıldı?
- Ağır dahili Markdown not editörü ve ek yükleme alanı (gövde artık Obsidian'da düzenlenir).
- Sayfa içi ham Excalidraw tuvali (`NoteCanvas.tsx`; PHASE 3'te kaldırıldı, `@excalidraw/excalidraw` bağımlılığı da düştü).
- `PUT /projects/{id}/journal/{day}` uçlu sayfa içi proje günlüğü editörü: `GET /projects/{id}/journal` artık `[{day, events}]` döner, gövde alanı yoktur.
- forkOS veritabanındaki `note_project_journal_day_uniq` ilişkisi artık ürün akışında kullanılmaz (tablo/ilişki dondurulmuş arşiv olarak kalır).

### Ne Kazanılıyor?
- forkOS sadece işin **yürütülmesine** ve **takibine** odaklanır.
- Kullanıcı Obsidian'ın gelişmiş eklenti ekosistemini (Dataview, Canvas, Omnisearch) özgürce kullanır.
- forkOS veritabanına yeni bilgi yazılmaz; legacy Notlar tabloları ve ek deposu
  dondurulmuş arşiv olarak yerinde kalır, bu yüzden yedek kapsamı bu fazda
  küçülmez (`docs/obsidian-hybrid/phase3-cutover.md` §3).
