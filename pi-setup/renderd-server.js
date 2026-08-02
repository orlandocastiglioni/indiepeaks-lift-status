#!/usr/bin/env node
/**
 * renderd - minimal headless-chromium render service for liftie.
 *
 * GET /render?url=<page>&wait=<css selector>&timeout=<ms>
 *   loads the page in system chromium, waits for network idle plus the
 *   optional selector, and returns the rendered HTML. Made for ski-resort
 *   pages that populate lift/trail rows from post-load XHR calls.
 * GET /healthz
 *
 * Listens on 127.0.0.1 only. One page at a time - this is a Raspberry Pi.
 */

import { createServer } from 'node:http';
import puppeteer from 'puppeteer-core';

const PORT = Number(process.env.RENDERD_PORT ?? 3002);
const CHROMIUM = process.env.RENDERD_CHROMIUM ?? '/usr/bin/chromium';
const USER_AGENT =
  process.env.RENDERD_USER_AGENT ??
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36';
const DEFAULT_TIMEOUT = 45_000;
const MAX_TIMEOUT = 90_000;
const BLOCKED_RESOURCES = new Set(['image', 'media', 'font']);

let browser = null;
let queue = Promise.resolve();

async function getBrowser() {
  if (browser?.connected) {
    return browser;
  }
  browser = await puppeteer.launch({
    executablePath: CHROMIUM,
    headless: true,
    args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage', '--disable-extensions', '--mute-audio']
  });
  browser.on('disconnected', () => {
    browser = null;
  });
  return browser;
}

async function render(url, wait, timeout) {
  const b = await getBrowser();
  const page = await b.newPage();
  try {
    await page.setUserAgent(USER_AGENT);
    await page.setViewport({ width: 1366, height: 900 });
    await page.setRequestInterception(true);
    page.on('request', req => {
      if (BLOCKED_RESOURCES.has(req.resourceType())) {
        req.abort().catch(() => {});
      } else {
        req.continue().catch(() => {});
      }
    });
    await page.goto(url, { waitUntil: 'networkidle2', timeout });
    if (wait) {
      await page.waitForSelector(wait, { timeout: Math.min(timeout, 30_000) });
    }
    return await page.content();
  } finally {
    await page.close().catch(() => {});
  }
}

function enqueue(job) {
  const run = queue.then(job, job);
  queue = run.catch(() => {});
  return run;
}

const server = createServer(async (req, res) => {
  const { pathname, searchParams } = new URL(req.url, `http://127.0.0.1:${PORT}`);

  if (pathname === '/healthz') {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    return res.end('ok\n');
  }
  if (pathname !== '/render') {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    return res.end('not found\n');
  }

  const url = searchParams.get('url');
  let target;
  try {
    target = new URL(url);
    if (!/^https?:$/.test(target.protocol)) {
      throw new Error('bad protocol');
    }
  } catch {
    res.writeHead(400, { 'Content-Type': 'text/plain' });
    return res.end('invalid url\n');
  }

  const wait = searchParams.get('wait') || undefined;
  const timeout = Math.min(Number(searchParams.get('timeout')) || DEFAULT_TIMEOUT, MAX_TIMEOUT);

  try {
    const html = await enqueue(() => render(target.toString(), wait, timeout));
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(html);
  } catch (err) {
    console.error(`render failed for ${target}: ${err.message}`);
    res.writeHead(502, { 'Content-Type': 'text/plain' });
    res.end(`render failed: ${err.message}\n`);
  }
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`renderd listening on 127.0.0.1:${PORT}, chromium: ${CHROMIUM}`);
});

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, async () => {
    server.close();
    if (browser) {
      await browser.close().catch(() => {});
    }
    process.exit(0);
  });
}
