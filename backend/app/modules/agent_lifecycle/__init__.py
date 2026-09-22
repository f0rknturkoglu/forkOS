"""Agent oturum gözlemleri; aranabilir bir domain nesnesi değildir."""

from app.modules import ModuleSpec
from app.modules.agent_lifecycle.router import router

MODULE = ModuleSpec(id="agent_lifecycle", title="Agent lifecycle", router=router)
