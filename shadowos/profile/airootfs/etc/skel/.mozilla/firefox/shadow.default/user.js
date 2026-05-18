// ShadowOS Firefox hardening — privacy / anti-fingerprint / no telemetry
// Adapted from arkenfox + ShadowCypher security profile.

// === Telemetry off ===
user_pref("toolkit.telemetry.enabled", false);
user_pref("toolkit.telemetry.unified", false);
user_pref("toolkit.telemetry.archive.enabled", false);
user_pref("toolkit.telemetry.coverage.opt-out", true);
user_pref("toolkit.coverage.opt-out", true);
user_pref("datareporting.healthreport.uploadEnabled", false);
user_pref("datareporting.policy.dataSubmissionEnabled", false);
user_pref("app.normandy.enabled", false);
user_pref("app.shield.optoutstudies.enabled", false);

// === Pocket / sponsored content off ===
user_pref("extensions.pocket.enabled", false);
user_pref("browser.newtabpage.activity-stream.feeds.section.topstories", false);
user_pref("browser.newtabpage.activity-stream.showSponsored", false);
user_pref("browser.newtabpage.activity-stream.showSponsoredTopSites", false);

// === Search ===
user_pref("browser.search.suggest.enabled", false);
user_pref("browser.urlbar.suggest.searches", false);
user_pref("browser.urlbar.suggest.history", false);
user_pref("browser.urlbar.speculativeConnect.enabled", false);

// === WebRTC leak prevention ===
user_pref("media.peerconnection.enabled", false);
user_pref("media.peerconnection.ice.default_address_only", true);
user_pref("media.peerconnection.ice.no_host", true);

// === Geolocation ===
user_pref("geo.enabled", false);
user_pref("geo.provider.use_geoclue", false);
user_pref("permissions.default.geo", 2);

// === DRM off ===
user_pref("media.eme.enabled", false);
user_pref("media.gmp-widevinecdm.enabled", false);

// === Disk cache + history ===
user_pref("privacy.clearOnShutdown.cache", true);
user_pref("privacy.clearOnShutdown.cookies", false);
user_pref("privacy.clearOnShutdown.downloads", true);
user_pref("privacy.clearOnShutdown.formdata", true);
user_pref("privacy.clearOnShutdown.history", true);
user_pref("privacy.clearOnShutdown.offlineApps", true);
user_pref("privacy.clearOnShutdown.sessions", true);

// === Tracking protection (strict) ===
user_pref("browser.contentblocking.category", "strict");
user_pref("privacy.trackingprotection.enabled", true);
user_pref("privacy.trackingprotection.socialtracking.enabled", true);
user_pref("network.cookie.cookieBehavior", 5);

// === Fingerprinting resistance ===
user_pref("privacy.resistFingerprinting", true);
user_pref("privacy.resistFingerprinting.letterboxing", true);
user_pref("webgl.disabled", true);
user_pref("media.navigator.enabled", false);

// === DNS over HTTPS to local dnscrypt-proxy ===
user_pref("network.trr.mode", 3);
user_pref("network.trr.uri", "https://127.0.0.1:8443/dns-query");

// === HTTPS-only mode ===
user_pref("dom.security.https_only_mode", true);
user_pref("dom.security.https_only_mode_ever_enabled", true);

// === Network prediction off ===
user_pref("network.prefetch-next", false);
user_pref("network.dns.disablePrefetch", true);
user_pref("network.predictor.enabled", false);
user_pref("network.http.speculative-parallel-limit", 0);

// === Disable safe browsing remote lookups (keeps local list) ===
user_pref("browser.safebrowsing.downloads.remote.enabled", false);

// === Misc ===
user_pref("beacon.enabled", false);
user_pref("browser.send_pings", false);
user_pref("browser.urlbar.trimURLs", false);
user_pref("dom.battery.enabled", false);
user_pref("network.http.referer.XOriginPolicy", 2);
user_pref("network.http.referer.XOriginTrimmingPolicy", 2);
