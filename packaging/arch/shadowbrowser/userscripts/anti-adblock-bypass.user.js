// ==UserScript==
// @name         ShadowBrowser Anti-Adblock Bypass
// @namespace    shadowcypher.site
// @version      1.0
// @description  Defangs common anti-adblock detection scripts.
// @match        *://*/*
// @run-at       document-start
// @grant        none
// ==/UserScript==

(() => {
    'use strict';

    // 1. Spoof window.canRunAds (used by BlockAdBlock, FuckAdBlock, etc.)
    Object.defineProperty(window, 'canRunAds', {
        value: true,
        writable: false,
        configurable: false,
    });

    // 2. Neutralize the BlockAdBlock detection function
    const noop = () => {};
    const noOpReturnsFalse = () => false;
    ['blockAdBlock', 'fuckAdBlock', 'BlockAdBlock', 'FuckAdBlock',
     'sniffAdBlock', 'adBlockerDetected'].forEach((name) => {
        Object.defineProperty(window, name, {
            get: () => ({
                onDetected: noop,
                onNotDetected: (cb) => cb && cb(),
                check: noop,
                emitEvent: noop,
                setOption: noop,
                clearEvent: noop,
                isFunction: noOpReturnsFalse,
            }),
            set: noop,
        });
    });

    // 3. Spoof bait div as visible (some scripts check element heights)
    const spoofBait = () => {
        document.querySelectorAll('[id*="ad"], [class*="adsbox"], [class*="ad-banner"]')
            .forEach((el) => {
                if (el.offsetHeight === 0) {
                    Object.defineProperty(el, 'offsetHeight', { value: 100 });
                    Object.defineProperty(el, 'clientHeight', { value: 100 });
                }
            });
    };
    new MutationObserver(spoofBait).observe(document, {
        childList: true,
        subtree: true,
    });

    // 4. Kill common detection-overlay popups by selector
    const overlaySelectors = [
        '.adblock-popup', '.adblock-overlay', '#adblock-detected',
        '[data-adblock-key]', '.ab-message-container',
        '.detection-message', '#ad-block-detected',
    ];
    const killOverlays = () => {
        overlaySelectors.forEach((sel) => {
            document.querySelectorAll(sel).forEach((el) => el.remove());
        });
    };
    new MutationObserver(killOverlays).observe(document, {
        childList: true, subtree: true,
    });

    // 5. Re-enable scroll if a detection script disabled it
    Object.defineProperty(document.body || document.documentElement, 'style', {
        get: function () { return this._style || {}; },
        set: function (v) { this._style = v; },
    });
})();
