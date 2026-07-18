/**
 * Transactional email templates — sent via Resend.
 *
 * Triggered by:
 *   - New user signup  → sendWelcomeEmail()
 *   - First agent install → sendAgentOnboardEmail()
 *   - Key rotated      → sendKeyRotatedEmail()
 *
 * All functions are fire-and-forget safe (swallow errors, return bool).
 */

import type { Env } from "./index";

const FROM = (env: Env) =>
  env.RESEND_FROM_EMAIL || "ShadowCypher <noreply@shadowcypher.site>";

const BRAND_PURPLE = "#b44aff";
const BG = "#03030a";
const TEXT = "#e6e6e6";
const MUTED = "#888";

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c] as string)
  );
}

function baseTemplate(title: string, body: string, ctaHref: string, ctaLabel: string): string {
  return `
<div style="font-family:-apple-system,system-ui,'Segoe UI',sans-serif;max-width:600px;margin:0 auto;background:${BG};color:${TEXT};padding:40px 28px;">
  <div style="border-left:4px solid ${BRAND_PURPLE};padding-left:16px;margin-bottom:32px;">
    <div style="font-size:11px;letter-spacing:3px;color:${BRAND_PURPLE};text-transform:uppercase;font-weight:700;">SHADOWCYPHER</div>
  </div>

  <h1 style="font-size:22px;font-weight:700;color:#fff;margin:0 0 20px;line-height:1.3;">${title}</h1>

  ${body}

  <div style="margin-top:36px;">
    <a href="${ctaHref}"
       style="display:inline-block;background:${BRAND_PURPLE};color:#000;padding:13px 28px;text-decoration:none;font-weight:700;font-size:13px;letter-spacing:1px;">
      ${ctaLabel}
    </a>
  </div>

  <div style="margin-top:48px;padding-top:24px;border-top:1px solid #1a1a1a;">
    <p style="color:${MUTED};font-size:11px;margin:0;line-height:1.6;">
      You're receiving this because you signed up at
      <a href="https://shadowcypher.site" style="color:${BRAND_PURPLE};text-decoration:none;">shadowcypher.site</a>.
      <br>This is a no-reply address — do not reply to this email. Visit our
      <a href="https://shadowcypher.site/docs" style="color:${BRAND_PURPLE};text-decoration:none;">docs</a> for help.
    </p>
  </div>
</div>`;
}

async function send(
  env: Env,
  to: string,
  subject: string,
  html: string
): Promise<boolean> {
  if (!env.RESEND_API_KEY) return false;
  try {
    const resp = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.RESEND_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ from: FROM(env), to, subject, html }),
    });
    return resp.ok;
  } catch {
    return false;
  }
}

// ─── Welcome ─────────────────────────────────────────────────────────────────

export async function sendWelcomeEmail(
  env: Env,
  to: string,
  handle: string
): Promise<boolean> {
  const safeHandle = escapeHtml(handle);
  const body = `
    <p style="color:${TEXT};font-size:15px;line-height:1.7;margin:0 0 16px;">
      Hey <strong>${safeHandle}</strong>, welcome to ShadowCypher.
    </p>
    <p style="color:${TEXT};font-size:15px;line-height:1.7;margin:0 0 16px;">
      Your account is live. From your dashboard you can:
    </p>
    <ul style="color:#ccc;font-size:14px;line-height:2;padding-left:20px;margin:0 0 20px;">
      <li>Install the Guardian agent on any machine to start monitoring</li>
      <li>Set up incident alerts (email + web push)</li>
      <li>Run recon and OSINT tools from the desktop app</li>
      <li>Manage your API key and upgrade your plan</li>
    </ul>
    <p style="color:${MUTED};font-size:13px;line-height:1.6;margin:0;">
      Your API key is in the dashboard under <strong>Settings → API Key</strong>.
      Keep it secret — it grants full access to your account.
    </p>`;

  return send(
    env,
    to,
    "Welcome to ShadowCypher",
    baseTemplate("You're in.", body, "https://shadowcypher.site", "OPEN DASHBOARD")
  );
}

// ─── First agent registered ───────────────────────────────────────────────────

