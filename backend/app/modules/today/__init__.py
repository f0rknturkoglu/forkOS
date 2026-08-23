from app.modules import ModuleSpec
from app.modules.today.router import router

MODULE = ModuleSpec(id="today", title="Today Agenda", router=router)
