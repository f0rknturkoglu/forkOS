# Hermes oturum yaşam döngüsü köprüsü (A1)

Bu köprü Hermes'in oturum başlangıcı, sonraki turları ve kapanışını forkOS'ta
yalnızca **içeriksiz metadata** olarak saklar. MCP'nin 29 aracı ajan tarafından
bilinçli okuma/yazma için kullanılır; bu köprü ise model döngüsünün dışındaki
Hermes host olaylarını `POST /api/agent/lifecycle/event` adresine iletir. Yeni
MCP aracı, arka plan süreci veya model bağlamı eklemez.

## Olay sözleşmesi

| Hermes hook'u | Koşul | forkOS olayı |
| --- | --- | --- |
| `pre_llm_call` | `is_first_turn=true` | `session_start` (ilk `turn_id` varsa aynı çağrıda sayılır) |
| `pre_llm_call` | sonraki tur | `turn_seen` |
| `on_session_finalize` | Hermes oturumu kapatır | `session_finalize` |

İstek sürüm 1'de `schema_version`, `event`, `harness`, `session_id`, isteğe bağlı
`turn_id` ve en çok 64 karakterlik normalize `platform` içerir. `turn_seen` için
`turn_id` zorunludur. Şema ek alanları reddeder. Plugin `user_message`, geçmiş,
model yanıtı, araç argümanı/çıktısı, prompt veya Vault içeriği göndermez ve
hook'tan daima `None` döndürür. Raw oturum/tur kimlikleri yalnızca isteğin
işlenmesi sırasında domain-separated SHA-256 anahtarlarına çevrilir; veritabanı
ve durum endpoint'i yalnızca özetlenmiş kimlikler, zamanlar, durum ve sayaç tutar.

`agent_session` ve `agent_session_turn` mevcut PostgreSQL içindeki destek
tablolarıdır. `session_key` ve `(session_id, turn_key)` eşsizdir. Tek transaction
içindeki satır kilidi, tekil tur eklemesi ve sayaç güncellemesi aynı turun
eşzamanlı/tekrarlı tesliminde çift sayımı önler. Başlangıç gözlenmeden gelen tur
veya kapanış kayıt altına alınır; `start_seen_at` boş kalır. Kapanan oturum yeni
turu reddeder (`LIFECYCLE_ALREADY_FINALIZED`), sessizce yeniden açmaz. Tekrarlı
kapanış güvenlidir.

`GET /api/agent/lifecycle/status` son gözlem zamanı, aktif oturum sayısı ve
eksik başlangıç sayısını verir. Bu, **Hermes'in şu an bağlı olduğunun kanıtı
değildir**; yalnızca forkOS'un daha önce olay gördüğünü söyler. Ayarlar'daki
“Oturum devamlılığı” satırı da aynı ayrımı korur.

## Kurulum

Kaynak repo içindeki `tools/hermes/forkos-lifecycle/` dizinidir. Kurulu Hermes
profilinin `HERMES_HOME` değişkenini kullanın; ayarlanmamışsa Hermes'in varsayılanı
`~/.hermes` kullanılır.

```bash
python3 scripts/install_hermes_lifecycle.py
hermes plugins enable forkos-lifecycle --no-allow-tool-override
hermes plugins list
```

Kurucu yalnızca kendi `.forkos-managed.json` işaretli eklentisini günceller;
yönetilmeyen veya yerelde değiştirilmiş aynı adlı dizini ezmez. Hermes'in
ürettiği standart Python `__pycache__` dosyalarını güncellemede temizler.
`plugins enable` öncesinde profil `config.yaml` dosyasının özel izinli, zaman damgalı yedeğini
alın. Komut model/sağlayıcı, MCP trust, skill veya diğer plugin ayarlarını
değiştirmez. Hermes işlemine yeni plugin'i yükletmek için o işlemi yeniden
başlatın. Eklenti varsayılan olarak `http://127.0.0.1:8787` adresine gider;
`FORKOS_LIFECYCLE_BASE_URL` yalnızca `http` ve `127.0.0.1`, `localhost`, `::1`
hostlarını kabul eder. Başka bir host, yönlendirme veya uzak servis yoktur.

## Doğrulama ve sınırlar

Test veritabanında `make test CO="docker compose"` migration, tekrarlı/eşzamanlı
teslim, sıra bozukluğu, gizlilik ve plugin'in hata durumlarını sınar. Gerçek
Hermes doğrulamasında yeni oturumun ilk turundan sonra `turn_count=1`, ikinci
turundan sonra `turn_count=2`, gerçek kapatma işleminden sonra `finalized_at`
dolu olmalıdır. Kurulu Hermes v0.21.3'te CLI `/exit` ve tek atımlık oturumun
normal bitişi finalize hook'unu ateşler. Masaüstü uygulamasında yalnızca
pencereyi kapatmak oturumu finalize etmez; o oturum hâlâ sürdürülmek üzere
durabilir. Bir sonraki oturumun özetlenmiş anahtarı farklıdır. forkOS
ulaşılamazsa hook kısa bir yerel timeout ile hata kaydeder ve Hermes konuşmasını
engellemez; hot path'te tekrar deneme yoktur. Bu nedenle ulaşamama sırasında
olay kaybı mümkündür ve durum endpoint'i kesintisiz gözlem garantisi vermez.

A1 hiçbir operasyonel varlığı, `event` günlüğünü, `90 Agent/Memory` içeriğini
veya Vault dosyasını değiştirmez. Alt ajan oturumu da yalnızca anonim yaşam
döngüsü metadata'sıdır.

## A1.1 Sertleştirmesi (Hardening)

1. **Kaynak Değişmezliği İnvariantı (`A1.1.1`):**
   `test_agent_lifecycle_invariants.py` testiyle; tüm yaşam döngüsü çağrılarının (`session_start`, `turn_seen`, `session_finalize`, duplicate çağrılar) 17 operasyonel veritabanı tablosu (`Entity`, `Event`, `Link`, `Todo`, `Project`, `Opportunity`, vb.) ve Vault/sıcak bellek dosyaları üzerinde **kesinlikle 0 mutasyon** yaptığı doğrulanır.
2. **Katı 2xx Başarı Semantiği (`A1.1.2`):**
   Hermes eklentisinde yalnızca `200 <= response.status < 300` durum kodları başarı kabul edilir; 3xx/4xx/5xx durumlarında `_send` `OSError` yükseltir ve eklenti fail-open çalışarak Hermes oturumunu asla çökertmez (`test_hermes_lifecycle_plugin.py`).
Oturum başlangıcı ve sonraki turlarda bütçeli bağlam enjeksiyonu ve kaynak devamlılığı için [A2 — Bootstrap & Continuity](a2-bootstrap-continuity.md) dokümanına bakın.
