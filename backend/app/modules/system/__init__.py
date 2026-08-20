from app.modules import ModuleSpec
from app.modules.system.router import router

MODULE = ModuleSpec(id="system", title="Settings", router=router)
