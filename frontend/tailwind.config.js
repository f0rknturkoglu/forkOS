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
        surface: {
          DEFAULT: "var(--surface)",
          sunken: "var(--surface-sunken)",
          hover: "var(--surface-hover)",
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
        // Grafik paleti -- kategorik dagilimlar; sabit sirayla atanir.
        chart: {
          1: "var(--chart-1)",
          2: "var(--chart-2)",
          3: "var(--chart-3)",
          4: "var(--chart-4)",
          5: "var(--chart-5)",
          6: "var(--chart-6)",
          7: "var(--chart-7)",
          8: "var(--chart-8)",
        },
        // Medya türleri -- her türün kimlik rengi (chip, rozet, vurgu).
        kind: {
          movie: "var(--kind-movie)",
          show: "var(--kind-show)",
          anime: "var(--kind-anime)",
          manga: "var(--kind-manga)",
          book: "var(--kind-book)",
          audiobook: "var(--kind-audiobook)",
          podcast: "var(--kind-podcast)",
          music: "var(--kind-music)",
          game: "var(--kind-game)",
        },
      },
      borderColor: { DEFAULT: "var(--border)" },
      fontFamily: {
        sans: ['"IBM Plex Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
        serif: ['"Newsreader Variable"', "Newsreader", "Georgia", "serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      fontSize: {
        // Tek tip olcek. text-[11px] gibi keyfi deger yazma.
        micro: ["10px", { lineHeight: "12px", letterSpacing: "0.16em" }],
        meta: ["12.5px", { lineHeight: "18px" }],
        body: ["13.5px", { lineHeight: "20px" }],
        heading: ["15px", { lineHeight: "20px", fontWeight: "600" }],
        title: ["20px", { lineHeight: "26px", letterSpacing: "-0.01em" }],
        display: ["30px", { lineHeight: "34px", letterSpacing: "-0.02em" }],
        // Sayisal ozetler (Metric/Stat) ve buyuk hero/timer rakamlari.
        // Keyfi text-[Npx] yazmak yerine bu adimlar kullanilir.
        "numeral-lg": ["24px", { lineHeight: "28px" }],
        "numeral-xl": ["26px", { lineHeight: "30px" }],
        "display-lg": ["40px", { lineHeight: "44px", letterSpacing: "-0.02em" }],
        "display-xl": ["56px", { lineHeight: "60px", letterSpacing: "-0.02em" }],
        "display-2xl": ["72px", { lineHeight: "76px", letterSpacing: "-0.02em" }],
      },
      borderRadius: { control: "4px", card: "5px", overlay: "6px" },
      borderRadius: { control: "4px", card: "5px", overlay: "6px" },
      spacing: { control: "34px", touch: "44px" },
      boxShadow: {
        // Katman yuzeyleri (komut paleti, popover).
        overlay: "0 24px 60px -20px rgb(9 11 15 / 0.30)",
        // Kutular: kenarligi destekleyen, anca secilen bir kabartma.
        card: "0 1px 2px 0 rgb(9 11 15 / 0.04)",
      },
    },
  },
  plugins: [],
};
