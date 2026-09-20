# forkOS — Project Slim Design: Operational Execution vs Project Knowledge

Bu doküman, Proje modülünün gelecekteki sınırlarını ve hangi yeteneklerin forkOS'ta kalıp hangilerinin Obsidian Vault'a devredileceğini tanımlar.

---

## 1. Temel Soru ve Ayrım Kriteri

> **"Bu bilgi operasyonel bir yürütme durumu mu, yoksa düşünsel/uzun vadeli bir bilgi mi?"**

- **Operasyonel (forkOS):** Durumlar, teslim tarihleri, açık görevler, GitHub PR/issue tetikleyicileri, günlük ajanda ve çalışma ritmi.
- **Bilgi (Obsidian Vault):** Projenin vizyonu, mimari kararları, teknik araştırmalar, toplantı notları, serbest günlükler, RFC'ler ve kılavuzlar.

---

## 2. Yetenek Bazında İnceleme ve Kararlar

| Proje Yeteneği | Tür | Gelecekteki Sahip | Karar | Gerekçe |
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

Gelecekteki sadeleştirilmiş Projeler ekranı:

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
```

### Ne Kaldırılıyor?
- Ağır dahili Markdown not editörü ve ek yükleme alanı.
- Sayfa içi ham Excalidraw tuvali.
- forkOS veritabanındaki `note_project_journal_day_uniq` ilişkisi.

### Ne Kazanılıyor?
- forkOS sadece işin **yürütülmesine** ve **takibine** odaklanır.
- Kullanıcı Obsidian'ın gelişmiş eklenti ekosistemini (Dataview, Canvas, Omnisearch) özgürce kullanır.
- forkOS veritabanı yükü ve yedekleme boyutu dramatik biçimde küçülür.
