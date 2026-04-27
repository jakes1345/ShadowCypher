/**
 * Stripe billing endpoints.
 *
 * Endpoints:
 *   POST /v1/billing/checkout   — create Checkout session, return URL
 *   POST /v1/billing/portal     — create Customer Portal session, return URL
 *   POST /v1/billing/webhook    — Stripe → us (events: subscription created/updated/deleted)
 *
 * Secrets needed (set via wrangler secret put):
 *   STRIPE_SECRET_KEY           — sk_test_… or sk_live_…
 *   STRIPE_WEBHOOK_SECRET       — whsec_… (from Stripe webhook configuration)
 *   STRIPE_PRICE_GUARDIAN_PRO   — price_… for $9.99/mo plan
 *   STRIPE_PRICE_OPERATOR       — price_… for $49/mo plan
 *
 * Public-safe vars (in wrangler.toml [vars]):
 *   SITE_URL                    — https://shadowcypher.site (for success_url / cancel_url)
 */

import type { Env } from "./index";
import { dbSelect, dbUpdate, dbUpsert } from "./supabase";

interface AuthedUser {
  id: string;
  email: string;
}

const json = (body: unknown, init: ResponseInit = {}, cors: HeadersInit = {}): Response =>
  new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", ...cors, ...(init.headers || {}) },
  });

// ─── Stripe REST helper (no SDK — keeps Worker bundle small) ────────────────

async function stripeForm(
  env: Env,
  path: string,
  body: Record<string, string>
): Promise<Record<string, unknown>> {
  const params = new URLSearchParams(body);
  const resp = await fetch(`https://api.stripe.com/v1${path}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.STRIPE_SECRET_KEY}`,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: params.toString(),
  });
  if (!resp.ok) throw new Error(`stripe_${resp.status}:${await resp.text()}`);
  return (await resp.json()) as Record<string, unknown>;
}

interface Profile {
  user_id: string;
  email: string | null;
  plan: string;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
}

async function getOrCreateCustomer(env: Env, user: AuthedUser): Promise<string> {
  const rows = await dbSelect<Profile>(env, "profiles", {
    select: "user_id,email,plan,stripe_customer_id,stripe_subscription_id",
    filters: { user_id: `eq.${user.id}` },
    limit: 1,
  });
  if (rows[0]?.stripe_customer_id) return rows[0].stripe_customer_id;

  const customer = (await stripeForm(env, "/customers", {
    email: user.email,
    "metadata[supabase_user_id]": user.id,
  })) as { id: string };

  await dbUpsert(
    env,
    "profiles",
    { user_id: user.id, email: user.email, stripe_customer_id: customer.id },
    "user_id"
  );
  return customer.id;
}

// ─── Handlers ───────────────────────────────────────────────────────────────

export async function createCheckout(req: Request, env: Env, user: AuthedUser, cors: HeadersInit) {
  const body = (await req.json().catch(() => ({}))) as { plan?: "guardian_pro" | "operator" };
  const priceId =
    body.plan === "operator" ? env.STRIPE_PRICE_OPERATOR : env.STRIPE_PRICE_GUARDIAN_PRO;
  if (!priceId) return json({ error: "price_not_configured" }, { status: 500 }, cors);

  const customerId = await getOrCreateCustomer(env, user);
  const site = env.SITE_URL || "https://shadowcypher.site";

  const session = (await stripeForm(env, "/checkout/sessions", {
    customer: customerId,
    mode: "subscription",
    "line_items[0][price]": priceId,
    "line_items[0][quantity]": "1",
    success_url: `${site}/?checkout=success&session_id={CHECKOUT_SESSION_ID}`,
    cancel_url: `${site}/?checkout=canceled`,
    "metadata[supabase_user_id]": user.id,
    "subscription_data[metadata][supabase_user_id]": user.id,
    allow_promotion_codes: "true",
  })) as { id: string; url: string };

  return json({ url: session.url, session_id: session.id }, {}, cors);
}

export async function createPortal(req: Request, env: Env, user: AuthedUser, cors: HeadersInit) {
  const customerId = await getOrCreateCustomer(env, user);
  const site = env.SITE_URL || "https://shadowcypher.site";

  const portal = (await stripeForm(env, "/billing_portal/sessions", {
    customer: customerId,
    return_url: `${site}/?account=1`,
  })) as { url: string };

  return json({ url: portal.url }, {}, cors);
}

