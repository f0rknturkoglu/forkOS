/**
 * Renkler CSS degiskeninden okunur (src/index.css). Buraya HEX yazma —
 * yazarsan tema degistiginde o deger sabit kalir ve koyu temada patlar.
 */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: ["class", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        canvas: "var(--canvas)",
        sidebar: "var(--sidebar)",
        scrim: "var(--overlay-scrim)",
        surface: {
          DEFAULT: "var(--surface)",
          sunken: "var(--surface-sunken)",
          hover: "var(--surface-hover)",
          raised: "var(--surface-raised)",
          selected: "var(--surface-selected)",
        },
        subtle: "var(--border)",
        strong: "var(--border-strong)",
        primary: "var(--text)",
        secondary: "var(--text-secondary)",
        muted: "var(--text-muted)",
        icon: "var(--icon)",
        accent: {
          DEFAULT: "var(--accent)",
          surface: "var(--accent-surface)",
          border: "var(--accent-border)",
        },
        ok: {
          DEFAULT: "var(--success)",
          surface: "var(--success-surface)",
          border: "var(--success-border)",
        },
        warn: {
          DEFAULT: "var(--warning)",
          surface: "var(--warning-surface)",
          border: "var(--warning-border)",
        },
        danger: {
          DEFAULT: "var(--danger)",
          surface: "var(--danger-surface)",
          border: "var(--danger-border)",
        },
        // Okuma akisindaki kaynak renkleri -- semantik degil, marka.
        feed: {
          rss: "var(--feed-rss)",
          hn: "var(--feed-hn)",
          reddit: "var(--feed-reddit)",
          gh: "var(--feed-gh)",
        },
        // Emek haritasi basamaklari -- semantik degil; 0..4 yogunluk kademesi.
        // index.css'teki --heat-N degiskenlerine bagli (Faz 8: kaldirilmis,
        // Heatmap STEP_BG siniflarinin uretilememesine yol aciyordu).
        heat: {
          0: "var(--heat-0)",
          1: "var(--heat-1)",
          2: "var(--heat-2)",
          3: "var(--heat-3)",
          4: "var(--heat-4)",
        },
      },
      borderColor: { DEFAULT: "var(--border)" },
      fontFamily: {
        sans: ['"Manrope Variable"', "ui-sans-serif", "system-ui", "sans-serif"],
        // Manrope: ana ürün UI ve kontrolleri. Newsreader: editoryal okuma bağlamları (BookmarkReaderModal).
        serif: ['"Newsreader Variable"', "Georgia", "serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      fontSize: {
        // Tek tip olcek. text-[11px] gibi keyfi deger yazma.
        micro: ["10px", { lineHeight: "12px", letterSpacing: "0.16em" }],
        meta: ["12.5px", { lineHeight: "18px" }],
        body: ["13.5px", { lineHeight: "20px" }],
        heading: ["15px", { lineHeight: "20px", fontWeight: "600" }],
        title: ["20px", { lineHeight: "26px", letterSpacing: "-0.01em" }],
        score: ["48px", { lineHeight: "1", letterSpacing: "-0.04em" }],
        display: ["30px", { lineHeight: "34px", letterSpacing: "-0.02em" }],
        // Sayisal ozetler (Metric/Stat) ve buyuk hero/timer rakamlari.
        // Keyfi text-[Npx] yazmak yerine bu adimlar kullanilir.
        "numeral-lg": ["24px", { lineHeight: "28px" }],
        "numeral-xl": ["26px", { lineHeight: "30px" }],
        "display-lg": ["40px", { lineHeight: "44px", letterSpacing: "-0.02em" }],
        "display-xl": ["56px", { lineHeight: "60px", letterSpacing: "-0.02em" }],
        "display-2xl": ["72px", { lineHeight: "76px", letterSpacing: "-0.02em" }],
      },
      borderRadius: { DEFAULT: "0.25rem", sm: "0.125rem", control: "6px", card: "8px", overlay: "12px" },
      spacing: {
        control: "34px",
        touch: "44px",
        sidebar: "248px",
        rail: "56px",
        "workspace-header": "52px",
        "workspace-body": "var(--workspace-body-height)",
      },
      gridTemplateColumns: {
        "workspace-rail": "var(--workspace-rail-width) minmax(0, 1fr)",
        "workspace-wide-rail": "var(--workspace-list-width) minmax(0, 1fr)",
        "workspace-inspector": "minmax(0, 1fr) var(--workspace-inspector-width)",
        "workspace-three": "var(--workspace-rail-width) minmax(0, 1fr) var(--workspace-inspector-width)",
        "workspace-wide-three": "var(--workspace-list-width) minmax(0, 1fr) var(--workspace-inspector-width)",
        "workspace-reader": "var(--workspace-rail-width) var(--workspace-list-width) minmax(0, 1fr)",
      },
      minWidth: {
        "calendar-month": "35rem",
        "calendar-week": "47.5rem",
      },
      // Katman skalasi: z-10/z-40 gibi keyfi deger yerine anlamli adlar.
      // sticky < header < popover < drawer < modal < toast < fullscreen.
      zIndex: {
        sticky: "10", // sayfa ici yapiskan toolbar/filtre barlari
        header: "20", // ana navigasyon basligi (dropdown'lari birlikte tasir)
        popover: "30", // menu/popover/dropdown/otomatik tamamlama
        drawer: "40", // saga acilan detay cekmecesi
        modal: "50", // ortali diyalog/palet/hizli yakala
        toast: "60", // sistem bildirimleri (diyaloglarin USTUNDE olmali)
        fullscreen: "70", // gecici tam ekran katmani (FocusMode, DropCapture)
      },
      boxShadow: {
        // V3 ölçeği; xs V3 sürümünde görünüm üretmiyordu.
        xs: "none",
        sm: "0 1px 2px 0 rgb(0 0 0 / 0.05)",
        DEFAULT: "0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)",
        // Katman yuzeyleri (komut paleti, popover).
        overlay: "0 24px 60px -20px rgb(9 11 15 / 0.30)",
        // Kutular: kenarligi destekleyen, sakin ve anca secilen bir kabartma.
        card: "0 1px 2px 0 rgb(0 0 0 / 0.03)",
        // Yalniz floating toolbar, popover ve denetci gibi yukseltilmis katmanlar.
        raised: "0 12px 36px -16px rgb(9 11 15 / 0.24)",
      },
    },
  },
  plugins: [],
};
