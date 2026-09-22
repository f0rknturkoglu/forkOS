"""Agent bağlam devamlılığı; aranabilir bir domain nesnesi değildir."""

from app.modules import ModuleSpec
from app.modules.agent_continuity.router import router

MODULE = ModuleSpec(id="agent_continuity", title="Agent continuity", router=router)
