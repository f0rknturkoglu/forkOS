// Offline PDF rendering through the pinned upstream engine. No tracker ownership.
import { readFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

const [htmlPath, pdfPath] = process.argv.slice(2);
const root = process.env.CAREER_OPS_CHECKOUT;
if (!root || !htmlPath || !pdfPath) throw new Error('Missing bounded render input');
const { renderHtmlToPdf } = await import(pathToFileURL(resolve(root, 'generate-pdf.mjs')));
const result = await renderHtmlToPdf(await readFile(htmlPath, 'utf8'), pdfPath, {
  workspaceRoot: process.env.CAREER_OPS_ROOT,
  baseDir: process.env.CAREER_OPS_ROOT,
  maxPages: 3,
  strictPages: true,
  format: 'a4',
});
process.stdout.write(JSON.stringify({ page_count: result.pageCount, size: result.size }));
