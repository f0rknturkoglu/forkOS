import test from "node:test";
import assert from "node:assert/strict";
import { extractJobDetails, cleanHtmlText } from "../extractor.js";

// Minimal DOM mock helper for Node tests
function createMockDoc({ scripts = [], elements = {}, meta = {}, title = "", bodyText = "" }) {
  return {
    title,
    querySelectorAll(selector) {
      if (selector === 'script[type="application/ld+json"]') {
        return scripts.map((s) => ({ textContent: typeof s === "string" ? s : JSON.stringify(s) }));
      }
      return [];
    },
    querySelector(selector) {
      if (meta[selector]) {
        return { getAttribute: (attr) => (attr === "content" ? meta[selector] : null) };
      }
      if (elements[selector]) {
        const val = elements[selector];
        return {
          textContent: typeof val === "string" ? val : val.text,
          innerHTML: typeof val === "object" ? val.html : val,
          getAttribute: (attr) => (val.attrs ? val.attrs[attr] : null),
        };
      }
      return null;
    },
    body: {
      innerText: bodyText,
      textContent: bodyText,
    },
  };
}

test("extracts JobPosting directly from JSON-LD Schema.org", () => {
  const schema = {
    "@context": "https://schema.org",
    "@type": "JobPosting",
    "title": "Senior Distributed Systems Engineer",
    "description": "<p>We are looking for an <strong>expert</strong> backend engineer.</p><ul><li>Go</li><li>Rust</li></ul>",
    "hiringOrganization": {
      "@type": "Organization",
      "name": "Acme Cloud Corp",
    },
    "jobLocationType": "TELECOMMUTE",
    "applicantLocationRequirements": {
      "@type": "Country",
      "name": "Worldwide",
    },
    "jobLocation": {
      "@type": "Place",
      "address": {
        "addressLocality": "Berlin",
        "addressCountry": "Germany",
      },
    },
    "baseSalary": {
      "@type": "MonetaryAmount",
      "currency": "EUR",
      "value": {
        "@type": "QuantitativeValue",
        "minValue": 90000,
        "maxValue": 120000,
        "unitText": "YEAR",
      },
    },
    "validThrough": "2026-12-31T23:59:59Z",
  };

  const doc = createMockDoc({
    scripts: [schema],
    title: "Careers - Acme Cloud Corp",
  });

  const result = extractJobDetails(doc, "https://acme.example/jobs/123");

  assert.equal(result.found, true);
  assert.equal(result.sourceType, "schema_org");
  assert.equal(result.title, "Senior Distributed Systems Engineer");
  assert.equal(result.organization, "Acme Cloud Corp");
  assert.equal(result.remote, "remote");
  assert.match(result.location, /Berlin/);
  assert.match(result.compensation, /90000/);
  assert.match(result.compensation, /120000/);
  assert.match(result.notes, /expert backend engineer/);
  assert.equal(result.deadline_at, "2026-12-31T23:59:59Z");
});

test("extracts JobPosting from nested @graph in JSON-LD", () => {
  const schemaWithGraph = {
    "@context": "https://schema.org",
    "@graph": [
      { "@type": "WebSite", "name": "Tech Corp" },
      {
        "@type": "JobPosting",
        "title": "Founding AI Engineer",
        "hiringOrganization": { "name": "NeuroTech AI" },
        "jobLocation": "San Francisco, CA",
        "description": "Build next-gen agentic workflows",
      },
    ],
  };

  const doc = createMockDoc({ scripts: [schemaWithGraph] });
  const result = extractJobDetails(doc, "https://neuro.example/jobs/ai");

  assert.equal(result.found, true);
  assert.equal(result.sourceType, "schema_org");
  assert.equal(result.title, "Founding AI Engineer");
  assert.equal(result.organization, "NeuroTech AI");
  assert.equal(result.location, "San Francisco, CA");
  assert.match(result.notes, /next-gen agentic workflows/);
});

