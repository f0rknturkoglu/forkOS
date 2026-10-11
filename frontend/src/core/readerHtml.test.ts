// @vitest-environment jsdom
import { expect, it } from "vitest";
import { sanitizeReaderHtml } from "./readerHtml";
it("untrusted markup cannot execute, navigate with scripts, style or download remote assets", () => {
  const html = sanitizeReaderHtml(
    '<p onclick="evil()">Keep <b>text</b></p><svg><a href="javascript:evil()">Bad</a></svg><img src="https://tracker.example/pixel"><iframe srcdoc="<script>evil()</script>"></iframe><a href="jav&#x61;script:evil()">click</a><a href="https://example.com" style="background:url(https://tracker.example)">Safe</a><object data="x"></object>',
  );
  expect(html).toContain("<p>Keep <b>text</b></p>");
  expect(html).toContain('href="https://example.com/"');
  for (const bad of ["onclick", "javascript:", "src=", "srcdoc", "<img", "<svg", "<iframe", "style=", "<object"])
    expect(html).not.toContain(bad);
});
