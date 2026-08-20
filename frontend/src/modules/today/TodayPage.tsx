import { allTodayStats, allTodayWidgets } from "@/core/registry";

export function TodayPage() {
  const stats = allTodayStats();
  const widgets = allTodayWidgets();
  const today = new Date().toLocaleDateString("tr-TR", {
    weekday: "long", day: "numeric", month: "long", year: "numeric",
  });

  return (
    <div className="p-6">
      <header className="mb-4">
        <h1 className="text-xl font-semibold">Today</h1>
        <p className="text-xs text-neutral-500">{today}</p>
      </header>

      {/* Kutucuklar ve widget'lar modullerden gelir -- Today hicbir modulu bilmez */}
      {stats.length > 0 && (
        <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
          {stats.map((Tile, i) => (
            <Tile key={i} />
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {widgets.map((Widget, i) => (
          <Widget key={i} />
        ))}
        {widgets.length === 0 && (
          <p className="text-sm opacity-60">Henuz widget kayitli degil.</p>
        )}
      </div>
    </div>
  );
}
