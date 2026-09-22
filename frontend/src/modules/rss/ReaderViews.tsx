import { navigate } from "@/app/router";
import { Tabs } from "@/core/ui";

/** RSS kaynakları ile birleşik akış aynı okuma ürününün görünümleridir. */
export function ReaderViews({ view }: { view: "feed" | "sources" }) {
  return (
    <Tabs
      value={view}
      onChange={(value) => navigate(value === "sources" ? "/rss" : "/feed")}
      items={[
        { id: "feed", label: "Akış" },
        { id: "sources", label: "RSS Kaynakları" },
      ]}
      ariaLabel="RSS ve akış görünümü"
    />
  );
}
