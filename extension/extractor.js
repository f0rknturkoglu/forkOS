// Deterministik İş İlanı Çıkarıcı (Schema.org JSON-LD, ATS Seçicileri ve Meta Heuristics)

export function cleanHtmlText(html) {
  if (!html) return "";
  let text = String(html);

  // Satır sonu oluşturan blok etiketleri
  text = text.replace(/<(?:br\s*\/?|\/p|\/div|\/li|\/h[1-6])>/gi, "\n");
  // Tüm HTML etiketlerini temizle
  text = text.replace(/<[^>]+>/g, "");

  // HTML entity dönüşümleri
  text = text
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;|&apos;|&#x27;/g, "'")
    .replace(/&nbsp;/g, " ");

  // Fazla satır ve boşlukları toparla
  const lines = text
    .split("\n")
    .map((l) => l.replace(/[ \t]+/g, " ").trim())
    .filter(
      (l, idx, arr) => l.length > 0 || (idx > 0 && arr[idx - 1].length > 0),
    );

  return lines.join("\n").trim();
}

function parseSalary(baseSalary) {
  if (!baseSalary) return null;
  if (typeof baseSalary === "string") return baseSalary.trim();

  const currency = baseSalary.currency || baseSalary.priceCurrency || "";
  const val = baseSalary.value;

  if (val && typeof val === "object") {
    const min = val.minValue ?? val.min;
    const max = val.maxValue ?? val.max;
    const unit = val.unitText ? ` / ${val.unitText.toLowerCase()}` : "";
    if (min && max) {
      return `${currency ? currency + " " : ""}${min} - ${max}${unit}`.trim();
    }
    if (val.value) {
      return `${currency ? currency + " " : ""}${val.value}${unit}`.trim();
    }
  }

  if (typeof val === "number" || typeof val === "string") {
    return `${currency ? currency + " " : ""}${val}`.trim();
  }

  if (baseSalary.minValue && baseSalary.maxValue) {
    return `${currency ? currency + " " : ""}${baseSalary.minValue} - ${baseSalary.maxValue}`.trim();
  }

  return null;
}

function parseLocation(jobLocation) {
  if (!jobLocation) return null;
  if (typeof jobLocation === "string") return jobLocation.trim();

  if (Array.isArray(jobLocation)) {
    const parts = jobLocation.map(parseLocation).filter(Boolean);
    return parts.join(" | ") || null;
  }

  const addr = jobLocation.address || jobLocation;
  if (typeof addr === "string") return addr.trim();

  if (typeof addr === "object") {
    const parts = [
      addr.addressLocality,
      addr.addressRegion,
      addr.addressCountry?.name || addr.addressCountry,
    ].filter(Boolean);
    if (parts.length > 0) return parts.join(", ");
  }

  return jobLocation.name || null;
}

function detectRemote(text) {
  if (!text) return null;
  const s = text.toLowerCase();
  if (
    s.includes("remote") ||
    s.includes("uzaktan") ||
    s.includes("telecommute")
  ) {
    return "remote";
  }
  if (s.includes("hybrid") || s.includes("hibrit")) {
    return "hybrid";
  }
  if (
    s.includes("onsite") ||
    s.includes("on-site") ||
    s.includes("ofis") ||
    s.includes("yerinde")
  ) {
    return "onsite";
  }
  return null;
}

function detectSalaryFromText(text) {
  if (!text) return null;
  // Örn: $120k - $160k, €80,000 - €100,000, 150.000 TL - 200.000 TL
  const match = text.match(
    /(?:[$€£₺]\s?[\d,.]+\s?[kK]?\s*(?:-|–|ila|to)\s*[$€£₺]?\s?[\d,.]+\s?[kK]?|[\d,.]+\s?[kK]?\s*[-–]\s*[\d,.]+\s?[kK]?\s*[$€£₺]|(?:[$€£₺]\s?[\d,.]+\s?[kK]?))/i,
  );
  return match ? match[0].trim() : null;
}

