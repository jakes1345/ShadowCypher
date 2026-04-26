# 🛡️ Sovereign Cloud: The Zero-Budget Infrastructure

ShadowCypher is built for sovereignty. You shouldn't rely on expensive, centralized clouds. Here is how we build our own infrastructure for $0/month.

## 1. The "Cheat Code": Oracle Cloud Free Tier
Oracle Cloud offers the most generous free tier in the world. This is our primary deployment target.
*   **CPU:** 4 OCPUs (Ampere ARM)
*   **RAM:** 24 GB RAM
*   **Storage:** 200 GB Block Storage
*   **Bandwidth:** 10 TB Egress per month

### How to Get It:
1.  Go to [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/).
2.  Sign up (requires a card for identity check, but $0 charge).
3.  **Critical:** Choose a region with capacity (e.g., US East, Frankfurt, or Tokyo).
4.  Provision an **Ampere A1 Compute** instance with the `Ubuntu 22.04` image.

---

## 2. The Engine: Coolify (Self-Hosted PaaS)
Instead of paying for Heroku or Vercel, we install **Coolify** on our server. It provides a beautiful UI to manage databases, websites, and APIs.

### One-Command Setup (ShadowNode):
Run the setup script included in this repo:
```bash
chmod +x ./deploy/setup_shadownode.sh
./deploy/setup_shadownode.sh
```
Once installed, visit `http://your-ip:3000` to start deploying ShadowCypher services.

---

## 3. The Tunnel: Cloudflare (Zero-Cost DNS & SSL)
To get your ShadowNode online without a static IP or port forwarding:
1.  Install `cloudflared` on your server.
2.  Create a tunnel to your local Coolify port.
3.  Point `shadowcypher.site` to the tunnel.
4.  **Result:** Free SSL, DDoS protection, and a professional domain for $0.

---

## 🏁 Deployment Strategy
1.  **Production:** Oracle Cloud VM (24GB RAM) running Coolify.
2.  **Edge:** Your home PC or a Raspberry Pi running as a secondary ShadowNode for redundancy.
3.  **Database:** Supabase (Free Tier) for users, or a self-hosted PostgreSQL inside Coolify.

**Total Monthly Cost: $0.00**
