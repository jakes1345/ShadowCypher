import { afterEach, describe, expect, it, vi } from "vitest";
import {
  _resetCatalogCache,
  buildPrintfulOrder,
  decodeItems,
  encodeItems,
  externalIdFor,
  fulfillShopSession,
  handleShopCheckout,
  normaliseProduct,
  parseCart,
  parseVariantName,
  shippingCents,
  toCents,
} from "../shop";
import type { Env } from "../index";

const env = {
  PRINTFUL_API_TOKEN: "pf_test",
  STRIPE_SECRET_KEY: "sk_test_x",
  SITE_URL: "https://shadowcypher.site",
} as unknown as Env;

afterEach(() => {
  vi.unstubAllGlobals();
  _resetCatalogCache();
});

describe("toCents", () => {
  it("parses Printful price strings exactly", () => {
    expect(toCents("34.00")).toBe(3400);
    expect(toCents("29.5")).toBe(2950);
    expect(toCents("5")).toBe(500);
    expect(toCents("19.99")).toBe(1999);
  });
  it("rejects junk", () => {
    expect(toCents(null)).toBeNull();
    expect(toCents("abc")).toBeNull();
    expect(toCents("1.999")).toBeNull();
  });
});

describe("parseVariantName", () => {
  it("splits product / colour / size", () => {
    expect(parseVariantName("Ghost Mode Tee / Black / XL")).toEqual({ color: "Black", size: "XL" });
    expect(parseVariantName("Encrypted Seal Sticker / 4″×4″")).toEqual({ color: null, size: "4″×4″" });
    expect(parseVariantName("Mug")).toEqual({ color: null, size: null });
  });
});

describe("normaliseProduct", () => {
  it("drops ignored and unpriced variants and picks the mockup preview", () => {
    const p = normaliseProduct({ id: 1, name: "Ghost Mode Tee", thumbnail_url: "t.png" }, [
      { id: 10, name: "Ghost Mode Tee / Black / M", retail_price: "34.00", currency: "USD",
        files: [{ type: "back" }, { type: "preview", preview_url: "m.png" }] },
      { id: 11, name: "Ghost Mode Tee / Black / L", retail_price: null, currency: "USD" },
      { id: 12, name: "Ghost Mode Tee / Black / XL", retail_price: "34.00", currency: "USD", is_ignored: true },
    ]);
    expect(p?.variants.map((v) => v.id)).toEqual([10]);
    expect(p?.variants[0]).toMatchObject({ size: "M", color: "Black", price_cents: 3400, image: "m.png", available: true });
  });
  it("returns null when nothing is sellable", () => {
    expect(normaliseProduct({ id: 1, name: "x" }, [])).toBeNull();
    expect(normaliseProduct({ id: 1, name: "x", is_ignored: true }, [
      { id: 2, name: "x / M", retail_price: "1.00", currency: "USD" },
    ])).toBeNull();
  });
});

describe("parseCart", () => {
  it("merges duplicate lines", () => {
    expect(parseCart({ items: [{ variant_id: 5, quantity: 1 }, { variant_id: 5, quantity: 2 }] }))
      .toEqual([{ variant_id: 5, quantity: 3 }]);
  });
  it("rejects bad carts", () => {
    expect(parseCart(null)).toBe("empty_cart");
    expect(parseCart({ items: [] })).toBe("empty_cart");
    expect(parseCart({ items: [{ variant_id: "x", quantity: 1 }] })).toBe("invalid_variant");
    expect(parseCart({ items: [{ variant_id: 1, quantity: 0 }] })).toBe("invalid_quantity");
    expect(parseCart({ items: [{ variant_id: 1, quantity: 1.5 }] })).toBe("invalid_quantity");
    expect(parseCart({ items: [{ variant_id: 1, quantity: 6 }, { variant_id: 1, quantity: 6 }] })).toBe("invalid_quantity");
    expect(parseCart({ items: Array.from({ length: 21 }, (_, i) => ({ variant_id: i + 1, quantity: 1 })) }))
      .toBe("too_many_items");
  });
});

