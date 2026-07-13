-- Shadow Mail: inbound + outbound messages per user
-- Inbound: stored by the Cloudflare Email Worker on arrival
-- Outbound: stored by POST /v1/mail/send via Resend

CREATE TABLE IF NOT EXISTS mail_messages (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  message_id    text,                          -- MIME Message-ID header (dedup)
  from_addr     text        NOT NULL,
  to_addr       text        NOT NULL,
  subject       text        NOT NULL DEFAULT '',
  body_text     text,
  body_html     text,
  direction     text        NOT NULL DEFAULT 'inbound' CHECK (direction IN ('inbound','outbound')),
  is_read       boolean     NOT NULL DEFAULT false,
  received_at   timestamptz NOT NULL DEFAULT now(),
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS mail_user_time_idx    ON mail_messages (user_id, received_at DESC);
CREATE INDEX IF NOT EXISTS mail_message_id_idx   ON mail_messages (message_id) WHERE message_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS mail_unread_idx       ON mail_messages (user_id, is_read) WHERE is_read = false;

ALTER TABLE mail_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see own mail" ON mail_messages
  FOR ALL USING (auth.uid() = user_id);
