// Marketing site (shadowcypher.site/). The app itself lives at /app/.
(() => {
    const SITE_PAGES = ['home', 'arsenal', 'ghost', 'download', 'shadowos', 'pricing'];

    // Old links (Stripe returns, emails, push notifications) point at /?nav=… — send them to the app.
    const params = new URLSearchParams(location.search);
    const nav = params.get('nav');
    const appParams = ['checkout', 'account', 'session_id', 'incident', 'source'];
    if ((nav && !SITE_PAGES.includes(nav)) || appParams.some(p => params.has(p))) {
        location.replace('/app/' + location.search + location.hash);
        return;
    }

    const shutter = document.getElementById('pageShutter');
    const indicator = document.getElementById('navIndicator');
    function updateIndicator(el) {
        if (!el) return;
        indicator.style.width = el.offsetWidth + 'px';
        indicator.style.left = el.offsetLeft + 'px';
    }
    async function navTo(pageId) {
        const target = document.getElementById('page-' + pageId);
        if (!target || target.classList.contains('active')) return;
        shutter.classList.add('active');
        await new Promise(r => setTimeout(r, 500));
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
        target.classList.add('active');
        const navEl = document.getElementById('nav-' + pageId);
        if (navEl) { navEl.classList.add('active'); updateIndicator(navEl); }
        window.scrollTo({ top: 0 });
        await new Promise(r => setTimeout(r, 100));
        shutter.classList.remove('active');
    }

    document.addEventListener('click', e => {
        const navEl = e.target.closest('[data-nav]');
        if (navEl) { e.preventDefault(); navTo(navEl.dataset.nav); return; }
        const linkEl = e.target.closest('[data-href]');
        if (linkEl) { e.preventDefault(); location.href = linkEl.dataset.href; }
    });

    if (nav) {
        history.replaceState(null, '', location.pathname);
        navTo(nav);
    }

        // THREE.JS Background — decorative only; without WebGL (or if the CDN
        // script is blocked) the rest of this script must still run.
        try {
        const scene = new THREE.Scene(), camera = new THREE.Camera();
        const renderer = new THREE.WebGLRenderer({canvas:document.getElementById('void-canvas'),alpha:true});
        const geo = new THREE.PlaneGeometry(2,2);
        const mat = new THREE.ShaderMaterial({
            uniforms:{time:{value:0},resolution:{value:new THREE.Vector2(window.innerWidth,window.innerHeight)}},
            vertexShader:`void main(){gl_Position=vec4(position,1.0);}`,
            fragmentShader:`
                precision highp float;
                uniform float time;
                uniform vec2 resolution;

                // Value noise + FBM for organic enterprise-grade ambient gradients
                float hash(vec2 p){p=fract(p*vec2(127.1,311.7));p+=dot(p,p+19.19);return fract(p.x*p.y);}
                float vnoise(vec2 p){
                    vec2 i=floor(p), f=fract(p);
                    float a=hash(i), b=hash(i+vec2(1,0)), c=hash(i+vec2(0,1)), d=hash(i+vec2(1,1));
                    vec2 u=f*f*(3.0-2.0*f);
                    return mix(mix(a,b,u.x), mix(c,d,u.x), u.y);
                }
                float fbm(vec2 p){
                    float v=0.0, a=0.5;
                    for(int k=0;k<5;k++){ v+=a*vnoise(p); p*=2.02; a*=0.5; }
                    return v;
                }

                void main(){
                    vec2 uv=gl_FragCoord.xy/resolution.xy;
                    float aspect=resolution.x/resolution.y;
                    vec2 p=uv*vec2(aspect,1.0);
                    float t=time*0.04;

                    // Deep navy base
                    vec3 col=vec3(0.012,0.012,0.028);

                    // L1: slow drifting purple nebula via 2-domain FBM (no orbits)
                    vec2 q=vec2(fbm(p*1.3+vec2(t,-t*0.6)), fbm(p*1.3+vec2(-t*0.7,t*0.5)));
                    float neb=fbm(p*2.0+q*1.8+vec2(t*0.3,0.0));
                    neb=smoothstep(0.35,0.95,neb);
                    col+=mix(vec3(0.0), vec3(0.42,0.18,0.78), neb)*0.55;

                    // L2: cool blue accent pocket, opposite-phase drift
                    float blue=fbm(p*1.6-q*1.2+vec2(-t*0.5,t*0.4));
                    blue=smoothstep(0.55,0.85,blue);
                    col+=vec3(0.18,0.22,0.55)*blue*0.22;

                    // L3: soft horizon glow band — diagonal, slow vertical breathe
                    float band=exp(-pow((uv.y-0.55-0.04*sin(time*0.05))*4.5,2.0));
                    col+=vec3(0.32,0.16,0.62)*band*0.18;

                    // L4: faint orthogonal grid that softly breathes (radar-feel, no harsh lines)
                    vec2 g=fract(uv*vec2(38.0,22.0))-0.5;
                    float gridLine=smoothstep(0.49,0.50,max(abs(g.x),abs(g.y)));
                    float breathe=0.5+0.5*sin(time*0.15);
                    col+=vec3(0.18,0.10,0.32)*(1.0-gridLine)*0.05*(0.6+0.4*breathe);

                    // L5: rare bokeh specks (lens dust feel) — sparse high-threshold hash
                    vec2 cellId=floor(p*60.0);
                    float spark=hash(cellId);
                    if(spark>0.992){
                        vec2 cf=fract(p*60.0)-0.5;
                        float pulse=0.5+0.5*sin(time*0.4+spark*30.0);
                        col+=vec3(0.55,0.35,0.95)*exp(-dot(cf,cf)*40.0)*0.35*pulse;
                    }

                    // Vignette to keep focus on content
                    vec2 vc=uv-0.5;
                    col*=1.0-dot(vc,vc)*0.55;

                    gl_FragColor=vec4(col, 0.42);
                }
            `
        });
        scene.add(new THREE.Mesh(geo,mat));
        function animate(t){mat.uniforms.time.value=t*0.001;renderer.render(scene,camera);requestAnimationFrame(animate);}
        animate(0);
        window.addEventListener('resize',()=>{mat.uniforms.resolution.value.set(window.innerWidth,window.innerHeight);renderer.setSize(window.innerWidth,window.innerHeight);});
        renderer.setSize(window.innerWidth,window.innerHeight);
        } catch (e) { console.warn('Background animation disabled:', e.message); }

    window.addEventListener('load', () => {
        updateIndicator(document.querySelector('.nav-tab.active'));
        const hex = document.getElementById('hex-dump');
        const log = document.getElementById('swarm-log');
        const entries = ['[GHOST] PING: {ip} → {ms}ms', '[RELAY] SIGNAL_LOCK: {id}', '[PULSE] VARIANCE: {var}', '[SENTINEL] PEER_LINKED: {node}', '[GUARD] DEVICE_OK: {dev}'];
        let hexTimer = null, swarmTimer = null;
        function start() {
            if (!hexTimer) hexTimer = setInterval(() => {
                if (!hex) return;
                hex.textContent = '';
                for (let row = 0; row < 20; row++) {
                    let t = '';
                    for (let i = 0; i < 20; i++) t += Math.floor(Math.random() * 16).toString(16).toUpperCase() + ' ';
                    hex.append(t, document.createElement('br'));
                }
            }, 800);
            if (!swarmTimer) swarmTimer = setInterval(() => {
                if (!log) return;
                const e = entries[Math.floor(Math.random() * entries.length)]
                    .replace('{ip}', '192.168.1.' + Math.floor(Math.random() * 255))
                    .replace('{ms}', Math.floor(Math.random() * 50))
                    .replace('{id}', 'NODE_' + Math.floor(Math.random() * 1000))
                    .replace('{var}', Math.random().toFixed(2))
                    .replace('{node}', 'SHADOW_' + Math.floor(Math.random() * 99))
                    .replace('{dev}', 'iPhone_' + Math.floor(Math.random() * 9));
                const d = document.createElement('div');
                d.style.opacity = '0';
                d.style.transition = 'opacity 0.5s';
                d.textContent = e;
                log.prepend(d);
                setTimeout(() => { d.style.opacity = '0.8'; }, 10);
                if (log.children.length > 5) log.removeChild(log.lastChild);
            }, 2500);
        }
        function stop() {
            clearInterval(hexTimer); hexTimer = null;
            clearInterval(swarmTimer); swarmTimer = null;
        }
        start();
        document.addEventListener('visibilitychange', () => (document.hidden ? stop() : start()));
        window.addEventListener('resize', () => updateIndicator(document.querySelector('.nav-tab.active')));
    });
})();