describe("item metadata encoding", () => {
  it("round-trips", () => {
    const lines = [{ variant_id: 4011, quantity: 2 }, { variant_id: 9, quantity: 1 }];
    expect(decodeItems(encodeItems(lines))).toEqual(lines);
    expect(decodeItems("")).toEqual([]);
    expect(decodeItems("1:x,2:3")).toEqual([{ variant_id: 2, quantity: 3 }]);
  });
});

describe("shippingCents", () => {
  it("is flat below the threshold and free at or above it", () => {
    expect(shippingCents(env, 3400)).toBe(699);
    expect(shippingCents(env, 7500)).toBe(0);
    expect(shippingCents({ ...env, SHOP_SHIPPING_CENTS: "500", SHOP_FREE_SHIPPING_CENTS: "0" } as Env, 99999)).toBe(500);
  });
});

describe("externalIdFor", () => {
  it("is deterministic and 32 chars", async () => {
    const a = await externalIdFor("cs_live_abc");
    expect(a).toHaveLength(32);
    expect(a).toBe(await externalIdFor("cs_live_abc"));
    expect(a).not.toBe(await externalIdFor("cs_live_abd"));
  });
});

const paidSession = {
  id: "cs_test_1",
  payment_status: "paid",
  metadata: { kind: "shop", items: "101:2,202:1" },
  customer_details: { email: "a@b.co", name: "Ada", phone: "+15551234567" },
  collected_information: {
    shipping_details: {
      name: "Ada L",
      address: { line1: "1 Main St", line2: null, city: "Geneva", state: "IL", postal_code: "60134", country: "US" },
    },
  },
  amount_subtotal: 6800,
  amount_total: 6800,
  total_details: { amount_shipping: 0, amount_tax: 0 },
};

describe("buildPrintfulOrder", () => {
  it("maps a paid Stripe session to a Printful order", () => {
    const o = buildPrintfulOrder(paidSession, "scX");
    expect(o.recipient).toMatchObject({ name: "Ada L", address1: "1 Main St", city: "Geneva", state_code: "IL", country_code: "US", zip: "60134", email: "a@b.co" });
    expect(o.items).toEqual([{ sync_variant_id: 101, quantity: 2 }, { sync_variant_id: 202, quantity: 1 }]);
    expect(o.retail_costs.total).toBe("68.00");
  });
  it("falls back to legacy shipping_details", () => {
    const { collected_information: _c, ...legacy } = paidSession;
    const o = buildPrintfulOrder({ ...legacy, shipping_details: paidSession.collected_information.shipping_details }, "scX");
    expect(o.recipient.city).toBe("Geneva");
  });
  it("refuses a session without an address", () => {
    expect(() => buildPrintfulOrder({ ...paidSession, collected_information: null }, "scX")).toThrow("missing_shipping_address");
  });
});

function pfResponse(status: number, result: unknown) {
  return new Response(JSON.stringify(status < 400 ? { code: status, result } : { code: status, error: { message: "x" } }), { status });
}