function parseTitleAndOrg(rawTitle) {
  let title = (rawTitle ?? "").trim();
  let org = "";

  if (title.includes(" at ")) {
    const parts = title.split(" at ");
    title = parts[0].trim();
    org = parts[1].split(/[|\-–]/)[0].trim();
  } else if (title.includes(" - ")) {
    const parts = title.split(" - ");
    title = parts[0].trim();
    org = parts[1].split(/[|\-–]/)[0].trim();
  } else if (title.includes(" | ")) {
    const parts = title.split(" | ");
    title = parts[0].trim();
    org = parts[1].split(/[|\-–]/)[0].trim();
  }

  org = org.replace(/LinkedIn|Jobs|Kariyer|Careers|Hiring/gi, "").trim();
  return { title, org };
}

// 1. KATMAN: Schema.org JSON-LD (JobPosting)
function extractFromJsonLd(doc) {
  const scripts = doc.querySelectorAll('script[type="application/ld+json"]');
  if (!scripts || scripts.length === 0) return null;

  for (const script of scripts) {
    try {
      const data = JSON.parse(script.textContent ?? "");
      const items = Array.isArray(data)
        ? data
        : data["@graph"]
          ? data["@graph"]
          : [data];

      for (const item of items) {
        const type = item["@type"];
        const isJob =
          type === "JobPosting" ||
          (Array.isArray(type) && type.includes("JobPosting"));
        if (!isJob) continue;

        let remote = null;
        if (
          item.jobLocationType === "TELECOMMUTE" ||
          item.jobLocation?.jobLocationType === "TELECOMMUTE"
        ) {
          remote = "remote";
        }

        const fullText = `${item.title || ""} ${item.description || ""} ${JSON.stringify(item.applicantLocationRequirements || "")}`;
        if (!remote) {
          remote = detectRemote(fullText);
        }

        const org =
          typeof item.hiringOrganization === "object"
            ? item.hiringOrganization?.name
            : typeof item.hiringOrganization === "string"
              ? item.hiringOrganization
              : null;

        const location = parseLocation(item.jobLocation);
        const compensation =
          parseSalary(item.baseSalary) || detectSalaryFromText(fullText);
        const notes = cleanHtmlText(item.description);

        return {
          found: true,
          sourceType: "schema_org",
          sourceLabel: "Schema.org (JSON-LD)",
          title: (item.title || "").trim(),
          organization: org ? org.trim() : null,
          location: location || null,
          remote: remote || null,
          compensation: compensation || null,
          deadline_at: item.validThrough || null,
          notes: notes || null,
          raw: item,
        };
      }
    } catch {
      // Geçersiz JSON veya parse hatasını yut ve sonraki script'e geç
    }
  }

  return null;
}

