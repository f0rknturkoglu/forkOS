from app.modules import EntityTypeSpec, ModuleSpec
from app.modules.learning.router import router

MODULE = ModuleSpec(
    id="learning",
    title="Learning",
    router=router,
    entity_types=[EntityTypeSpec('course', 'Kurs', 'Kurslar', '/learning', 'GraduationCap'),
        EntityTypeSpec('book', 'Kitap', 'Kitaplar', '/learning', 'Book')],
    event_verbs=["course.progressed", "course.completed", "book.finished"],
)
