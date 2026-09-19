import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { LocateFixed } from "lucide-react";
import { Button, cx } from "@/core/ui";
import { appTimeParts, formatAppDate } from "@/lib/date";
import { useWeather, weatherIcon, weatherLabel } from "./weather";

function greeting(hour: number): string {
  if (hour < 5) return "İyi geceler";
  if (hour < 12) return "Günaydın";
  if (hour < 18) return "İyi günler";
  return "İyi akşamlar";
}

/**
 * Panelin ust seridi: saat + tarih + hava + gunun sayilari, TEK kutuda.
 *
 * Hepsi "su an nerdeyiz" sorusunun parcasi; ayri seritlerde durduklarinda
 * panelin ustunde ust uste iki-uc bant olusuyordu.
 *
 * Arama BURADA YOK: çalışma alanı başlığındaki arama her sayfada duruyor,
 * ikincisi ayni ekranda iki kutu demekti.
 *
 * Saat ve hava bilincli olarak sutunlarin disinda ve tek bir blokta: ikisi de
 * "su an" bilgisi, listelerin arasina serpistirilince hem yerleri her modul
 * eklemesinde kayiyordu hem de birbirinden kopuyordu.
 */
export function TodayHero({ metrics = [] }: { metrics?: ReactNode[] }) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    // Saat DAKIKA gosterir; saniyelik guncelleme hava durumu panelini ve
    // metrik karolarini her saniye yeniden render ediyordu. Dakika sinirinda
    // bir kez guncellemek hem dogru hem bedava (SLEEP'e kadar bos).
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
    <header className="mb-5 rounded-card border border-subtle bg-surface px-4 py-3.5 shadow-card">
      <div className="flex flex-wrap items-end gap-x-8 gap-y-4">
        <div className="min-w-0 shrink-0">
          <p className="label-caps">{greeting(hour)}</p>
          <div className="mt-1.5 flex items-baseline gap-3">
            <time
              dateTime={now.toISOString()}
              className="numeral text-display-lg leading-none tracking-[-0.02em] text-primary"
            >
              {time}
            </time>
            <span className="truncate text-body text-secondary">{date}</span>
          </div>
        </div>

        <WeatherPanel />

        {metrics.length > 0 && (
          /*
           * Sayilar saatin sagina yaslanir, dar ekranda alt satira iner.
           * Metric kendi ic bosluguyla gelir; burada onu sifirlayip
           * rakami saatin (44px) yaninda ezilmeyecek boya cekiyoruz.
           */
          <div
            className={cx(
              "grid w-full shrink-0 grid-cols-2 gap-x-6 gap-y-3 border-t border-subtle pt-3.5",
              "sm:ml-auto sm:w-auto sm:grid-cols-4 sm:border-t-0 sm:pt-0",
              "[&>*]:min-w-[104px] [&>*]:px-0 [&>*]:py-0 [&_.numeral]:text-title",
            )}
          >
            {metrics}
          </div>
        )}
      </div>
    </header>
  );
}

/** Saatin yanindaki hava blogu: su anki durum + uc gunluk ince serit. */
function WeatherPanel() {
  const { coords, data, isError, refetch, asking, denied, place, requestLocation } = useWeather();

  if (!coords) {
    return (
      <div className="flex items-center gap-2.5 text-meta text-muted sm:border-l sm:border-subtle sm:pl-8">
        <span>{denied ? "Konum izni yok — Ayarlar'dan şehir gir." : "Hava durumu için konum gerekli."}</span>
        <button
          type="button"
          onClick={requestLocation}
          disabled={asking}
          className="flex items-center gap-1.5 border-b border-accent-border text-accent disabled:opacity-50"
        >
          <LocateFixed size={13} />
          {asking ? "izin isteniyor…" : "konumumu kullan"}
        </button>
      </div>
    );
  }

  const current = data?.current;
  const daily = data?.daily;
  if (isError) {
    return (
      <div className="flex items-center gap-2 text-meta text-muted sm:border-l sm:border-subtle sm:pl-8">
        <span>Hava durumu alınamadı.</span>
        <Button size="sm" variant="ghost" onClick={() => void refetch()}>
          Yeniden dene
        </Button>
      </div>
    );
  }
  if (!current) {
    return <div className="text-meta text-muted sm:border-l sm:border-subtle sm:pl-8">Hava yükleniyor…</div>;
  }

  const Icon = weatherIcon(current.weather_code);

  return (
    <div className="flex items-center gap-5 sm:border-l sm:border-subtle sm:pl-8">
      <div className="flex items-center gap-3">
        <Icon size={30} strokeWidth={1.4} className="shrink-0 text-secondary" />
        <div>
          <p className="numeral text-display leading-none text-primary">{Math.round(current.temperature_2m)}°</p>
          <p className="mt-1 text-meta text-secondary">{weatherLabel(current.weather_code)}</p>
        </div>
      </div>

      {daily && (
        <ul className="hidden items-stretch gap-4 lg:flex">
          {daily.time.slice(0, 4).map((day, index) => {
            const DayIcon = weatherIcon(daily.weather_code[index]);
            const today = index === 0;
            return (
              <li key={day} className="text-center">
                <p className={cx("text-micro uppercase tracking-[0.08em]", today ? "text-accent" : "text-muted")}>
                  {today ? "bugün" : formatAppDate(day, { weekday: "short" })}
                </p>
                <DayIcon size={15} strokeWidth={1.5} className="mx-auto my-1 text-icon" />
                <p className="numeral text-micro text-secondary">
                  {Math.round(daily.temperature_2m_min[index])}°
                  <span className="text-primary"> {Math.round(daily.temperature_2m_max[index])}°</span>
                </p>
              </li>
            );
          })}
        </ul>
      )}

      <p className="hidden self-end text-meta text-muted xl:block">
        nem %{current.relative_humidity_2m}
        {place && ` · ${place}`}
      </p>
    </div>
  );
}