// 2. KATMAN: Popüler ATS ve Kariyer Portalı Seçicileri
function extractFromAts(doc, pageUrl) {
  const url = String(pageUrl || "");

  // Greenhouse
  if (url.includes("greenhouse.io") || doc.querySelector(".app-title")) {
    const titleEl =
      doc.querySelector(".app-title") || doc.querySelector("h1.app-title");
    const orgEl = doc.querySelector(".company-name");
    const locEl = doc.querySelector(".location");
    const descEl =
      doc.querySelector("#content") || doc.querySelector(".content");

    if (titleEl?.textContent?.trim()) {
      const locText = locEl?.textContent?.trim() || "";
      const descText = cleanHtmlText(descEl?.innerHTML || descEl?.textContent);
      return {
        found: true,
        sourceType: "ats",
        sourceLabel: "Greenhouse ATS",
        title: titleEl.textContent.trim(),
        organization: orgEl?.textContent?.trim() || null,
        location: locText || null,
        remote: detectRemote(`${titleEl.textContent} ${locText} ${descText}`),
        compensation: detectSalaryFromText(descText),
        deadline_at: null,
        notes: descText || null,
        raw: { ats: "greenhouse" },
      };
    }
  }

  // Lever
  if (url.includes("jobs.lever.co") || doc.querySelector(".posting-headline")) {
    const titleEl = doc.querySelector(".posting-headline h2");
    const locEl = doc.querySelector(".posting-categories .location");
    const typeEl = doc.querySelector(".posting-categories .workplace-type");
    const descEl =
      doc.querySelector('[data-qa="job-description"]') ||
      doc.querySelector(".section-wrapper");

    if (titleEl?.textContent?.trim()) {
      const locText = locEl?.textContent?.trim() || "";
      const workplace = typeEl?.textContent?.trim() || "";
      const descText = cleanHtmlText(descEl?.innerHTML || descEl?.textContent);
      return {
        found: true,
        sourceType: "ats",
        sourceLabel: "Lever ATS",
        title: titleEl.textContent.trim(),
        organization: null, // Genellikle Lever URL'inden veya title'dan çıkarılır
        location: locText || null,
        remote: detectRemote(`${workplace} ${locText} ${titleEl.textContent}`),
        compensation: detectSalaryFromText(descText),
        deadline_at: null,
        notes: descText || null,
        raw: { ats: "lever" },
      };
    }
  }

  // Ashby
  if (
    url.includes("ashbyhq.com") ||
    doc.querySelector('[data-test="job-location"]')
  ) {
    const titleEl = doc.querySelector("h1");
    const locEl = doc.querySelector('[data-test="job-location"]');
    const descEl = doc.querySelector('[data-test="job-description"]');

    if (titleEl?.textContent?.trim()) {
      const locText = locEl?.textContent?.trim() || "";
      const descText = cleanHtmlText(descEl?.innerHTML || descEl?.textContent);
      return {
        found: true,
        sourceType: "ats",
        sourceLabel: "Ashby ATS",
        title: titleEl.textContent.trim(),
        organization: null,
        location: locText || null,
        remote: detectRemote(`${titleEl.textContent} ${locText}`),
        compensation: detectSalaryFromText(descText),
        deadline_at: null,
        notes: descText || null,
        raw: { ats: "ashby" },
      };
    }
  }

  // Workable
  if (
    url.includes("workable.com") ||
    doc.querySelector('[data-ui="job-title"]')
  ) {
    const titleEl = doc.querySelector('[data-ui="job-title"]');
    const orgEl = doc.querySelector('[data-ui="company-name"]');
    const locEl = doc.querySelector('[data-ui="job-location"]');
    const descEl = doc.querySelector('[data-ui="job-description"]');

    if (titleEl?.textContent?.trim()) {
      const locText = locEl?.textContent?.trim() || "";
      const descText = cleanHtmlText(descEl?.innerHTML || descEl?.textContent);
      return {
        found: true,
        sourceType: "ats",
        sourceLabel: "Workable",
        title: titleEl.textContent.trim(),
        organization: orgEl?.textContent?.trim() || null,
        location: locText || null,
        remote: detectRemote(`${titleEl.textContent} ${locText}`),
        compensation: detectSalaryFromText(descText),
        deadline_at: null,
        notes: descText || null,
        raw: { ats: "workable" },
      };
    }
  }

  // LinkedIn
  if (
    url.includes("linkedin.com") ||
    doc.querySelector(".job-details-jobs-unified-top-card__job-title")
  ) {
    const titleEl =
      doc.querySelector(".job-details-jobs-unified-top-card__job-title") ||
      doc.querySelector(".top-card-layout__title");
    const orgEl =
      doc.querySelector(".job-details-jobs-unified-top-card__company-name") ||
      doc.querySelector(".topcard__org-name-link");
    const locEl =
      doc.querySelector(".job-details-jobs-unified-top-card__bullet") ||
      doc.querySelector(".topcard__flavor--bullet");
    const descEl =
      doc.querySelector("#job-details") ||
      doc.querySelector(".show-more-less-html__markup");

    if (titleEl?.textContent?.trim()) {
      const locText = locEl?.textContent?.trim() || "";
      const descText = cleanHtmlText(descEl?.innerHTML || descEl?.textContent);
      return {
        found: true,
        sourceType: "ats",
        sourceLabel: "LinkedIn Jobs",
        title: titleEl.textContent.trim(),
        organization: orgEl?.textContent?.trim() || null,
        location: locText || null,
        remote: detectRemote(`${titleEl.textContent} ${locText}`),
        compensation: detectSalaryFromText(descText),
        deadline_at: null,
        notes: descText || null,
        raw: { ats: "linkedin" },
      };
    }
  }

  // Indeed
  if (
    url.includes("indeed.com") ||
    doc.querySelector("h1.jobsearch-JobInfoHeader-title")
  ) {
    const titleEl = doc.querySelector("h1.jobsearch-JobInfoHeader-title");
    const orgEl =
      doc.querySelector('[data-company-name="true"]') ||
      doc.querySelector(".jobsearch-CompanyInfoContainer");
    const locEl = doc.querySelector(
      '[data-testid="inlineHeader-companyLocation"]',
    );
    const descEl = doc.querySelector("#jobDescriptionText");

    if (titleEl?.textContent?.trim()) {
      const locText = locEl?.textContent?.trim() || "";
      const descText = cleanHtmlText(descEl?.innerHTML || descEl?.textContent);
      return {
        found: true,
        sourceType: "ats",
        sourceLabel: "Indeed",
        title: titleEl.textContent.trim(),
        organization: orgEl?.textContent?.trim() || null,
        location: locText || null,
        remote: detectRemote(`${titleEl.textContent} ${locText}`),
        compensation: detectSalaryFromText(descText),
        deadline_at: null,
        notes: descText || null,
        raw: { ats: "indeed" },
      };
    }
  }

  return null;
}

