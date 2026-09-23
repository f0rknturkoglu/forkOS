"""A4: Semantic Promotion & Durable Memory modülü.

Aday yönetimi, inceleme ve kontrollü terfi katmanı.
"""

from app.modules import ModuleSpec
from app.modules.semantic_memory.router import router

MODULE = ModuleSpec(
    id="agent_semantic",
    title="Agent Semantic Memory",
    router=router,
    event_verbs=["semantic_candidate.promoted"],
)
