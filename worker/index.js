// eprkit.com Worker: serves the static site from ./site and handles /api/intake.
// Static files are served without running this code (assets.run_worker_first is only "/api/*").
import { onRequestGet, onRequestPost, onRequest } from "./intake.js";

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === "/api/intake") {
      const context = { request, env, waitUntil: (p) => ctx.waitUntil(p) };
      if (request.method === "GET") return onRequestGet(context);
      if (request.method === "POST") return onRequestPost(context);
      return onRequest(context);
    }
    if (url.pathname.startsWith("/api/")) {
      return new Response(JSON.stringify({ ok: false, error: "Not found" }), { status: 404, headers: { "content-type": "application/json" } });
    }
    return env.ASSETS.fetch(request);
  },
};