// 3. KATMAN: OpenGraph, Meta Etiketleri ve Sayfa İçi Sezgisel Analiz
function extractFromMeta(doc, pageUrl) {
  const getMeta = (selector) =>
    doc.querySelector(selector)?.getAttribute("content")?.trim() || null;

  const ogTitle =
    getMeta('meta[property="og:title"]') ||
    getMeta('meta[name="twitter:title"]');
  const siteName = getMeta('meta[property="og:site_name"]');
  const description =
    getMeta('meta[name="description"]') ||
    getMeta('meta[property="og:description"]');

  const rawTitle = ogTitle || doc.title || "";
  const parsed = parseTitleAndOrg(rawTitle);

  const fullText = `${rawTitle} ${description || ""}`;
  const remote = detectRemote(fullText);
  const compensation = detectSalaryFromText(fullText);

  return {
    found: Boolean(parsed.title),
    sourceType: "meta",
    sourceLabel: "Sayfa Meta Verileri",
    title: parsed.title,
    organization: siteName || parsed.org || null,
    location: null,
    remote: remote || null,
    compensation: compensation || null,
    deadline_at: null,
    notes: description || null,
    raw: { metaTitle: ogTitle, siteName, description },
  };
}

// DOM veya Snapshot sarmalayıcı (Tarayıcı DOM ve Node/snapshot testlerini birleştirir)
function wrapDoc(docOrSnapshot) {
  if (!docOrSnapshot) return null;
  if (typeof docOrSnapshot.querySelectorAll === "function") {
    return docOrSnapshot;
  }
  const {
    scripts = [],
    metas = {},
    elements = {},
    title = "",
    url = "",
    selectedText = "",
    favicon = "",
    readingTimeMinutes = 1,
  } = docOrSnapshot;
  return {
    title,
    url,
    selectedText,
    favicon,
    readingTimeMinutes,
    querySelectorAll(selector) {
      if (selector === 'script[type="application/ld+json"]') {
        return scripts.map((s) => ({
          textContent: typeof s === "string" ? s : JSON.stringify(s),
        }));
      }
      return [];
    },
    querySelector(selector) {
      if (selector.startsWith("meta[")) {
        const propMatch = selector.match(/property="([^"]+)"/);
        const nameMatch = selector.match(/name="([^"]+)"/);
        const key = propMatch?.[1] || nameMatch?.[1];
        if (key && metas[key]) {
          return {
            getAttribute: (attr) => (attr === "content" ? metas[key] : null),
          };
        }
      }
      if (elements[selector]) {
        const item = elements[selector];
        return {
          textContent: typeof item === "string" ? item : item.text,
          innerHTML: typeof item === "object" ? item.html : item,
          getAttribute: (attr) => (item.attrs ? item.attrs[attr] : null),
        };
      }
      return null;
    },
  };
}

