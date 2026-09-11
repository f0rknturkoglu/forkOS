"""Pomodoro seansi medyaya aktarilinca "yalniz sure" kaydi icin 'session' eylemi.

Sure kaydi ilerlemeyi artirmaz; ayri bir eylem degeri bunu semada da
garantiler (amount 0 kalir, etkinlik sayaclari ilerleme bazli kaldigi icin
cift sayim olmaz).
"""

from alembic import op

revision = "0047_media_session_action"
down_revision = "0046_skill_match_ratio"
branch_labels = None
depends_on = None

#: Eski kisit (0026_media_domain.py) ile ayni liste + 'session'.
_ACTIONS = "'quick','set','complete_unit','uncomplete_unit','finish'"


def upgrade() -> None:
    op.execute("alter table media_consumption drop constraint media_consumption_action_check")
    op.execute(
        "alter table media_consumption add constraint media_consumption_action_check "
        f"check (action in ({_ACTIONS},'session'))"
    )


def downgrade() -> None:
    # 'session' satirlari yeni eylem degerini tasiyamayacagi icin once onlar
    # temizlenir; entity silinince media_consumption CASCADE ile duser, aksi
    # halde kisit geri eklenirken migration patlar.
    op.execute(
        "delete from entity where id in (select id from media_consumption where action = 'session')"
    )
    op.execute("alter table media_consumption drop constraint media_consumption_action_check")
    op.execute(
        "alter table media_consumption add constraint media_consumption_action_check "
        f"check (action in ({_ACTIONS}))"
    )
