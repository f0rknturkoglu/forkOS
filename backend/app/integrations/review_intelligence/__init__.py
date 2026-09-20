"""H5 gözden geçirme zekâsı (review intelligence).

Süreklilik, delta, gözden geçirme ve konsolidasyon **adayları** üretir; hiçbir
şey yazmaz. Kanonik kaynaklar (Review, Event, son tarihler, günlük notlar, H3
kanıtı) sınırlı biçimde okunur, H4 isteğe bağlı olarak devreye girer ve her
olgusal iddia kaynak referansı taşır.
"""

from app.integrations.review_intelligence.service import review_intelligence

__all__ = ["review_intelligence"]
