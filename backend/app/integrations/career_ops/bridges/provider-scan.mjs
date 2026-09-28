// forkOS-owned, read-only bridge to the pinned career-ops provider registry.
// Input is a JSON-formatted portals.yml projection (JSON is valid YAML).
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const checkout = process.env.CAREER_OPS_CHECKOUT;
if (!checkout) throw new Error('CAREER_OPS_CHECKOUT is required');
const providersDir = path.join(checkout, 'providers');
const { loadProviders, resolveProvider } = await import(pathToFileURL(path.join(providersDir, '_registry.mjs')).href);
const { makeHttpCtx } = await import(pathToFileURL(path.join(providersDir, '_http.mjs')).href);
const files = readdirSync(providersDir).filter((name) => name.endsWith('.mjs') && !name.startsWith('_'));
const providers = await loadProviders(providersDir);

if (process.argv[2] === 'inventory') {
  const pluginDir = path.join(checkout, 'plugins');
  const plugins = existsSync(pluginDir) ? readdirSync(pluginDir).flatMap((name) => {
    const manifestPath = path.join(pluginDir, name, 'manifest.json');
    if (!existsSync(manifestPath)) return [];
    try {
      const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
      if (manifest.id !== name || !Array.isArray(manifest.requiredEnv)) return [];
      return [{ id: name, required_env: manifest.requiredEnv, hooks: manifest.hooks || [], status: 'unconfigured' }];
    } catch {
      return [];
    }
  }) : [];
  const result = {
    version: 'forkos.careerops.providers@1',
    files: files.length,
    providers: [...providers.values()].map((provider) => ({
      id: provider.id,
      detect_capable: typeof provider.detect === 'function',
      // The upstream contract does not expose reliable auth/browser/category
      // metadata. Unknown must remain unknown, never an invented green state.
      provider_type: 'unknown',
      requires_auth: null,
      browser_required: null,
      globally_enumerable: null,
    })),
    plugins,
  };
  process.stdout.write(`${JSON.stringify(result)}\n`);
} else if (process.argv[2] === 'scan') {
  const portalsPath = process.argv[3];
  if (!portalsPath || !path.resolve(portalsPath).startsWith(path.resolve(process.env.CAREER_OPS_ROOT) + path.sep)) {
    throw new Error('Projection must be inside isolated runtime directory');
  }
  const config = JSON.parse(readFileSync(portalsPath, 'utf8'));
  const targets = [...(config.tracked_companies || []).map((target) => ({ ...target, kind: 'company' })),
    ...(config.job_boards || []).map((target) => ({ ...target, kind: 'board' }))];
  if (targets.length > 100) throw new Error('Too many provider targets');
  const offers = [];
  const errors = [];
  const targetResults = [];
  let partial = false;
  const sinceDays = Math.min(90, Math.max(1, Number(config.since_days) || 7));
  const sinceMs = Date.now() - sinceDays * 86400000;
  for (const target of targets) {
    const resolved = resolveProvider(target, providers);
    const provider = resolved?.provider;
    if (!provider || provider.id === 'local-parser') {
      const error = resolved?.error || 'No public provider matched';
      errors.push({ target: target.name, provider: target.provider || null, error });
      targetResults.push({ target: target.name, provider: target.provider || null, status: 'unconfigured', found: 0 });
      partial = true;
      continue;
    }
    let requests = 0;
    const maxPages = Math.min(12, Math.max(1, Number(target.max_pages) || 5));
    const ctx = {
      ...makeHttpCtx({ onRequest: () => { if (++requests > 40) throw new Error('Request budget exceeded'); } }),
      sinceMs,
      includeUndated: true,
      maxPages,
    };
    try {
      const jobs = await provider.fetch(target, ctx);
      if (!Array.isArray(jobs)) throw new Error('Provider returned a non-array result');
      const limit = Math.min(400, Math.max(1, Number(target.max_results) || 200));
      if (jobs.length >= limit) partial = true;
      let cappedGlobal = false;
      for (const job of jobs.slice(0, limit)) {
        if (!job || typeof job.title !== 'string' || typeof job.url !== 'string') continue;
        if (offers.length >= 5000) {
          partial = true;
          cappedGlobal = true;
          break;
        }
        offers.push({
          company: String(job.company || target.name || ''),
          title: job.title,
          url: job.url,
          location: typeof job.location === 'string' ? job.location : null,
          description: typeof job.description === 'string' ? job.description.slice(0, 1500) : null,
          salary: typeof job.salary === 'string' ? job.salary : null,
          posted_at: Number.isFinite(job.postedAt) ? new Date(job.postedAt).toISOString() : null,
          provider: provider.id,
          target: target.name,
          kind: target.kind,
        });
      }
      const capHit = jobs.length >= limit || cappedGlobal;
      targetResults.push({
        target: target.name, provider: provider.id, status: capHit ? 'partial' : 'ok',
        found: jobs.length, cap_hit: capHit, max_pages_requested: maxPages,
        requests_made: requests, result_limit: limit,
      });
    } catch (error) {
      const message = String(error?.message || error).slice(0, 300);
      errors.push({ target: target.name, provider: provider.id, error: message });
      targetResults.push({ target: target.name, provider: provider.id, status: 'error', found: 0,
        cap_hit: message === 'Request budget exceeded', max_pages_requested: maxPages,
        requests_made: requests, result_limit: Math.min(400, Math.max(1, Number(target.max_results) || 200)) });
      partial = true;
    }
  }
  process.stdout.write(`${JSON.stringify({
    version: 'forkos.careerops.scan@1',
    providers_loaded: providers.size,
    targets_scanned: targets.length,
    boards_scanned: targets.filter((target) => target.kind === 'board').length,
    companies_scanned: targets.filter((target) => target.kind === 'company').length,
    offers,
    errors,
    target_results: targetResults,
    partial,
  })}\n`);
} else {
  throw new Error('Expected inventory or scan');
}