// ─── Webhook signature verification (HMAC-SHA256, no deps) ──────────────────

async function verifyStripeSignature(
  payload: string,
  header: string,
  secret: string,
  toleranceSec = 300
): Promise<boolean> {
  const parts = Object.fromEntries(
    header.split(",").map((kv) => {
      const [k, ...rest] = kv.split("=");
      return [k, rest.join("=")];
    })
  );
  const t = parts.t;
  const v1 = parts.v1;
  if (!t || !v1) return false;

  const ts = parseInt(t, 10);
  if (Number.isNaN(ts)) return false;
  if (Math.abs(Date.now() / 1000 - ts) > toleranceSec) return false;

  const signedPayload = `${t}.${payload}`;
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sigBytes = new Uint8Array(await crypto.subtle.sign("HMAC", key, enc.encode(signedPayload)));
  const expected = Array.from(sigBytes, (b) => b.toString(16).padStart(2, "0")).join("");

  // Constant-time compare
  if (expected.length !== v1.length) return false;
  let diff = 0;
  for (let i = 0; i < expected.length; i++) {
    diff |= expected.charCodeAt(i) ^ v1.charCodeAt(i);
  }
  return diff === 0;
}

function planFromPriceId(env: Env, priceId: string): string {
  if (priceId === env.STRIPE_PRICE_GUARDIAN_PRO) return "guardian_pro";
  if (priceId === env.STRIPE_PRICE_OPERATOR) return "operator";
  return "community";
}

export async function handleWebhook(req: Request, env: Env, cors: HeadersInit): Promise<Response> {
  const payload = await req.text();
  const sig = req.headers.get("stripe-signature") || "";
  if (!sig) return json({ error: "missing_signature" }, { status: 400 }, cors);
  if (!env.STRIPE_WEBHOOK_SECRET) {
    return json({ error: "webhook_secret_not_configured" }, { status: 500 }, cors);
  }

  const valid = await verifyStripeSignature(payload, sig, env.STRIPE_WEBHOOK_SECRET);
  if (!valid) return json({ error: "invalid_signature" }, { status: 400 }, cors);

  const event = JSON.parse(payload) as { type: string; data: { object: Record<string, unknown> } };
  const obj = event.data.object;

  try {
    switch (event.type) {
      case "checkout.session.completed":
      case "customer.subscription.created":
      case "customer.subscription.updated": {
        const customerId = (obj.customer as string) || null;
        const subId = (obj.id as string) || (obj.subscription as string) || null;
        const status = (obj.status as string) || null;
        const periodEnd = (obj.current_period_end as number) || null;
        const cancelAtEnd = Boolean(obj.cancel_at_period_end);
        const items = ((obj.items as Record<string, unknown>)?.data as Array<{ price: { id: string } }>) || [];
        const priceId = items[0]?.price?.id;
        const plan = priceId ? planFromPriceId(env, priceId) : "community";
        if (!customerId) break;

        const profiles = await dbSelect<Profile>(env, "profiles", {
          select: "user_id",
          filters: { stripe_customer_id: `eq.${customerId}` },
          limit: 1,
        });
        if (!profiles[0]) break;

        await dbUpdate(
          env,
          "profiles",
          { user_id: `eq.${profiles[0].user_id}` },
          {
            plan,
            stripe_subscription_id: subId,
            subscription_status: status,
            current_period_end: periodEnd ? new Date(periodEnd * 1000).toISOString() : null,
            cancel_at_period_end: cancelAtEnd,
            updated_at: new Date().toISOString(),
          }
        );
        break;
      }

      case "customer.subscription.deleted": {
        const customerId = obj.customer as string;
        if (!customerId) break;
        const profiles = await dbSelect<Profile>(env, "profiles", {
          select: "user_id",
          filters: { stripe_customer_id: `eq.${customerId}` },
          limit: 1,
        });
        if (!profiles[0]) break;
        await dbUpdate(env, "profiles", { user_id: `eq.${profiles[0].user_id}` }, {
          plan: "community",
          subscription_status: "canceled",
          stripe_subscription_id: null,
          cancel_at_period_end: false,
          updated_at: new Date().toISOString(),
        });
        break;
      }
    }
  } catch (err) {
    console.error("[webhook] handler failed", err);
    return json({ error: "handler_failed" }, { status: 500 }, cors);
  }

  return json({ received: true }, {}, cors);
}
