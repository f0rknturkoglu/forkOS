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
        // Emek haritasi basamaklari.
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
      },
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
