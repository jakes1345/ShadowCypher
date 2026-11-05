// Marketing site (shadowcypher.site/). The app itself lives at /app/.
(() => {
    // Old links point at /?nav=… — site pages scroll to their section, the rest go to the app.
    const SECTIONS = { home: '', arsenal: 'platform', ghost: 'privacy', shadowos: 'shadowos', download: 'download', pricing: 'pricing' };
    const params = new URLSearchParams(location.search);
    const nav = params.get('nav');
    const appParams = ['checkout', 'account', 'session_id', 'incident', 'source'];
    if ((nav && !(nav in SECTIONS)) || appParams.some(p => params.has(p))) {
        location.replace('/app/' + location.search + location.hash);
        return;
    }
    if (nav) {
        history.replaceState(null, '', location.pathname + (SECTIONS[nav] ? '#' + SECTIONS[nav] : ''));
        if (SECTIONS[nav]) document.getElementById(SECTIONS[nav])?.scrollIntoView();
    }

    const hex = document.getElementById('hex-dump');
    let timer = null;
    function draw() {
        hex.textContent = '';
        for (let row = 0; row < 20; row++) {
            let t = '';
            for (let i = 0; i < 20; i++) t += Math.floor(Math.random() * 16).toString(16).toUpperCase() + ' ';
            hex.append(t, document.createElement('br'));
        }
    }
    function start() { if (hex && !timer && !matchMedia('(prefers-reduced-motion: reduce)').matches) timer = setInterval(draw, 800); }
    function stop() { clearInterval(timer); timer = null; }
    start();
    document.addEventListener('visibilitychange', () => (document.hidden ? stop() : start()));
})();
