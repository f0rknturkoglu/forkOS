import { useEffect, useState } from "react";
import { LocateFixed } from "lucide-react";
import { Button } from "@/core/ui";
import { appTimeParts, formatAppDate } from "@/lib/date";
import { useWeather, weatherIcon, weatherLabel } from "./weather";

function greeting(hour: number): string {
  if (hour < 5) return "İyi geceler";
  if (hour < 12) return "Günaydın";
  if (hour < 18) return "İyi günler";
  return "İyi akşamlar";
}

/** Tarih ve hava çalışma gününe bağlam verir; planın üstünde büyük kart kurmaz. */
export function TodayHero() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    let timer = 0;
    const schedule = () => {
      const current = new Date();
      const delay = (60 - current.getSeconds()) * 1000 - current.getMilliseconds() + 50;
      timer = window.setTimeout(() => {
        setNow(new Date());
        schedule();
      }, delay);
    };
    schedule();
    return () => window.clearTimeout(timer);
  }, []);

  const { hour, minute } = appTimeParts(now);
  const time = `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
  const date = formatAppDate(now, { weekday: "long", day: "numeric", month: "long" });

  return (
    <header className="mb-6 flex flex-wrap items-center justify-between gap-x-5 gap-y-2 border-b border-subtle pb-4">
      <div className="flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-1">
        <p className="text-title font-medium text-primary">{greeting(hour)}</p>
        <span className="text-body text-secondary">{date}</span>
        <time dateTime={now.toISOString()} className="tabular-nums text-meta text-muted">
          {time}
        </time>
      </div>
      <WeatherPanel />
    </header>
  );
}

function WeatherPanel() {
  const { coords, data, isError, refetch, asking, denied, place, requestLocation } = useWeather();

  if (!coords) {
    return (
      <div className="flex items-center gap-2 text-meta text-muted">
        <span>{denied ? "Konum izni yok — Ayarlar'dan şehir gir." : "Hava durumu için konum gerekli."}</span>
        <Button size="sm" variant="ghost" onClick={requestLocation} disabled={asking}>
          <LocateFixed size={13} /> {asking ? "İzin isteniyor…" : "Konumumu kullan"}
        </Button>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center gap-2 text-meta text-muted">
        <span>Hava durumu alınamadı.</span>
        <Button size="sm" variant="ghost" onClick={() => void refetch()}>
          Yeniden dene
        </Button>
      </div>
    );
  }

  const current = data?.current;
  if (!current) return <span className="text-meta text-muted">Hava yükleniyor…</span>;

  const Icon = weatherIcon(current.weather_code);
  const daily = data?.daily;
  const forecast = daily?.time.slice(0, 4) ?? [];
  return (
    <details
      className="group relative text-meta text-secondary"
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          event.currentTarget.open = false;
          event.currentTarget.querySelector("summary")?.focus();
        }
      }}
    >
      <summary
        role="button"
        aria-label="Hava durumu ve tahmin"
        title={place ?? undefined}
        className="flex cursor-pointer list-none items-center gap-2 rounded-control px-1 py-1 hover:bg-surface-hover"
      >
        <Icon size={17} strokeWidth={1.5} className="text-icon" />
        <span className="tabular-nums font-medium text-primary">{Math.round(current.temperature_2m)}°</span>
        <span>{weatherLabel(current.weather_code)}</span>
        {place && <span className="hidden text-muted sm:inline">· {place}</span>}
      </summary>
      {daily && forecast.length > 0 && (
        <div className="absolute right-0 top-full z-popover mt-1 w-64 rounded-card border border-subtle bg-surface-raised p-3 shadow-overlay">
          <p className="mb-2 text-meta font-medium text-primary">Dört günlük tahmin</p>
          <div className="space-y-1.5">
            {forecast.map((day, index) => {
              const DayIcon = weatherIcon(daily.weather_code[index]);
              return (
                <div key={day} className="flex items-center gap-2 text-meta">
                  <span className="min-w-12 capitalize">{formatAppDate(`${day}T12:00:00Z`, { weekday: "short" })}</span>
                  <DayIcon size={14} className="text-icon" />
                  <span className="ml-auto tabular-nums">
                    {Math.round(daily.temperature_2m_min[index])}°–{Math.round(daily.temperature_2m_max[index])}°
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </details>
  );
}
