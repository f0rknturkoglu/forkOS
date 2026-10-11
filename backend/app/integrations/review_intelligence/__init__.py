"""H5 gözden geçirme zekâsı (review intelligence).

Süreklilik, delta, gözden geçirme ve konsolidasyon **adayları** üretir; hiçbir
şey yazmaz. Kanonik kaynaklar (Review, Event, son tarihler, günlük notlar, H3
kanıtı) sınırlı biçimde okunur, H4 isteğe bağlı olarak devreye girer ve her
olgusal iddia kaynak referansı taşır.
"""


def __getattr__(name):
    # Schema imports during registry construction must not load registry readers.
    if name == "review_intelligence":
        from app.integrations.review_intelligence.service import review_intelligence

        return review_intelligence
    raise AttributeError(name)


__all__ = ["review_intelligence"]
