// Supabase Edge Function: tmdb-proxy
// Acts as a hardened, authenticated proxy between Cineforge clients and TMDb.
// Kept strictly read-only with parameter validation, whitelisted endpoints,
// and private TMDb credentials stored exclusively as Supabase cloud secrets.

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const TMDB_API_BASE = "https://api.themoviedb.org/3";
const ALLOWED_ORIGINS = new Set([
  "tauri://localhost",
  "https://tauri.localhost",
  "http://localhost:5173",
  "http://127.0.0.1:5173",
  "http://localhost:3000",
]);

// Whitelist of strictly permitted TMDb endpoints
const ALLOWED_PATH_PATTERNS = [
  /^\/search\/movie$/,
  /^\/search\/tv$/,
  /^\/discover\/movie$/,
  /^\/movie\/\d+$/,
];

function getCorsHeaders(origin: string | null): Record<string, string> {
  const allowedOrigin = origin && ALLOWED_ORIGINS.has(origin) ? origin : "tauri://localhost";
  return {
    "Access-Control-Allow-Origin": allowedOrigin,
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Authorization, Content-Type, Accept, X-Client-Info, apikey",
    "Access-Control-Max-Age": "86400",
  };
}

serve(async (req: Request) => {
  const origin = req.headers.get("Origin");
  const corsHeaders = getCorsHeaders(origin);

  // 1. Handle CORS preflight
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders });
  }

  // 2. Enforce GET only
  if (req.method !== "GET") {
    return new Response(
      JSON.stringify({ error: "Method not allowed. Only GET is supported." }),
      { status: 405, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }

  // 3. Verify Authentication: Require valid Bearer token or Supabase anon apikey
  const authHeader = req.headers.get("Authorization");
  const apiKeyHeader = req.headers.get("apikey");
  if (!authHeader && !apiKeyHeader) {
    return new Response(
      JSON.stringify({ error: "Unauthorized. Missing Authorization or apikey header." }),
      { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }

  // 4. Retrieve cloud secret
  const tmdbKey = Deno.env.get("TMDB_API_KEY");
  if (!tmdbKey) {
    return new Response(
      JSON.stringify({ error: "TMDb proxy is unconfigured on the server (missing TMDB_API_KEY secret)." }),
      { status: 503, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }

  try {
    const url = new URL(req.url);
    const targetPath = url.searchParams.get("endpoint") || url.pathname.replace(/^\/tmdb-proxy/, "");
    const normalizedPath = targetPath.startsWith("/") ? targetPath : `/${targetPath}`;

    // 5. Validate endpoint whitelist
    const isAllowed = ALLOWED_PATH_PATTERNS.some((pattern) => pattern.test(normalizedPath));
    if (!isAllowed) {
      return new Response(
        JSON.stringify({
          error: `Forbidden TMDb endpoint: '${normalizedPath}'. Allowed: /search/movie, /search/tv, /discover/movie, /movie/{id}`,
        }),
        { status: 403, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // 6. Validate and sanitize query parameters
    const upstreamParams = new URLSearchParams();

    // Query string length constraint
    const query = url.searchParams.get("query");
    if (query !== null) {
      if (query.trim().length === 0 || query.length > 100) {
        return new Response(
          JSON.stringify({ error: "Invalid 'query' parameter: length must be between 1 and 100 characters." }),
          { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }
      upstreamParams.set("query", query.trim());
    }

    // Page constraint (1..10)
    const page = url.searchParams.get("page");
    if (page !== null) {
      const pageNum = parseInt(page, 10);
      if (isNaN(pageNum) || pageNum < 1 || pageNum > 10) {
        return new Response(
          JSON.stringify({ error: "Invalid 'page' parameter: must be an integer between 1 and 10." }),
          { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }
      upstreamParams.set("page", pageNum.toString());
    }

    // Optional Year (1900..2100)
    const year = url.searchParams.get("year");
    if (year !== null) {
      const yearNum = parseInt(year, 10);
      if (isNaN(yearNum) || yearNum < 1900 || yearNum > 2100) {
        return new Response(
          JSON.stringify({ error: "Invalid 'year' parameter: must be between 1900 and 2100." }),
          { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }
      upstreamParams.set("year", yearNum.toString());
    }

    // Allowed pass-through parameters with validation
    const allowedParamMap: Record<string, RegExp> = {
      sort_by: /^[a-z_]+(\.(asc|desc))?$/,
      with_release_type: /^[0-9|]+$/,
      "primary_release_date.lte": /^\d{4}-\d{2}-\d{2}$/,
      "vote_count.gte": /^\d{1,6}$/,
      with_original_language: /^[a-z]{2,3}$/,
      append_to_response: /^[a-z,]+$/,
      include_adult: /^(true|false)$/,
    };

    for (const [paramName, regex] of Object.entries(allowedParamMap)) {
      const val = url.searchParams.get(paramName);
      if (val !== null) {
        if (!regex.test(val)) {
          return new Response(
            JSON.stringify({ error: `Invalid format for parameter '${paramName}'.` }),
            { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
          );
        }
        upstreamParams.set(paramName, val);
      }
    }

    // 7. Inject TMDb authentication credentials (Bearer or api_key param)
    const headers: Record<string, string> = {
      Accept: "application/json",
    };

    if (tmdbKey.startsWith("eyJ")) {
      headers["Authorization"] = `Bearer ${tmdbKey}`;
    } else {
      upstreamParams.set("api_key", tmdbKey);
    }

    // 8. Execute upstream TMDb request
    const tmdbUrl = `${TMDB_API_BASE}${normalizedPath}?${upstreamParams.toString()}`;
    const upstreamRes = await fetch(tmdbUrl, {
      method: "GET",
      headers,
    });

    const responseData = await upstreamRes.text();
    return new Response(responseData, {
      status: upstreamRes.status,
      headers: {
        ...corsHeaders,
        "Content-Type": upstreamRes.headers.get("Content-Type") || "application/json",
        "Cache-Control": "public, max-age=3600",
      },
    });
  } catch (err) {
    return new Response(
      JSON.stringify({ error: "Internal TMDb Proxy Error", details: String(err) }),
      { status: 502, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