export async function sendAgentOnboardEmail(
  env: Env,
  to: string,
  handle: string,
  hostname: string
): Promise<boolean> {
  const safeHandle = escapeHtml(handle);
  const safeHost = escapeHtml(hostname);
  const body = `
    <p style="color:${TEXT};font-size:15px;line-height:1.7;margin:0 0 16px;">
      Hey <strong>${safeHandle}</strong> — your Guardian agent just registered from <code style="background:#111;padding:2px 6px;border-radius:3px;font-size:13px;">${safeHost}</code>.
    </p>
    <p style="color:${TEXT};font-size:15px;line-height:1.7;margin:0 0 16px;">
      The agent is now running network scans and will surface incidents to your dashboard automatically.
      Make sure incident alerts are turned on so you never miss a critical event.
    </p>
    <p style="color:${MUTED};font-size:13px;line-height:1.6;margin:0;">
      If you didn't register this agent, rotate your API key immediately under
      <strong>Settings → API Key → Rotate</strong>.
    </p>`;

  return send(
    env,
    to,
    `Guardian agent connected — ${hostname}`,
    baseTemplate("Agent connected.", body, "https://shadowcypher.site/?nav=account", "VIEW DASHBOARD")
  );
}

// ─── Key rotated ─────────────────────────────────────────────────────────────

export async function sendKeyRotatedEmail(
  env: Env,
  to: string,
  handle: string
): Promise<boolean> {
  const safeHandle = escapeHtml(handle);
  const body = `
    <p style="color:${TEXT};font-size:15px;line-height:1.7;margin:0 0 16px;">
      Hey <strong>${safeHandle}</strong> — your ShadowCypher API key was just rotated.
      Your old key is no longer valid.
    </p>
    <p style="color:${TEXT};font-size:15px;line-height:1.7;margin:0 0 16px;">
      Copy your new key from the dashboard and update it in any agent installs or
      integrations that were using the old one.
    </p>
    <p style="color:#ff3b6b;font-size:13px;font-weight:700;margin:0 0 8px;">
      If you didn't rotate your key, your account may be compromised.
    </p>
    <p style="color:${MUTED};font-size:13px;line-height:1.6;margin:0;">
      Contact support immediately if this wasn't you.
    </p>`;

  return send(
    env,
    to,
    "Your API key was rotated",
    baseTemplate("API key rotated.", body, "https://shadowcypher.site/?nav=account", "VIEW DASHBOARD")
  );
}

// ─── Recovery kit (sent to disposal email, address discarded after) ──────────

export async function sendRecoveryKitEmail(
  env: Env,
  disposalEmail: string,
  handle: string,
  codes: string[]
): Promise<boolean> {
  const safeHandle = escapeHtml(handle);
  const codeRows = codes.map((c, i) =>
    `<div style="display:flex;align-items:center;gap:12px;background:#0e0e1e;padding:10px 14px;margin-bottom:6px;">
       <span style="color:#555;font-size:11px;width:20px;">${i + 1}</span>
       <code style="font-family:monospace;letter-spacing:3px;color:#fff;font-size:13px;">${escapeHtml(c)}</code>
     </div>`
  ).join('');

  const body = `
    <p style="color:${TEXT};font-size:15px;line-height:1.7;margin:0 0 16px;">
      Hey <strong>${safeHandle}</strong> — here are your ShadowCypher recovery codes.
    </p>
    <p style="color:${TEXT};font-size:14px;line-height:1.7;margin:0 0 20px;">
      Each code works once. Store them somewhere safe — a password manager, printed paper, anything offline.
      We'll never send these again and we've already forgotten this email address.
    </p>
    ${codeRows}
    <p style="color:#ff3b6b;font-size:13px;font-weight:700;margin:20px 0 4px;">
      Don't share these with anyone.
    </p>
    <p style="color:${MUTED};font-size:12px;line-height:1.6;margin:0;">
      This is a one-time delivery. This email address has been discarded from our systems.
      Your ShadowCypher account has no email on file — your handle and password are your identity.
    </p>`;

  return send(
    env,
    disposalEmail,
    `@${handle} — your ShadowCypher recovery kit`,
    baseTemplate("Recovery kit.", body, "https://shadowcypher.site", "OPEN SHADOWCYPHER")
  );
}
