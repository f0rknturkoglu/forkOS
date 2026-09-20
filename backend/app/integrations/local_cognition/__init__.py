"""H4 yerel bilis (Local Cognition) router'i.

Hermes hangi bilişsel primitife ihtiyaç duyduğuna karar verir; H4 bunu yerel,
sınırlı ve incelenebilir biçimde yürütür. Model önerir, deterministik
doğrulayıcı kabul eder, zincir tükenirse `needs_escalation` döner.

H4 hiçbir doğruluğa sahip değildir ve hiçbir yazma yapmaz.
"""

from app.integrations.local_cognition.service import run_local_cognition

__all__ = ["run_local_cognition"]
