"""Tamamlanmis konulari tekrar kuyruguna alir (geriye donuk veri).

0048 yeni SRS kolonlarini ekledi ama mevcut kayitlarda `next_review_at` bos
kaldi; bu yuzden 490 konuluk gercek veride tekrar kuyrugu bos gorunuyordu.
Kural: ogrenilmis (`status='done'`) ve en az bir kez calisilmis konular icin
ilk tekrar tarihi = son calisma + 7 gun (gecmisse hemen tekrar edilebilir).

Idempotent: yalnizca `next_review_at is null` satirlara dokunur.
"""

from alembic import op

revision = "0049_learning_review_backfill"
down_revision = "0048_learning_workspace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        update study_topic
           set next_review_at = coalesce(last_studied_at, now()) + interval '7 days'
         where status = 'done'
           and next_review_at is null
        """
    )


def downgrade() -> None:
    # Geri donuste yalnizca bu migration'in urettigi degerleri tahmin ederek
    # silmek riskli olurdu; kolon 0048 downgrade'inde tamamen duser.
    pass
