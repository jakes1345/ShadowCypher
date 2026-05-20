// ==UserScript==
// @name         ShadowBrowser Cookie Banner Killer
// @namespace    shadowcypher.site
// @version      1.0
// @description  Removes GDPR cookie consent banners by clicking "reject all" or hiding them.
// @match        *://*/*
// @run-at       document-idle
// @grant        none
// ==/UserScript==

(() => {
    'use strict';

    const REJECT_SELECTORS = [
        '[id*="reject"][role="button"]',
        'button[id*="reject"]',
        'button[class*="reject"]',
        'button[data-cy="reject-all"]',
        'button[aria-label*="reject" i]',
        'button[aria-label*="Reject all" i]',
        'button[aria-label*="Decline" i]',
        '#onetrust-reject-all-handler',
        '.cc-deny',
        '.fc-cta-do-not-consent',
    ];

    const BANNER_SELECTORS = [
        '#onetrust-banner-sdk',
        '#cookie-banner',
        '.cookie-banner',
        '.cookie-notice',
        '.cc-banner',
        '.gdpr-banner',
        '[id*="cookie-consent"]',
        '[class*="cookie-consent"]',
        '.fc-consent-root',
    ];

    const tryReject = () => {
        for (const sel of REJECT_SELECTORS) {
            const btn = document.querySelector(sel);
            if (btn && btn.offsetParent !== null) {
                btn.click();
                return true;
            }
        }
        return false;
    };

    const removeBanners = () => {
        BANNER_SELECTORS.forEach((sel) => {
            document.querySelectorAll(sel).forEach((el) => el.remove());
        });
        // Restore scroll if any banner locked it
        document.body.style.overflow = '';
        document.documentElement.style.overflow = '';
    };

    setTimeout(() => {
        if (!tryReject()) {
            removeBanners();
        } else {
            setTimeout(removeBanners, 300);
        }
    }, 800);
})();
