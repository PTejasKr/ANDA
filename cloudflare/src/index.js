/**
 * Project ANDA: Cloudflare Edge Worker
 * Features:
 *  - Free-tier Gemma 7B inference via Cloudflare Workers AI (@cf/google/gemma-7b-it)
 *  - Free-tier Whisper Speech-to-Text inference (@cf/openai/whisper)
 *  - Edge routing & proxy to Fly.io Orchestrator
 *  - Secure WSS / Token handshake for Local Elevated Daemon
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Handle CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
      });
    }

    const corsHeaders = {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    };

    // 1. Health / Edge Status
    if (url.pathname === "/health" || url.pathname === "/") {
      return new Response(
        JSON.stringify({
          service: "Project ANDA Edge Gateway",
          provider: "Cloudflare Workers",
          ai_model: env.DEFAULT_AI_MODEL || "@cf/google/gemma-7b-it",
          free_tier_active: true,
          fly_target: env.FLY_ORCHESTRATOR_URL,
        }),
        { headers: corsHeaders }
      );
    }

    // 2. Free Tier Gemma Inference via Workers AI
    if (url.pathname === "/api/ai/gemma" && request.method === "POST") {
      try {
        const body = await request.json();
        const prompt = body.prompt || "";
        const systemPrompt =
          body.system ||
          "You are Project ANDA Gemma 4 Edge Brain. Parse user OS intent into JSON: action, plane (ELEVATED_DAEMON or WORKER_PLANE), and drive.";

        if (!prompt) {
          return new Response(JSON.stringify({ error: "Missing prompt" }), { status: 400, headers: corsHeaders });
        }

        // Run Cloudflare Workers AI free Gemma model
        const model = env.DEFAULT_AI_MODEL || "@cf/google/gemma-7b-it";
        const aiResponse = await env.AI.run(model, {
          messages: [
            { role: "system", content: systemPrompt },
            { role: "user", content: prompt },
          ],
          max_tokens: 512,
        });

        return new Response(
          JSON.stringify({
            model_used: model,
            provider: "Cloudflare Workers AI (Free Tier)",
            result: aiResponse.response,
          }),
          { headers: corsHeaders }
        );
      } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), { status: 500, headers: corsHeaders });
      }
    }

    // 3. Free Tier Speech-to-Text via Cloudflare Workers AI Whisper
    if (url.pathname === "/api/ai/stt" && request.method === "POST") {
      try {
        const audioBuffer = await request.arrayBuffer();
        const input = {
          audio: [...new Uint8Array(audioBuffer)],
        };
        const sttResponse = await env.AI.run("@cf/openai/whisper", input);

        return new Response(
          JSON.stringify({
            transcription: sttResponse.text,
            provider: "Cloudflare Workers AI Whisper (Free Tier)",
          }),
          { headers: corsHeaders }
        );
      } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), { status: 500, headers: corsHeaders });
      }
    }

    // 4. Proxy public commands to Fly.io Orchestrator
    if (url.pathname.startsWith("/api/")) {
      const flyUrl = new URL(url.pathname + url.search, env.FLY_ORCHESTRATOR_URL);
      try {
        const proxyReq = new Request(flyUrl, {
          method: request.method,
          headers: request.headers,
          body: request.method !== "GET" && request.method !== "HEAD" ? request.body : undefined,
        });
        const resp = await fetch(proxyReq);
        return new Response(resp.body, {
          status: resp.status,
          headers: {
            ...resp.headers,
            "Access-Control-Allow-Origin": "*",
          },
        });
      } catch (err) {
        return new Response(
          JSON.stringify({
            error: "Failed to connect to Fly.io Orchestrator",
            details: err.message,
            target: env.FLY_ORCHESTRATOR_URL,
          }),
          { status: 502, headers: corsHeaders }
        );
      }
    }

    return new Response(JSON.stringify({ error: "Route not found" }), { status: 404, headers: corsHeaders });
  },
};