describe("fulfillShopSession", () => {
  it("creates a draft order when none exists", async () => {
    const calls: Array<{ url: string; init?: RequestInit }> = [];
    vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
      calls.push({ url, init });
      if (url.includes("/orders/@")) return pfResponse(404, null);
      return pfResponse(200, { id: 77, status: "draft" });
    }));
    await fulfillShopSession(env, paidSession);
    expect(calls).toHaveLength(2);
    expect(calls[1].url).toBe("https://api.printful.com/orders?confirm=false");
    expect(JSON.parse(String(calls[1].init?.body)).items).toHaveLength(2);
  });
  it("confirms straight to production when SHOP_AUTO_CONFIRM=true", async () => {
    const urls: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      urls.push(url);
      return url.includes("/orders/@") ? pfResponse(404, null) : pfResponse(200, { id: 1, status: "pending" });
    }));
    await fulfillShopSession({ ...env, SHOP_AUTO_CONFIRM: "true" } as Env, paidSession);
    expect(urls[1]).toBe("https://api.printful.com/orders?confirm=true");
  });
  it("is idempotent across webhook retries", async () => {
    const f = vi.fn(async () => pfResponse(200, { id: 77 }));
    vi.stubGlobal("fetch", f);
    await fulfillShopSession(env, paidSession);
    expect(f).toHaveBeenCalledTimes(1);
  });
  it("waits on unpaid sessions", async () => {
    const f = vi.fn();
    vi.stubGlobal("fetch", f);
    await fulfillShopSession(env, { ...paidSession, payment_status: "unpaid" });
    expect(f).not.toHaveBeenCalled();
  });
});

describe("handleShopCheckout", () => {
  function stubCatalogAndStripe(capture: { form?: URLSearchParams }) {
    vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/store/products?limit=100")) return pfResponse(200, [{ id: 1, name: "Ghost Mode Tee" }]);
      if (url.endsWith("/store/products/1"))
        return pfResponse(200, {
          sync_product: { id: 1, name: "Ghost Mode Tee" },
          sync_variants: [{ id: 101, name: "Ghost Mode Tee / Black / M", retail_price: "34.00", currency: "USD" }],
        });
      if (url.startsWith("https://api.stripe.com/v1/checkout/sessions")) {
        capture.form = new URLSearchParams(String(init?.body));
        return new Response(JSON.stringify({ id: "cs_1", url: "https://checkout.stripe.com/c/cs_1" }));
      }
      throw new Error(`unexpected ${url}`);
    }));
  }

  it("prices from Printful, not the client", async () => {
    const cap: { form?: URLSearchParams } = {};
    stubCatalogAndStripe(cap);
    const req = new Request("https://api/x", { method: "POST", body: JSON.stringify({ items: [{ variant_id: 101, quantity: 2, price: 1 }] }) });
    const res = await handleShopCheckout(req, env, {});
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ url: "https://checkout.stripe.com/c/cs_1", session_id: "cs_1" });
    expect(cap.form?.get("mode")).toBe("payment");
    expect(cap.form?.get("line_items[0][price_data][unit_amount]")).toBe("3400");
    expect(cap.form?.get("line_items[0][quantity]")).toBe("2");
    expect(cap.form?.get("metadata[kind]")).toBe("shop");
    expect(cap.form?.get("metadata[items]")).toBe("101:2");
    expect(cap.form?.get("shipping_options[0][shipping_rate_data][fixed_amount][amount]")).toBe("699");
    expect(cap.form?.get("shipping_address_collection[allowed_countries][0]")).toBe("US");
  });

  it("gives free shipping over the threshold", async () => {
    const cap: { form?: URLSearchParams } = {};
    stubCatalogAndStripe(cap);
    const req = new Request("https://api/x", { method: "POST", body: JSON.stringify({ items: [{ variant_id: 101, quantity: 3 }] }) });
    await handleShopCheckout(req, env, {});
    expect(cap.form?.get("shipping_options[0][shipping_rate_data][fixed_amount][amount]")).toBe("0");
  });

  it("rejects variants that are not in the store", async () => {
    stubCatalogAndStripe({});
    const req = new Request("https://api/x", { method: "POST", body: JSON.stringify({ items: [{ variant_id: 999, quantity: 1 }] }) });
    const res = await handleShopCheckout(req, env, {});
    expect(res.status).toBe(409);
    expect(await res.json()).toEqual({ error: "variant_unavailable" });
  });

  it("is closed until Printful is configured", async () => {
    const req = new Request("https://api/x", { method: "POST", body: "{}" });
    const res = await handleShopCheckout(req, { ...env, PRINTFUL_API_TOKEN: undefined } as Env, {});
    expect(res.status).toBe(503);
  });
});
