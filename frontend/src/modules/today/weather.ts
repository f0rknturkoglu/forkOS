import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Cloud,
  CloudDrizzle,
  CloudFog,
  CloudLightning,
  CloudRain,
  CloudSnow,
  CloudSun,
  Sun,
  Thermometer,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { api } from "@/core/api";
import { readStored, writeStored } from "@/core/storage";
import { invalidateAfter } from "@/core/invalidation";

interface Forecast {
  current: { temperature_2m: number; weather_code: number; relative_humidity_2m: number };
  daily: {
    time: string[];
    weather_code: number[];
    temperature_2m_max: number[];
    temperature_2m_min: number[];
  };
}

/**
 * WMO hava kodu -> lucide ikonu + Turkce etiket.
 * Emoji kullanilmiyor: emoji her isletim sisteminde baska ciziliyor ve
 * arayuzun geri kalaniyla ayni cizgi kalinligini tutturamiyor.
 */
const WMO: Record<number, [LucideIcon, string]> = {
  0: [Sun, "Açık"],
  1: [CloudSun, "Az bulutlu"],
  2: [CloudSun, "Parçalı bulutlu"],
  3: [Cloud, "Kapalı"],
  45: [CloudFog, "Sisli"],
  48: [CloudFog, "Kırağılı sis"],
  51: [CloudDrizzle, "Hafif çisinti"],
  53: [CloudDrizzle, "Çisinti"],
  55: [CloudDrizzle, "Yoğun çisinti"],
  56: [CloudDrizzle, "Dondurucu çisinti"],
  57: [CloudDrizzle, "Dondurucu yağmur"],
  61: [CloudRain, "Hafif yağmur"],
  63: [CloudRain, "Yağmur"],
  65: [CloudRain, "Şiddetli yağmur"],
  66: [CloudRain, "Dondurucu yağmur"],
  67: [CloudSnow, "Dondurucu sağanak"],
  71: [CloudSnow, "Hafif kar"],
  73: [CloudSnow, "Kar"],
  75: [CloudSnow, "Yoğun kar"],
  77: [CloudSnow, "Kar taneleri"],
  80: [CloudRain, "Hafif sağanak"],
  81: [CloudRain, "Sağanak"],
  82: [CloudLightning, "Şiddetli sağanak"],
  85: [CloudSnow, "Kar sağanağı"],
  86: [CloudSnow, "Yoğun kar sağanağı"],
  95: [CloudLightning, "Gök gürültülü"],
  96: [CloudLightning, "Gök gürültülü, dolu"],
  99: [CloudLightning, "Gök gürültülü, yoğun dolu"],
};

export const weatherIcon = (code: number): LucideIcon => WMO[code]?.[0] ?? Thermometer;
export const weatherLabel = (code: number): string => WMO[code]?.[1] ?? "Bilinmiyor";

interface Coords {
  lat: number;
  lon: number;
}

function readCoord(key: string): number | null {
  const raw = readStored(key);
  if (!raw) return null;
  try {
    const value = Number(JSON.parse(raw));
    return Number.isFinite(value) ? value : null;
  } catch {
    return null;
  }
}

/**
 * Hava durumu backend proxy'si uzerinden gelir (`/api/weather/*`): tarayici
 * open-meteo'ya dogrudan gitmez, dis DNS/IP sizintisi olmaz. Konum tarayici
 * izniyle alinir ve ayarlara yazilir; Ayarlar sayfasindan sehir adiyla da
 * girilebilir.
 */
export function useWeather({ displayed = true } = {}) {
  const preferences = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.get<Record<string, unknown>>("/settings"),
    enabled: displayed,
    staleTime: 60_000,
  });
  const [localCoords, setCoords] = useState<Coords | null>(() => {
    const lat = readCoord("weather.lat");
    const lon = readCoord("weather.lon");
    return lat !== null && lon !== null && Number.isFinite(lat) && Number.isFinite(lon) ? { lat, lon } : null;
  });
  const [asking, setAsking] = useState(false);
  const [denied, setDenied] = useState(false);
  const [place, setPlace] = useState<string | null>(() => readStored("weather.place"));
  const savedLat = preferences.data?.["weather.lat"];
  const savedLon = preferences.data?.["weather.lon"];
  const coords =
    typeof savedLat === "number" &&
    typeof savedLon === "number" &&
    Number.isFinite(savedLat) &&
    Number.isFinite(savedLon) &&
    Math.abs(savedLat) <= 90 &&
    Math.abs(savedLon) <= 180
      ? { lat: savedLat, lon: savedLon }
      : localCoords;

  const { data, isFetching, isError, refetch } = useQuery({
    queryKey: ["weather", coords?.lat, coords?.lon],
    queryFn: () => api.get<Forecast>(`/weather/forecast?lat=${coords!.lat}&lon=${coords!.lon}`),
    enabled: displayed && coords !== null,
    refetchInterval: 30 * 60_000,
    staleTime: 15 * 60_000,
  });

  function requestLocation() {
    if (!navigator.geolocation) {
      setDenied(true);
      return;
    }
    setAsking(true);
    setDenied(false);
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        try {
          const geo = await api.get<{ name: string }>(`/weather/geocode?lat=${lat}&lon=${lon}`);
          const name = geo.name || "Konumum";
          await api.put("/settings/weather.location", { value: name });
          await api.put("/settings/weather.lat", { value: lat });
          await api.put("/settings/weather.lon", { value: lon });
          setPlace(name);
          writeStored("weather.place", name);
          invalidateAfter("settings.write");
        } catch {
          // Konum yazilamadi: hava durumu yine de gosterilir, kalici olmaz.
        }
        writeStored("weather.lat", JSON.stringify(lat));
        writeStored("weather.lon", JSON.stringify(lon));
        setCoords({ lat, lon });
        setAsking(false);
      },
      () => {
        setDenied(true);
        setAsking(false);
      },
      { timeout: 10_000 },
    );
  }

  const savedPlace = preferences.data?.["weather.location"];
  return {
    coords,
    data,
    isFetching,
    isError,
    refetch,
    asking,
    denied,
    place: typeof savedPlace === "string" ? savedPlace : place,
    requestLocation,
  };
}
