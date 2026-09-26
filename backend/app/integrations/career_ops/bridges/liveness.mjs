#!/usr/bin/env node
/**
 * bridges/liveness.mjs — Static typed JSON bridge for career-ops liveness verification.
 *
 * Imports upstream ES modules (liveness-api.mjs, liveness-browser.mjs) and returns
 * a single structured JSON document on stdout. Never prints prose or emojis.
 *
 * Usage:
 *   node bridges/liveness.mjs <url> [--timeout <ms>] [--no-fallback]
 */

import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

const checkoutDir = process.env.CAREER_OPS_CHECKOUT || process.cwd();

async function loadUpstreamModules() {
  const apiPath = resolve(checkoutDir, 'liveness-api.mjs');
  const browserPath = resolve(checkoutDir, 'liveness-browser.mjs');

  const { checkLivenessViaApi } = await import(pathToFileURL(apiPath).href);
  const {
    checkUrlLivenessWithFallback,
    newLivenessPage,
    rejectPrivateOrInvalid,
  } = await import(pathToFileURL(browserPath).href);

  return {
    checkLivenessViaApi,
    checkUrlLivenessWithFallback,
    newLivenessPage,
    rejectPrivateOrInvalid,
  };
}

function parseArgs(args) {
  let url = null;
  let timeoutMs = 15000;
  let noFallback = false;

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === '--no-fallback') {
      noFallback = true;
    } else if (arg === '--timeout' && i + 1 < args.length) {
      const parsed = parseInt(args[++i], 10);
      if (!isNaN(parsed) && parsed > 0) timeoutMs = parsed;
    } else if (arg.startsWith('--timeout=')) {
      const parsed = parseInt(arg.split('=')[1], 10);
      if (!isNaN(parsed) && parsed > 0) timeoutMs = parsed;
    } else if (!arg.startsWith('-') && !url) {
      url = arg;
    }
  }

  return { url, timeoutMs, noFallback };
}

async function main() {
  const args = process.argv.slice(2);
  const { url, timeoutMs, noFallback } = parseArgs(args);

  if (!url) {
    const out = {
      url: '',
      status: 'uncertain',
      code: 'no_url',
      reason: 'No URL provided to liveness bridge',
      method: 'bridge',
      checked_at: new Date().toISOString(),
    };
    process.stdout.write(JSON.stringify(out));
    process.exit(1);
  }

  let modules;
  try {
    modules = await loadUpstreamModules();
  } catch (err) {
    const out = {
      url,
      status: 'uncertain',
      code: 'module_load_failure',
      reason: `Failed to load upstream modules: ${err.message}`,
      method: 'bridge',
      checked_at: new Date().toISOString(),
    };
    process.stdout.write(JSON.stringify(out));
    process.exit(1);
  }

  const {
    checkLivenessViaApi,
    checkUrlLivenessWithFallback,
    newLivenessPage,
    rejectPrivateOrInvalid,
  } = modules;

  // SSRF guard
  const guard = rejectPrivateOrInvalid(url);
  if (guard) {
    const out = {
      url,
      status: 'uncertain',
      code: guard.code || 'blocked_host',
      reason: guard.reason || 'Private or invalid host rejected',
      method: 'bridge',
      checked_at: new Date().toISOString(),
    };
    process.stdout.write(JSON.stringify(out));
    process.exit(0);
  }

  // Rung 1: ATS API check (zero-token, fast)
  try {
    const apiResult = await checkLivenessViaApi(url);
    if (apiResult) {
      const out = {
        url,
        status: apiResult.result,
        code: apiResult.code,
        reason: apiResult.reason,
        method: 'api',
        checked_at: new Date().toISOString(),
      };
      process.stdout.write(JSON.stringify(out));
      process.exit(0);
    }
  } catch (err) {
    // Inconclusive, proceed to browser fallback unless --no-fallback
  }

  if (noFallback) {
    const out = {
      url,
      status: 'uncertain',
      code: 'api_inconclusive',
      reason: 'ATS API inconclusive and browser fallback disabled',
      method: 'api',
      checked_at: new Date().toISOString(),
    };
    process.stdout.write(JSON.stringify(out));
    process.exit(0);
  }

  // Rung 2: Playwright Chromium browser check
  let chromiumModule;
  try {
    chromiumModule = await import('playwright');
  } catch {
    const out = {
      url,
      status: 'uncertain',
      code: 'no_playwright',
      reason: 'Playwright not installed for browser fallback',
      method: 'bridge',
      checked_at: new Date().toISOString(),
    };
    process.stdout.write(JSON.stringify(out));
    process.exit(0);
  }

  const { chromium } = chromiumModule;
  let browser = null;
  try {
    browser = await chromium.launch({ headless: true });
    const page = await newLivenessPage(browser);
    const browserResult = await checkUrlLivenessWithFallback(page, url);

    const out = {
      url,
      status: browserResult.result,
      code: browserResult.code || 'browser_verdict',
      reason: browserResult.reason || '',
      method: 'browser',
      checked_at: new Date().toISOString(),
    };
    process.stdout.write(JSON.stringify(out));
    process.exit(0);
  } catch (err) {
    const out = {
      url,
      status: 'uncertain',
      code: 'browser_error',
      reason: `Browser liveness check error: ${err.message}`,
      method: 'browser',
      checked_at: new Date().toISOString(),
    };
    process.stdout.write(JSON.stringify(out));
    process.exit(0);
  } finally {
    if (browser) {
      await browser.close().catch(() => {});
    }
  }
}

main().catch((err) => {
  const out = {
    url: '',
    status: 'uncertain',
    code: 'fatal_error',
    reason: err.message,
    method: 'bridge',
    checked_at: new Date().toISOString(),
  };
  process.stdout.write(JSON.stringify(out));
  process.exit(1);
});
