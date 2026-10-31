/**
 * ShadowCypher merch shop — Printful (print-on-demand) + Stripe Checkout.
 *
 * Endpoints (all public, no API key):
 *   GET  /v1/shop/products  — live catalogue read from the Printful store
 *   POST /v1/shop/checkout  — create a Stripe Checkout session for a cart
 *   (fulfilment runs from the existing Stripe webhook: /v1/billing/webhook)
 *
 * Flow:
 *   1. Products are created once in the Printful dashboard from the print files
 *      in merch/drop01/print/. Printful holds names, sizes, retail prices and
 *      photo mockups; this module reads them, so nothing is hard-coded here.
 *   2. Checkout re-reads prices server-side (the client only sends variant ids
 *      and quantities) and opens a Stripe Checkout session in payment mode.
 *   3. On checkout.session.completed (kind=shop, paid) the webhook submits the
 *      order to Printful. Orders land as Printful DRAFTS unless
 *      SHOP_AUTO_CONFIRM="true", so the first orders can be checked by hand.
 *
 * Secrets / vars:
 *   PRINTFUL_API_TOKEN        secret — Printful private token (orders + store read)
 *   PRINTFUL_STORE_ID         var    — needed only for account-level tokens
 *   SHOP_AUTO_CONFIRM         var    — "true" sends paid orders straight to production
 *   SHOP_SHIPPING_CENTS       var    — flat shipping, default 699
 *   SHOP_FREE_SHIPPING_CENTS  var    — free shipping at/above this subtotal, default 7500
 *   SHOP_SHIP_COUNTRIES       var    — comma list of ISO countries Stripe will accept
 *   STRIPE_SECRET_KEY / STRIPE_WEBHOOK_SECRET — shared with billing.ts
 */

import type { Env } from "./index";
import { stripeForm } from "./billing";

const PRINTFUL = "https://api.printful.com";
const CATALOG_TTL_MS = 5 * 60_000;
const MAX_LINES = 20;
const MAX_QTY = 10;
const DEFAULT_COUNTRIES =
  "US,CA,GB,IE,AU,NZ,DE,FR,NL,BE,LU,ES,PT,IT,AT,CH,SE,DK,NO,FI,PL,CZ,JP";

export interface ShopVariant {
  id: number;            // Printful sync_variant_id
  name: string;
  size: string | null;
  color: string | null;
  price_cents: number;
  currency: string;
  image: string | null;
  available: boolean;
}

export interface ShopProduct {
  id: number;            // Printful sync_product id
  name: string;
  thumbnail: string | null;
  variants: ShopVariant[];
}

interface PfSyncProduct {
  id: number;
  name: string;
  thumbnail_url?: string | null;
  is_ignored?: boolean;
}

interface PfSyncVariant {
  id: number;
  name: string;
  retail_price: string | null;
  currency: string | null;
  is_ignored?: boolean;
  size?: string | null;
  color?: string | null;
  availability_status?: string | null;
  synced?: boolean;
  product?: { image?: string | null };
  files?: Array<{ type: string; preview_url?: string | null; thumbnail_url?: string | null }>;
}

const json = (body: unknown, init: ResponseInit = {}, cors: HeadersInit = {}): Response =>
  new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", ...cors, ...(init.headers || {}) },
  });

export function shopConfigured(env: Env): boolean {
  return Boolean(env.PRINTFUL_API_TOKEN && env.STRIPE_SECRET_KEY);
}