test("extracts fields from Greenhouse ATS selectors when no JSON-LD", () => {
  const doc = createMockDoc({
    elements: {
      ".app-title": "Staff Infrastructure Engineer",
      ".company-name": "Stripe",
      ".location": "Remote - US / Europe",
      "#content": { html: "<p>Work on global financial infrastructure.</p>" },
    },
    title: "Staff Infrastructure Engineer at Stripe",
  });

  const result = extractJobDetails(doc, "https://boards.greenhouse.io/stripe/jobs/456");

  assert.equal(result.found, true);
  assert.equal(result.sourceType, "ats");
  assert.match(result.sourceLabel, /Greenhouse/i);
  assert.equal(result.title, "Staff Infrastructure Engineer");
  assert.equal(result.organization, "Stripe");
  assert.equal(result.remote, "remote");
  assert.match(result.location, /Remote/);
  assert.match(result.notes, /global financial infrastructure/);
});

test("extracts fields from Lever ATS selectors", () => {
  const doc = createMockDoc({
    elements: {
      ".posting-headline h2": "Product Operations Lead",
      ".posting-categories .location": "Amsterdam, Netherlands",
      ".posting-categories .workplace-type": "Hybrid",
      "[data-qa=\"job-description\"]": "Leading cross-functional product operations teams.",
    },
    title: "Product Operations Lead - Miro - Lever",
  });

  const result = extractJobDetails(doc, "https://jobs.lever.co/miro/789");

  assert.equal(result.found, true);
  assert.equal(result.sourceType, "ats");
  assert.match(result.sourceLabel, /Lever/i);
  assert.equal(result.title, "Product Operations Lead");
  assert.equal(result.remote, "hybrid");
  assert.match(result.location, /Amsterdam/);
});

test("falls back to OpenGraph and meta tags with regex heuristics", () => {
  const doc = createMockDoc({
    meta: {
      'meta[property="og:title"]': "Senior Frontend Engineer (Remote) - Linear",
      'meta[property="og:site_name"]': "Linear",
      'meta[name="description"]': "Join Linear to build high-performance project management tools. Compensation: $150k - $190k.",
    },
    title: "Senior Frontend Engineer (Remote) - Linear",
  });

  const result = extractJobDetails(doc, "https://linear.app/careers/senior-frontend");

  assert.equal(result.found, true);
  assert.match(result.title, /Senior Frontend Engineer/);
  assert.equal(result.organization, "Linear");
  assert.equal(result.remote, "remote");
  assert.match(result.compensation, /150k/);
  assert.match(result.notes, /high-performance project management/);
});

test("cleanHtmlText strips tags, decodes common entities, and collapses spaces", () => {
  const raw = "<p>Hello &amp; welcome to <strong>forkOS</strong>!<br/>Line 2&nbsp;&nbsp;extra</p>";
  const cleaned = cleanHtmlText(raw);
  assert.equal(cleaned, "Hello & welcome to forkOS!\nLine 2 extra");
});

test("extractJobDetails supports snapshot objects returned by collectPageDom", () => {
  const snapshot = {
    url: "https://jobs.ashbyhq.com/superagent/123",
    title: "Lead Agentic Engineer - Superagent",
    scripts: [
      JSON.stringify({
        "@type": "JobPosting",
        "title": "Lead Agentic Engineer",
        "hiringOrganization": { "name": "Superagent AI" },
        "jobLocationType": "TELECOMMUTE",
        "baseSalary": "$180,000 - $220,000",
        "description": "Build autonomous multi-agent swarms.",
      }),
    ],
    metas: {
      "og:title": "Lead Agentic Engineer - Superagent",
    },
    elements: {},
  };

  const result = extractJobDetails(snapshot);
  assert.equal(result.found, true);
  assert.equal(result.sourceType, "schema_org");
  assert.equal(result.title, "Lead Agentic Engineer");
  assert.equal(result.organization, "Superagent AI");
  assert.equal(result.remote, "remote");
  assert.match(result.compensation, /180,000/);
  assert.match(result.notes, /autonomous multi-agent/);
});

