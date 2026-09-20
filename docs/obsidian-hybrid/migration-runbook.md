# forkOS → Obsidian Notes Migration Runbook

Bu runbook, `backend/app/scripts/migrate_notes_to_vault.py` aracını çalıştıran
operatör içindir. Migration **kopya + doğrulama**dır: kaynak forkOS Notes
verisi bu fazda hiçbir şekilde değiştirilmez.

> [!IMPORTANT]
> Bu fazda Notes sahipliği **değişmez**. Notes modülü, ek dosya deposu ve
> frontend aynen çalışmaya devam eder. Cutover ileriki bir fazın işidir.

---

## 1. Ön koşullar

| Koşul | Nasıl sağlanır |
|---|---|
| Vault yapılandırılmış | `.env` içinde `OBSIDIAN_VAULT_PATH` (host) / `OBSIDIAN_VAULT_HOST_PATH` (container) |
| Vault yazılabilir | `make up-obsidian` (mount yalnızca `api` servisine verilir) |
| Kaynak DB erişilebilir | `make up` + `make migrate` (şema repo head'inde olmalı) |
| Ek deposu okunabilir | `backend/data/attachments` ya da container'da `/app/data/attachments` |

Container içinde çalıştırmak için:

```bash
make up-obsidian
docker compose exec api python -m app.scripts.migrate_notes_to_vault --dry-run
```

Host'ta çalıştırmak için (`backend/` içinden):

```bash
DATABASE_URL="postgresql+asyncpg://<user>:<pass>@127.0.0.1:<port>/<db>" \
  .venv/bin/python -m app.scripts.migrate_notes_to_vault --dry-run
```

---

## 2. Preflight kapıları

`--apply` **hiçbir not yazmadan önce** şu kapıları kontrol eder; kritik bir
blocker varsa durur ve rapor eder:

1. `vault_configured` — `OBSIDIAN_VAULT_PATH` dolu olmalı
2. `vault_available` — dizin var ve erişilebilir olmalı
3. `vault_readable` / `vault_writable`
4. `vault_identity_conflicts` — aynı `forkos_id` iki dosyada **olmamalı**
5. `vault_managed_metadata` — geçersiz `forkos_id`/`forkos_type` içeren managed dosya olmamalı
6. `source_db` — kaynak veritabanı erişilebilir olmalı
7. `manifest_version` — mevcut manifest sürümü uyumlu olmalı
8. `plan_identity` / `plan_blockers` — hedef yollar tek olmalı, plan çakışmasız olmalı

Uyarı seviyesinde (apply'ı durdurmayan) kapı:

- `attachment_storage` — blob gerektiren ek varsa depo okunabilir olmalı

---

## 3. Akış

### 3.1 Dry-run (varsayılan)

```bash
python -m app.scripts.migrate_notes_to_vault --dry-run
python -m app.scripts.migrate_notes_to_vault --dry-run --json --report /tmp/plan.md
```

Vault'a **hiçbir şey** yazılmaz (manifest dahil). Çıktı: not sayıları, tür
dağılımı, planlanan hedef yollar, çakışmalar, ek sayısı/boyutu.

### 3.2 Apply

```bash
python -m app.scripts.migrate_notes_to_vault --apply
```

Sıra:

1. Preflight (kritik blocker varsa durur)
2. Kaynak anlık görüntüsü (salt-okunur `REPEATABLE READ, READ ONLY` transaction)
3. Tüm hedef yolların ve ek adlarının planlanması
4. Manifest planının yazılması (her not `planned`)
5. Eklerin kopyalanması → canvas yan dosyaları → not dosyaları (her notta manifest atomik güncellenir)
6. Vault indeksinin tazelenmesi + kimlik tekilliği kontrolü
7. Kaynak parmak izinin yeniden hesaplanması (before == after olmalı)
8. `report.md` + `errors.json`

### 3.3 Verify

```bash
python -m app.scripts.migrate_notes_to_vault --verify
```

Her not için kimlik, gövde, metadata, ek ve canvas kontrolü yeniden yapılır;
Vault indeksi tazelenir ve `READY_FOR_CUTOVER` kararı verilir.

---

## 4. Resume (kesintiye dayanıklılık)

Migration her nottan sonra manifest'i atomik yazar. Kesinti olursa:

```bash
python -m app.scripts.migrate_notes_to_vault --apply   # aynı komut
```

- `copied` durumunda kalan notlar doğrulanıp `verified`'a yükseltilir.
- Zaten yazılmış dosyalar **yeniden kullanılır** (`skipped_existing`).
- Kopyalanmış ekler içerik özetiyle eşleşirse yeniden kullanılır; ikinci kopya oluşmaz.

Yeni komut yok, yeni bayrak yok: aynı `--apply` devam eder.

---

## 5. Durumlar ve anlamları

| Durum | Anlamı | Operatör aksiyonu |
|---|---|---|
| `verified` | Bu turda yazıldı ve doğrulandı | — |
| `skipped_existing` | Dosya zaten vardı ve içerik beklenenle aynı | — |
| `diverged` | Dosya var ama içerik beklenenden farklı (kullanıcı düzenlemiş ya da kaynak değişmiş) | Elle incele; migration ÜZERİNE YAZMAZ |
| `failed` | Ek eksik/bozuk ya da doğrulama hatası | Kaynağı düzelt, tekrar `--apply` |
| `blocked` | Preflight blocker'ı (kimlik çakışması, geçersiz metadata) | Vault'u düzelt, tekrar çalıştır |
| `planned` | Yalnızca dry-run / apply henüz bu nota gelmedi | — |

---

## 6. Çakışmalar

- **Aynı taban yol** (iki not aynı başlık/klasör): `Başlık--a1b2c3d4.md` (id soneki deterministiktir, `(1)` gibi sıraya bağlı ad ÜRETİLMEZ).
- **Vault'ta yönetilmeyen dosya** (kullanıcının kendi notu): üzerine yazılmaz; migration id sonekli yolu kullanır.
- **Aynı `forkos_id`** iki managed dosyada: fail-closed; apply hiç başlamaz.
- **Ek adı çakışması**: aynı ad, farklı içerik → `Attachments/ek--<sha8>.png`; aynı içerik → tek dosya.

---

## 7. Rollback semantiği

Bu fazda **yıkıcı rollback gerekmez**: kaynak forkOS verisi hiç değişmez
(parmak izi before == after ile kanıtlanır).

Vault kopyasını geri almak istenirse, yalnızca manifest'in kaydettiği
dosyalar silinir:

```text
.forkos-migration/notes-v1/manifest.json
  notes.<uuid>.target_path
  notes.<uuid>.attachments[].vault_path
  notes.<uuid>.canvas.sidecar_path
```

Kurallar:

- Bu temizlik **otomatik çalışmaz**; elle ve kullanıcı onayıyla yapılır.
- Yönetilmeyen (manifest'te olmayan) hiçbir dosya silinmez.
- `diverged` işaretli dosyalar silinmez — kullanıcı verisi olabilir.

---

## 8. Manifest dizini

```text
<Vault>/.forkos-migration/notes-v1/
├── manifest.json   # not → hedef yol, özetler, ekler, canvas, durum
├── report.md       # insan okunur global rapor
└── errors.json     # blocker ve hata listesi
```

Gizli dizin olduğu için Vault tarayıcısı ve Obsidian graf/arama kapsamı dışındadır.

---

## 9. Doğrulama kontrol listesi

- [`SOURCE_FINGERPRINT_BEFORE` == `SOURCE_FINGERPRINT_AFTER`](manifest.json)
- [`READY_FOR_CUTOVER`](../..) `= YES`
- `notes_verified == source_total_notes`
- `attachments_failed == 0`, `canvas_count == canvas_verified`
- `diverged == 0`, `failed == 0`, `blocked == 0`
- Vault indeksi: çakışma 0, geçersiz metadata 0

Bir satır tutmuyorsa `--apply`/`--verify` çıktısındaki ilgili hata satırını
`errors.json` içinde bulup düzeltin; kaynak veriye dokunmayın.
