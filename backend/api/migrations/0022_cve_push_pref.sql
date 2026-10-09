-- CVE push notification per-event toggle
ALTER TABLE notification_prefs
  ADD COLUMN IF NOT EXISTS cve_push_enabled boolean NOT NULL DEFAULT true;