// Aktif sekmede executeScript ile koşturulabilen DOM toplayıcı
export function collectPageDom() {
  const scripts = Array.from(
    document.querySelectorAll('script[type="application/ld+json"]'),
  )
    .slice(0, 8)
    .map((s) => s.textContent.slice(0, 4000));
  const metas = {};
  for (const el of Array.from(
    document.querySelectorAll("meta[property], meta[name]"),
  ).slice(0, 80)) {
    const key = el.getAttribute("property") || el.getAttribute("name");
    if (key)
      metas[key.slice(0, 120)] = (el.getAttribute("content") || "").slice(
        0,
        500,
      );
  }

  const selectedText = window.getSelection
    ? window.getSelection().toString().trim().slice(0, 6000)
    : "";
  const faviconEl = document.querySelector('link[rel~="icon"]');
  const favicon = faviconEl
    ? faviconEl.href
    : `${window.location.origin}/favicon.ico`;
  const readingTimeMinutes = null; // Full-page text is intentionally not collected.

  const selectors = [
    ".app-title",
    "h1.app-title",
    ".company-name",
    ".location",
    "#content",
    ".posting-headline h2",
    ".posting-categories .location",
    ".posting-categories .workplace-type",
    '[data-qa="job-description"]',
    ".section-wrapper",
    "h1",
    '[data-test="job-location"]',
    '[data-test="job-description"]',
    '[data-ui="job-title"]',
    '[data-ui="company-name"]',
    '[data-ui="job-location"]',
    '[data-ui="job-description"]',
    ".job-details-jobs-unified-top-card__job-title",
    ".top-card-layout__title",
    ".job-details-jobs-unified-top-card__company-name",
    ".topcard__org-name-link",
    ".job-details-jobs-unified-top-card__bullet",
    ".topcard__flavor--bullet",
    "#job-details",
    ".show-more-less-html__markup",
    "h1.jobsearch-JobInfoHeader-title",
    '[data-company-name="true"]',
    ".jobsearch-CompanyInfoContainer",
    '[data-testid="inlineHeader-companyLocation"]',
    "#jobDescriptionText",
  ];

  const elements = {};
  for (const sel of selectors) {
    try {
      const el = document.querySelector(sel);
      if (el) {
        elements[sel] = {
          text: (el.textContent?.trim() || "").slice(0, 1200),
          html: "", // text-only bounded snapshot; never transmit page HTML.
        };
      }
    } catch {}
  }

  return {
    url: window.location.href,
    title: document.title.slice(0, 300),
    scripts,
    officialDocuments: Array.from(document.querySelectorAll('a[href$=".pdf"]'))
      .slice(0, 3)
      .map((a) => a.href.slice(0, 4000)),
    metas,
    elements,
    selectedText,
    favicon,
    readingTimeMinutes,
  };
}

