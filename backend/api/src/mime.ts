/**
 * MIME parsing helpers — extracted for testability.
 * Used by mail.ts for inbound email processing.
 */

export interface MimePart {
  headers: Map<string, string>;
  body: string;
}

export function decodeMimeWords(s: string): string {
  return s.replace(/=\?([^?]+)\?([BQbq])\?([^?]*)\?=/g, (_m, _cs, enc, txt: string) => {
    try {
      if (enc.toUpperCase() === "B") return atob(txt);
      const bytes = txt
        .replace(/_/g, " ")
        .replace(/=([0-9A-Fa-f]{2})/g, (_: string, h: string) => String.fromCharCode(parseInt(h, 16)));
      return bytes;
    } catch {
      return txt;
    }
  });
}

export function decodeQuotedPrintable(s: string): string {
  return s
    .replace(/=\r?\n/g, "")
    .replace(/=([0-9A-Fa-f]{2})/g, (_: string, h: string) => String.fromCharCode(parseInt(h, 16)));
}

export function decodeBase64Body(s: string): string {
  try {
    return atob(s.replace(/\s/g, ""));
  } catch {
    return s;
  }
}

export function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function parseHeaders(raw: string): Map<string, string> {
  const map = new Map<string, string>();
  const lines = raw.replace(/\r\n/g, "\n").split("\n");
  let current = "";
  for (const line of lines) {
    if (line.match(/^\s+/) && current) {
      const [key, ...rest] = current.split(":");
      const val = rest.join(":").trimStart() + " " + line.trim();
      map.set(key.toLowerCase(), val);
    } else if (line.includes(":")) {
      if (current) {
        const [key, ...rest] = current.split(":");
        map.set(key.toLowerCase(), rest.join(":").trimStart());
      }
      current = line;
    }
  }
  if (current) {
    const [key, ...rest] = current.split(":");
    map.set(key.toLowerCase(), rest.join(":").trimStart());
  }
  return map;
}

export function parseMimeParts(raw: string): MimePart[] {
  const headerBodySep = raw.indexOf("\r\n\r\n") !== -1 ? "\r\n\r\n" : "\n\n";
  const [headerSection, ...bodyParts] = raw.split(headerBodySep);
  const body = bodyParts.join(headerBodySep);
  const headers = parseHeaders(headerSection);
  const ct = headers.get("content-type") ?? "";

  const boundaryMatch = ct.match(/boundary="?([^";]+)"?/i);
  if (boundaryMatch) {
    const boundary = boundaryMatch[1];
    const parts: MimePart[] = [];
    const sections = body.split(new RegExp(`--${escapeRegex(boundary)}(?:--)?`));
    for (const section of sections.slice(1)) {
      if (section.trim() === "" || section.trim() === "--") continue;
      const sub = parseMimeParts(section.trimStart());
      parts.push(...sub);
    }
    return parts;
  }

  return [{ headers, body }];
}

export function extractBodies(raw: string): { text: string | null; html: string | null } {
  let text: string | null = null;
  let html: string | null = null;

  const parts = parseMimeParts(raw);
  for (const part of parts) {
    const ct = (part.headers.get("content-type") ?? "text/plain").toLowerCase();
    const enc = (part.headers.get("content-transfer-encoding") ?? "7bit").toLowerCase();

    let decoded = part.body;
    if (enc === "quoted-printable") decoded = decodeQuotedPrintable(decoded);
    else if (enc === "base64") decoded = decodeBase64Body(decoded);

    if (ct.startsWith("text/html") && !html) html = decoded.trim();
    else if (ct.startsWith("text/plain") && !text) text = decoded.trim();
  }

  return { text, html };
}
