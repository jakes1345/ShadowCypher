/**
 * Handles nobody may register, and where mail for them goes.
 *
 * Every user's address is handle@shadowcypher.site, so a handle like "security"
 * or "billing" would let its owner read mail meant for the project and send
 * mail that looks official. Sign-up goes straight from the browser to Supabase
 * Auth, so the list is enforced in the database by
 * migrations/0024_reserved_handles.sql. Keep the two lists identical; the test
 * in __tests__/reserved.test.ts fails when they drift.
 */

export const MAIL_DOMAIN = "shadowcypher.site";

/** The operator's account. Admin routes check this address, and role mail lands in its inbox. */
export const ADMIN_EMAIL = `shadow@${MAIL_DOMAIN}`;

export const RESERVED_HANDLES: ReadonlySet<string> = new Set([
  // the operator and generic authority names
  "shadow", "shadowcypher", "admin", "administrator", "root", "sysadmin", "owner",
  "official", "staff", "team", "system", "moderator", "mod",
  // addresses published on the site, in the terms and in SECURITY.md
  "security", "privacy", "legal", "billing", "hello",
  // roles people expect a service to answer
  "support", "help", "abuse", "postmaster", "hostmaster", "webmaster", "info",
  "contact", "sales", "press", "jobs", "dmca", "copyright", "compliance",
  "trust", "safety", "accounts", "account", "payments", "refunds",
  // automated senders
  "noreply", "no_reply", "mailer_daemon", "notifications", "alerts",
  // product and host names
  "guardian", "api", "www", "mail", "status", "docs", "blog", "dev", "ops",
]);

export function isReservedHandle(handle: string): boolean {
  return RESERVED_HANDLES.has(handle.trim().toLowerCase());
}

/** The local part of a shadowcypher.site address, or null for any other address. */
export function handleOf(email: string): string | null {
  const m = email.trim().toLowerCase().match(/^([^@\s]+)@shadowcypher\.site$/);
  return m ? m[1] : null;
}

/**
 * Which mailbox receives mail addressed to `handle`.
 * Role addresses always go to the operator, whoever holds an account by that name.
 */
export function inboxFor(handle: string): string {
  const h = handle.trim().toLowerCase();
  return isReservedHandle(h) ? ADMIN_EMAIL : `${h}@${MAIL_DOMAIN}`;
}

/** True when this account may not send mail: it holds a role name and is not the operator. */
export function isBlockedSender(email: string): boolean {
  const h = handleOf(email);
  return h !== null && isReservedHandle(h) && email.trim().toLowerCase() !== ADMIN_EMAIL;
}