// Sayfa Meta Verileri ve Okuma Süresi Çıkarıcı
export function extractPageMetadata(docOrSnapshot, pageUrl) {
  const doc = wrapDoc(docOrSnapshot);
  if (!doc) {
    return {
      title: "",
      url: pageUrl || "",
      description: "",
      image: "",
      favicon: "",
      selectedText: "",
      readingTimeMinutes: 1,
    };
  }

  const effectiveUrl = pageUrl || doc.url || "";
  const title = doc.title || "";

  const getMeta = (names) => {
    for (const name of names) {
      const el =
        doc.querySelector(`meta[property="${name}"]`) ||
        doc.querySelector(`meta[name="${name}"]`);
      const content = el?.getAttribute?.("content");
      if (content && content.trim()) return content.trim();
    }
    return "";
  };

  const description = getMeta([
    "og:description",
    "description",
    "twitter:description",
  ]);
  const image = getMeta(["og:image", "og:image:secure_url", "twitter:image"]);
  const author = getMeta([
    "author",
    "article:author",
    "twitter:creator",
    "byl",
  ]);

  return {
    title,
    url: effectiveUrl,
    description,
    image,
    author: author || null,
    favicon: doc.favicon || "",
    selectedText: doc.selectedText || "",
    readingTimeMinutes: doc.readingTimeMinutes || 1,
  };
}

// ANA GİRİŞ NOKTASI: Deterministik İş İlanı Çıkarıcı
export function extractJobDetails(docOrSnapshot, pageUrl) {
  const doc = wrapDoc(docOrSnapshot);
  if (!doc) {
    return {
      found: false,
      sourceType: "none",
      sourceLabel: "Belge bulunamadı",
      title: "",
      organization: null,
      location: null,
      remote: null,
      compensation: null,
      deadline_at: null,
      notes: null,
      url: pageUrl || "",
      raw: {},
    };
  }

  const effectiveUrl = pageUrl || doc.url || "";

  // 1. Adım: Schema.org JSON-LD
  const jsonLd = extractFromJsonLd(doc);
  if (jsonLd && jsonLd.title) {
    // Sayfa başlığından veya meta'dan eksik şirket adını tamamla
    if (!jsonLd.organization) {
      const parsed = parseTitleAndOrg(doc.title);
      jsonLd.organization = parsed.org || null;
    }
    return { ...jsonLd, url: effectiveUrl };
  }

  // 2. Adım: Popüler ATS Seçicileri
  const ats = extractFromAts(doc, effectiveUrl);
  if (ats && ats.title) {
    if (!ats.organization) {
      const parsed = parseTitleAndOrg(doc.title);
      ats.organization = parsed.org || null;
    }
    return { ...ats, url: effectiveUrl };
  }

  // 3. Adım: Meta Veriler & Heuristics
  const meta = extractFromMeta(doc, effectiveUrl);
  return { ...meta, url: effectiveUrl };
}

/** Academic capture is explicitly selected; ATS heuristics do not determine its type. */
export function extractAnnouncement(snapshot, pageUrl) {
  const metas = snapshot?.metas ?? {};
  let article = {};
  for (const script of snapshot?.scripts ?? []) {
    try {
      const data = JSON.parse(script);
      const entries = Array.isArray(data) ? data : (data["@graph"] ?? [data]);
      const match = entries.find((x) =>
        ["Article", "NewsArticle", "ScholarlyArticle"].includes(x["@type"]),
      );
      if (match) {
        article = match;
        break;
      }
    } catch {}
  }
  const date = article.datePublished ?? metas["article:published_time"];
  const validDate =
    typeof date === "string" &&
    /T.*(Z|[+-]\d\d:\d\d)$/.test(date) &&
    Number.isFinite(Date.parse(date))
      ? date
      : null;
  const publisher = article.publisher?.name;
  const documentUrl =
    snapshot?.officialDocuments?.find((url) => {
      try {
        return ["http:", "https:"].includes(new URL(url).protocol);
      } catch {
        return false;
      }
    }) ?? null;
  return {
    title: String(
      article.headline ?? metas["og:title"] ?? snapshot?.title ?? "",
    ).slice(0, 300),
    organization:
      typeof publisher === "string" ? publisher.slice(0, 300) : null,
    url: pageUrl,
    published_at: validDate,
    deadline_at: null,
    official_document_url: documentUrl,
    sourceLabel:
      "Sayfa yayın metaverisi · resmîlik kullanıcı doğrulaması gerektirir",
  };
}
