"""Secret ayar siniflandirmasi -- TEK kaynak (Faz 15).

Yedek/export/import ayni politikayi buradan alir. Siniflandirma isimde
"key" gecmesine guvenmez; acik liste kullanilir. Yeni bir secret ayar
eklenirken key BU listeye yazilmalidir -- koruyan test
`tests/test_backup_secrets.py` kod taramasindan gecirir ve yedek
payload'inda hicbir secret key'in bulunmadigini dogrular.

Eski yedekler OTOMATIK olarak guvenli hale gelmez: iclerinde secret satir
varsa restore/import bunlari atlar, ama diskte kalan dosya hala icerir.
Gecmis yedeklerdeki anahtarlarin dondurulmesi (rotation) onerilir.
"""

SECRET_SETTING_KEYS: frozenset[str] = frozenset(
    {
        # Authorization is not portable data: a backup must never grant cloud access.
        "hermes.goal_studio.consent.v1",
        "media.tmdb_key",
        "media.google_books_key",
        "media.igdb_client_id",
        "media.igdb_client_secret",
        # RAWG artik arayuzde yok (IGDB oyun aramasini devraldi) ama eski
        # kayitlarda anahtar kalmis olabilir; yedekten yine dislanir.
        "media.rawg_key",
    }
)


def is_secret_setting(key: str) -> bool:
    """Bir `setting` anahtari yedekten dislanmali mi?"""
    return key in SECRET_SETTING_KEYS
