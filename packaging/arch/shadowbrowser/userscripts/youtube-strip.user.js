// ==UserScript==
// @name         ShadowBrowser YouTube Strip
// @namespace    shadowcypher.site
// @version      1.0
// @description  Removes YouTube ads, shorts, ad popup overlay, and end-screen ads.
// @match        *://*.youtube.com/*
// @run-at       document-end
// @grant        none
// ==/UserScript==

(() => {
    'use strict';

    const SELECTORS_TO_KILL = [
        '.ytd-ad-slot-renderer',
        'ytd-display-ad-renderer',
        'ytd-promoted-sparkles-web-renderer',
        'ytd-statement-banner-renderer',
        '.ytp-ad-module',
        '.ytp-ad-overlay-container',
        '.ytd-popup-container tp-yt-paper-dialog',  // anti-adblock dialog
        '#masthead-ad',
        '#player-ads',
        'ytd-rich-section-renderer[is-shorts]',
    ];

    const purge = () => {
        SELECTORS_TO_KILL.forEach((sel) => {
            document.querySelectorAll(sel).forEach((el) => el.remove());
        });

        // If an ad is playing, skip it
        const skipBtn = document.querySelector('.ytp-ad-skip-button, .ytp-ad-skip-button-modern');
        if (skipBtn) skipBtn.click();

        // Fast-forward through pre-roll
        const video = document.querySelector('video.html5-main-video');
        if (video) {
            const adShowing = document.querySelector('.ad-showing, .ytp-ad-player-overlay');
            if (adShowing) {
                video.currentTime = video.duration || 9999;
                video.playbackRate = 16;
                video.muted = true;
            } else if (video.playbackRate === 16) {
                video.playbackRate = 1;
                video.muted = false;
            }
        }
    };

    new MutationObserver(purge).observe(document.documentElement, {
        childList: true,
        subtree: true,
    });
    setInterval(purge, 500);
})();
