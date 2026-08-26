# Alembic migration zinciri

Dosya adları gerçek sırayı yanıltabilir (bazı revision'lar sonradan
eklendi ve dosya adlarındaki sayılar zincir konumunu göstermiyor).
**Gerçek sıra `down_revision` alanından gelir.**

## Gerçek zincir (head → geri)

```
0001_core → 0002_capture → 0003_rss → 0004_todo → 0005_plan_slot
→ 0006_pomodoro → 0007_habit_review → 0008_opportunity → 0009_notification
→ 0010_deadline → 0011_study → 0012_course_book → 0013_document
→ 0014_calendar → 0015_project → 0016_finance → 0017_settings
→ 0018_opportunity_trash_sync → 0019_rss_reader → 0020_feed_favicon
→ 0021_media_item → 0022_pomodoro_pause → 0023_todo_recur
→ 0024_todo_milestone → 0025_document_folder_source → 0026_media_domain
→ 0022_finance_sub → 0023_application_crm → 0024_remove_habit
→ 0025_drop_deadline_v
→ 0027_book_to_media_item   ← head
```

## Dosya adı / zincir konumu eşleşmesi

| Dosya adı | Gerçek zincir konumu |
|---|---|
| `0022_finance_sub.py` | `0026_media_domain`'den SONRA (down_revision = 0026) |
| `0023_application_crm.py` | `0022_finance_sub`'dan sonra |
| `0024_remove_habit.py` | `0023_application_crm`'dan sonra |
| `0025_drop_deadline_v.py` | `0024_remove_habit`'ten sonra |

## Yeni migration eklerken

- `down_revision`'ı **her zaman** `alembic heads` çıktısındaki gerçek head'e
  ver; dosya adı numarasına güvenme.
- Dosya adını zincirdeki anlamlı adla ver (`NNNN_aciklama.py`); NNNN
  benzersiz olmasa da sorun değildir — yalnızca `revision` string'i kimliktir.
- `tests/test_migrations.py::test_revisions_form_a_single_chain` zinciri
  doğrular; tek head koşulu vardır.

## Karar (Faz 6, Y1)

Dosyalar yeniden adlandırılmadı (seçenek b): 0022/0023 dosyalarını
0027/0028 yapmak, bizim 0024/0025 revision'larımızla birlikte 6+ dosya
adı değişikliği gerektirirdi ve `alembic_version` tablosu zaten revision
string'ini tutuyor. Üretim verisi etkilenmez; bu tablo gerçek sırayı belgeler.
