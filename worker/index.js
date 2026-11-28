// eprkit.com Worker: serves the static site from ./site, handles /api/intake and /api/shopify/*, and runs
// the cron that saves finished Shopify exports.
// Static files are served without running this code (assets.run_worker_first is only "/api/*").
import { onRequestGet, onRequestPost, onRequest } from "./intake.js";
import { shopifyInstall, shopifyCallback, shopifyWebhook, shopifyCron } from "./shopify.js";
import { appPage, appStatus, appBook } from "./app.js";

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(shopifyCron(env));
  },
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === "/api/intake") {
      const context = { request, env, waitUntil: (p) => ctx.waitUntil(p) };
      if (request.method === "GET") return onRequestGet(context);
      if (request.method === "POST") return onRequestPost(context);
      return onRequest(context);
    }
    if (url.pathname === "/app" || url.pathname === "/app/") return appPage(env);
    if (url.pathname === "/api/app/status" && request.method === "GET") return appStatus(request, env, (p) => ctx.waitUntil(p));
    if (url.pathname === "/api/app/book" && request.method === "POST") return appBook(request, env, (p) => ctx.waitUntil(p));
    if (url.pathname === "/api/shopify/install" && request.method === "GET") return shopifyInstall(request, env);
    if (url.pathname === "/api/shopify/callback" && request.method === "GET") return shopifyCallback(request, env, (p) => ctx.waitUntil(p));
    if (url.pathname === "/api/shopify/webhooks" && request.method === "POST") return shopifyWebhook(request, env);
    if (url.pathname.startsWith("/api/")) {
      return new Response(JSON.stringify({ ok: false, error: "Not found" }), { status: 404, headers: { "content-type": "application/json" } });
    }
    return env.ASSETS.fetch(request);
  },
};
