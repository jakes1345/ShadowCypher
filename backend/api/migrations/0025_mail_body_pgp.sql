-- Mail bodies sealed to the mailbox owner's OpenPGP identity key (mail_crypto.ts).
-- Apply to Supabase before deploying the Worker that writes body_pgp.
--
-- For an account with a row in user_keys, new mail is stored with body_text and
-- body_html empty and the body in body_pgp: an armored OpenPGP message holding
-- {"v":1,"text":...,"html":...}, readable only with the owner's private key.
-- Existing rows are left as they are.

ALTER TABLE mail_messages
  ADD COLUMN IF NOT EXISTS body_pgp text;