async function printful<T>(env: Env, path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${env.PRINTFUL_API_TOKEN}`,
    "Content-Type": "application/json",
  };
  if (env.PRINTFUL_STORE_ID) headers["X-PF-Store-Id"] = env.PRINTFUL_STORE_ID;
  const resp = await fetch(`${PRINTFUL}${path}`, { ...init, headers: { ...headers, ...(init.headers || {}) } });
  const text = await resp.text();
  if (!resp.ok) throw new PrintfulError(resp.status, text);
  return (JSON.parse(text) as { result: T }).result;
}

export class PrintfulError extends Error {
  constructor(public status: number, public body: string) {
    super(`printful_${status}`);
  }
}

// ─── Catalogue ──────────────────────────────────────────────────────────────

/** Price string "34.00" → 3400 cents, without float drift. */
export function toCents(price: string | null | undefined): number | null {
  if (price == null) return null;
  const m = /^\s*(\d+)(?:\.(\d{1,2}))?\s*$/.exec(price);
  if (!m) return null;
  return parseInt(m[1], 10) * 100 + parseInt((m[2] || "0").padEnd(2, "0"), 10);
}

/** "Ghost Mode Tee / Black / XL" → { color: "Black", size: "XL" } */
export function parseVariantName(name: string): { color: string | null; size: string | null } {
  const parts = name.split(" / ").map((p) => p.trim());
  if (parts.length >= 3) return { color: parts[parts.length - 2], size: parts[parts.length - 1] };
  if (parts.length === 2) return { color: null, size: parts[1] };
  return { color: null, size: null };
}

export function normaliseProduct(p: PfSyncProduct, variants: PfSyncVariant[]): ShopProduct | null {
  if (p.is_ignored) return null;
  const out: ShopVariant[] = [];
  for (const v of variants) {
    if (v.is_ignored) continue;
    const cents = toCents(v.retail_price);
    if (cents === null || cents <= 0) continue;   // never sell an unpriced variant
    const parsed = parseVariantName(v.name);
    const preview = v.files?.find((f) => f.type === "preview")?.preview_url ?? null;
    out.push({
      id: v.id,
      name: v.name,
      size: v.size ?? parsed.size,
      color: v.color ?? parsed.color,
      price_cents: cents,
      currency: (v.currency || "USD").toUpperCase(),
      image: preview || v.product?.image || p.thumbnail_url || null,
      available: v.synced !== false && (v.availability_status ?? "active") === "active",
    });
  }
  if (!out.length) return null;
  return { id: p.id, name: p.name, thumbnail: p.thumbnail_url ?? null, variants: out };
}

let cache: { at: number; products: ShopProduct[] } | null = null;

export function _resetCatalogCache() {
  cache = null;
}

export async function loadCatalog(env: Env): Promise<ShopProduct[]> {
  if (cache && Date.now() - cache.at < CATALOG_TTL_MS) return cache.products;
  const list = await printful<PfSyncProduct[]>(env, "/store/products?limit=100");
  const products: ShopProduct[] = [];
  for (const p of list) {
    if (p.is_ignored) continue;
    const detail = await printful<{ sync_product: PfSyncProduct; sync_variants: PfSyncVariant[] }>(
      env,
      `/store/products/${p.id}`
    );
    const norm = normaliseProduct(detail.sync_product, detail.sync_variants);
    if (norm) products.push(norm);
  }
  cache = { at: Date.now(), products };
  return products;
}

export async function getProducts(_req: Request, env: Env, cors: HeadersInit): Promise<Response> {
  if (!shopConfigured(env)) return json({ open: false, products: [] }, {}, cors);
  try {
    const products = await loadCatalog(env);
    return json({ open: products.length > 0, products }, {
      headers: { "Cache-Control": "public, max-age=120" },
    }, cors);
  } catch (err) {
    console.error("[shop] catalog failed", err instanceof Error ? err.message : err);
    return json({ error: "catalog_unavailable" }, { status: 502 }, cors);
  }
}

// ─── Checkout ───────────────────────────────────────────────────────────────

export interface CartLine {
  variant_id: number;
  quantity: number;
}

export function parseCart(body: unknown): CartLine[] | string {
  const items = (body as { items?: unknown })?.items;
  if (!Array.isArray(items) || items.length === 0) return "empty_cart";
  if (items.length > MAX_LINES) return "too_many_items";
  const merged = new Map<number, number>();
  for (const raw of items) {
    const id = Number((raw as CartLine)?.variant_id);
    const qty = Number((raw as CartLine)?.quantity);
    if (!Number.isInteger(id) || id <= 0) return "invalid_variant";
    if (!Number.isInteger(qty) || qty < 1 || qty > MAX_QTY) return "invalid_quantity";
    merged.set(id, (merged.get(id) || 0) + qty);
  }
  for (const q of merged.values()) if (q > MAX_QTY) return "invalid_quantity";
  return [...merged.entries()].map(([variant_id, quantity]) => ({ variant_id, quantity }));
}

/** Compact "id:qty,id:qty" — fits Stripe's 500-char metadata value limit. */
export function encodeItems(lines: CartLine[]): string {
  return lines.map((l) => `${l.variant_id}:${l.quantity}`).join(",");
}

export function decodeItems(s: string | undefined | null): CartLine[] {
  if (!s) return [];
  return s.split(",").flatMap((pair) => {
    const [a, b] = pair.split(":");
    const variant_id = parseInt(a, 10);
    const quantity = parseInt(b, 10);
    return Number.isInteger(variant_id) && Number.isInteger(quantity) && quantity > 0
      ? [{ variant_id, quantity }]
      : [];
  });
}

export function shippingCents(env: Env, subtotal: number): number {
  const flat = parseInt(env.SHOP_SHIPPING_CENTS || "699", 10);
  const freeAt = parseInt(env.SHOP_FREE_SHIPPING_CENTS || "7500", 10);
  return freeAt > 0 && subtotal >= freeAt ? 0 : flat;
}

export async function createShopCheckout(req: Request, env: Env, cors: HeadersInit): Promise<Response> {
  if (!shopConfigured(env)) return json({ error: "shop_closed" }, { status: 503 }, cors);
  const cart = parseCart(await req.json().catch(() => null));
  if (typeof cart === "string") return json({ error: cart }, { status: 400 }, cors);

  let products: ShopProduct[];
  try {
    products = await loadCatalog(env);
  } catch {
    return json({ error: "catalog_unavailable" }, { status: 502 }, cors);
  }
  const byId = new Map<number, { product: ShopProduct; variant: ShopVariant }>();
  for (const p of products) for (const v of p.variants) byId.set(v.id, { product: p, variant: v });

  const site = env.SITE_URL || "https://shadowcypher.site";
  const form: Record<string, string> = {
    mode: "payment",
    success_url: `${site}/shop.html?order=success&session_id={CHECKOUT_SESSION_ID}`,
    cancel_url: `${site}/shop.html?order=canceled`,
    "metadata[kind]": "shop",
    "metadata[items]": encodeItems(cart),
    "payment_intent_data[metadata][kind]": "shop",
    "phone_number_collection[enabled]": "true",
    billing_address_collection: "auto",
  };

  let subtotal = 0;
  let currency = "";
  cart.forEach((line, i) => {
    const hit = byId.get(line.variant_id);
    if (!hit || !hit.variant.available) throw new CartError("variant_unavailable");
    const cur = hit.variant.currency.toLowerCase();
    if (currency && cur !== currency) throw new CartError("mixed_currency");
    currency = cur;
    subtotal += hit.variant.price_cents * line.quantity;
    const k = `line_items[${i}]`;
    form[`${k}[quantity]`] = String(line.quantity);
    form[`${k}[price_data][currency]`] = cur;
    form[`${k}[price_data][unit_amount]`] = String(hit.variant.price_cents);
    form[`${k}[price_data][product_data][name]`] = hit.variant.name;
    form[`${k}[price_data][product_data][metadata][sync_variant_id]`] = String(hit.variant.id);
    if (hit.variant.image) form[`${k}[price_data][product_data][images][0]`] = hit.variant.image;
  });

  const ship = shippingCents(env, subtotal);
  form["shipping_options[0][shipping_rate_data][type]"] = "fixed_amount";
  form["shipping_options[0][shipping_rate_data][fixed_amount][amount]"] = String(ship);
  form["shipping_options[0][shipping_rate_data][fixed_amount][currency]"] = currency;
  form["shipping_options[0][shipping_rate_data][display_name]"] =
    ship === 0 ? "Free standard shipping" : "Standard shipping";
  form["shipping_options[0][shipping_rate_data][delivery_estimate][minimum][unit]"] = "business_day";
  form["shipping_options[0][shipping_rate_data][delivery_estimate][minimum][value]"] = "5";
  form["shipping_options[0][shipping_rate_data][delivery_estimate][maximum][unit]"] = "business_day";
  form["shipping_options[0][shipping_rate_data][delivery_estimate][maximum][value]"] = "12";
  (env.SHOP_SHIP_COUNTRIES || DEFAULT_COUNTRIES)
    .split(",")
    .map((c) => c.trim().toUpperCase())
    .filter((c) => /^[A-Z]{2}$/.test(c))
    .forEach((c, i) => (form[`shipping_address_collection[allowed_countries][${i}]`] = c));

  const session = (await stripeForm(env, "/checkout/sessions", form)) as { id: string; url: string };
  return json({ url: session.url, session_id: session.id }, {}, cors);
}

class CartError extends Error {}

export async function handleShopCheckout(req: Request, env: Env, cors: HeadersInit): Promise<Response> {
  try {
    return await createShopCheckout(req, env, cors);
  } catch (err) {
    if (err instanceof CartError) return json({ error: err.message }, { status: 409 }, cors);
    console.error("[shop] checkout failed", err instanceof Error ? err.message : err);
    return json({ error: "checkout_failed" }, { status: 502 }, cors);
  }
}

// ─── Fulfilment (called from the Stripe webhook) ────────────────────────────

interface StripeAddress {
  line1?: string | null;
  line2?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  country?: string | null;
}

interface CheckoutSessionLike {
  id: string;
  payment_status?: string;
  payment_intent?: string | null;
  metadata?: Record<string, string> | null;
  customer_details?: { email?: string | null; name?: string | null; phone?: string | null } | null;
  shipping_details?: { name?: string | null; address?: StripeAddress | null } | null;
  collected_information?: { shipping_details?: { name?: string | null; address?: StripeAddress | null } | null } | null;
  total_details?: { amount_shipping?: number | null; amount_tax?: number | null } | null;
  amount_subtotal?: number | null;
  amount_total?: number | null;
}

export function isShopSession(obj: Record<string, unknown>): boolean {
  return (obj.metadata as Record<string, string> | undefined)?.kind === "shop";
}

/** Deterministic 32-char Printful external_id for a Stripe session (idempotency key). */
export async function externalIdFor(sessionId: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(sessionId));
  const hex = Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
  return `sc${hex.slice(0, 30)}`;
}

export function buildPrintfulOrder(s: CheckoutSessionLike, externalId: string) {
  const ship = s.collected_information?.shipping_details ?? s.shipping_details ?? null;
  const addr = ship?.address;
  if (!addr?.line1 || !addr.city || !addr.country) throw new Error("missing_shipping_address");
  const items = decodeItems(s.metadata?.items);
  if (!items.length) throw new Error("missing_items");
  const money = (c: number | null | undefined) => ((c ?? 0) / 100).toFixed(2);
  return {
    external_id: externalId,
    shipping: "STANDARD",
    recipient: {
      name: ship?.name || s.customer_details?.name || "Customer",
      address1: addr.line1,
      address2: addr.line2 || undefined,
      city: addr.city,
      state_code: addr.state || undefined,
      country_code: addr.country,
      zip: addr.postal_code || undefined,
      email: s.customer_details?.email || undefined,
      phone: s.customer_details?.phone || undefined,
    },
    items: items.map((l) => ({ sync_variant_id: l.variant_id, quantity: l.quantity })),
    retail_costs: {
      currency: "USD",
      subtotal: money(s.amount_subtotal),
      shipping: money(s.total_details?.amount_shipping),
      tax: money(s.total_details?.amount_tax),
      total: money(s.amount_total),
    },
  };
}

export async function fulfillShopSession(env: Env, obj: Record<string, unknown>): Promise<void> {
  const s = obj as unknown as CheckoutSessionLike;
  if (s.payment_status !== "paid") {
    console.log("[shop] session not paid yet, waiting for async_payment_succeeded", s.id);
    return;
  }
  if (!env.PRINTFUL_API_TOKEN) throw new Error("printful_not_configured");
  const externalId = await externalIdFor(s.id);

  // Idempotency: Stripe retries webhooks, so skip if this order already exists.
  try {
    await printful(env, `/orders/@${externalId}`);
    console.log("[shop] order already submitted", externalId);
    return;
  } catch (err) {
    if (!(err instanceof PrintfulError) || err.status !== 404) throw err;
  }

  const order = buildPrintfulOrder(s, externalId);
  const confirm = env.SHOP_AUTO_CONFIRM === "true";
  const created = await printful<{ id: number; status: string }>(env, `/orders?confirm=${confirm}`, {
    method: "POST",
    body: JSON.stringify(order),
  });
  console.log("[shop] printful order", created.id, created.status, externalId);
}
