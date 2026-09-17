# Deploy IngreSure API on OCI — full step-by-step (Vercel frontend, no paid domain)

This guide assumes:

- Your **website** is on Vercel at something like **`https://your-app.vercel.app`** (you do **not** own a separate domain).
- Your **API** will run on an **OCI VM** you already have.

---

## Important: two different URLs

| What | Example | Where it lives |
|------|---------|----------------|
| **Frontend (UI)** | `https://your-app.vercel.app` | Vercel — you already have this. |
| **Backend (API)** | Must be a URL Vercel can call | Your OCI server — **Vercel does not give you a second `*.vercel.app` for OCI.** |

So you need **some way** to reach the API over the internet:

1. **Recommended (free):** A **free hostname** (this guide uses **Dynu**) pointing at your OCI public IP + **HTTPS** (Caddy + Let’s Encrypt).  
2. **Alternative:** **Cloudflare Tunnel** (HTTPS URL without opening port 443 on OCI).  
3. **Demo only:** **`http://YOUR_PUBLIC_IP:8000`** — works with Vercel **server** routes in many setups, but **no encryption** to the API (not for real production).

Below we use **Path A: Dynu + Caddy** as the main line-by-line path. Paths B and C are shorter add-ons at the end.

---

## Which free hostname is “best”? (security & performance)

**First:** Your **encryption** (HTTPS) and **certificate trust** come from **Let’s Encrypt + Caddy** on your VM (Path A), or from **Cloudflare** (Path B)—not from the DNS brand. The free name is mainly **DNS pointing** at your server.

| Option | Best for | Security notes | Performance |
|--------|----------|----------------|-------------|
| **Dynu** + Caddy + Let’s Encrypt | This guide’s path; free dynamic DNS (e.g. `*.dynu.net`); dashboard + API IP updates | TLS to **your** OCI box; protect **Dynu** account (**strong password**, 2FA if offered). If someone hijacks DNS, they could point the name elsewhere—same as any DNS provider. | **Fine** for an API: DNS lookup is tiny vs request time; your bottleneck is the VM + app, not Dynu. |
| **DuckDNS** + Caddy | Same idea as Dynu; alternative if you prefer it | Same pattern as Dynu | Same as Dynu |
| **Cloudflare Tunnel** (`cloudflared`) | **Strongest “free” setup** if you want **no public 443** on OCI, **hidden origin IP**, and HTTPS terminated at Cloudflare’s edge | Traffic: client ↔ Cloudflare (TLS) ↔ encrypted tunnel ↔ your app. Reduces exposure of OCI to raw internet scans. Configure access in Cloudflare dashboard. | Often **very good** globally (Cloudflare’s network); adds one hop—usually negligible for API latency vs your region’s distance to OCI anyway. |
| **nip.io / sslip.io** (IP baked into hostname) | Quick tests only | Let’s Encrypt and policies change; some names look “weird” to users/blocklists. | OK for demos; not ideal as a long-term production URL. |
| **Raw public IP + HTTP** | Temporary dev only | **No TLS** to the API—avoid for anything real. | Fastest path, worst security. |

**Practical recommendation**

- **This guide:** **Dynu** + **Caddy** (Path A)—good balance of simplicity, real HTTPS, and acceptable security if you **lock your Dynu account** and keep **NSG** tight (only 22 from you, 80/443 for the world as required for LE + HTTPS).
- **Best security among free options (no paid domain):** **Cloudflare Tunnel**—especially if you don’t want to expose inbound **443** on OCI at all; use Path B and Cloudflare’s current tunnel docs.

**Performance reality:** For IngreSure, almost all latency is **your OCI shape**, **Python**, optional **LLM**, and **distance**—not whether the hostname is Dynu vs another free DNS brand.

---

## Part A — One-time setup (browser + OCI console)

### Step A1 — Get your OCI instance **public IP**

1. Open **Oracle Cloud Console** → **Compute** → **Instances**.
2. Click your instance.
3. Under **Primary VNIC** / **Public IP address**, copy the **IPv4** (e.g. `129.146.x.x`).

You will use this IP in NSG rules and in **Dynu**.

### Step A2 — Create a **free hostname** with Dynu (no paid domain)

1. Open **https://www.dynu.com** and create a free account.
2. Sign in → **Control Panel** → **DDNS Services** (or **My Services** → Dynamic DNS) → **Add** a dynamic DNS hostname.
3. Choose a hostname on a **free Dynu domain** (e.g. **`ingresure-api.dynu.net`** — use the suffix Dynu offers you, often `dynu.net`).
4. Set the **IPv4 address** to your OCI **public IP** from A1 → save.
5. Wait **1–15 minutes** for DNS to propagate.

You will use **`https://ingresure-api.dynu.net`** (your real hostname) everywhere below instead of `api.yourdomain.com`.

**Own domain (e.g. `ingresure-api.gleeze.com`):** At your DNS host, create an **A** record: name = the subdomain (e.g. `ingresure-api`), value = **the same public IPv4** as in Step A1. TTL 300s is fine. No Dynu account needed. Use that **exact** hostname in the Caddyfile and in Vercel **`BACKEND_URL`**.

**Dynu form fields (what to use for IngreSure + OCI)**

| Field | What to do |
|-------|------------|
| **IPv4 Address** | Paste your OCI instance **public IPv4** (from Step A1). **Required** for this setup. |
| **IPv6 Address** | **Leave empty** unless you deliberately use IPv6 on OCI and opened IPv6 in NSG. Most people skip. |
| **Group** | **Optional** — only for organizing many hostnames in Dynu; can leave blank/default. |
| **TTL (seconds)** | **120** (or default) is fine. Lower = DNS updates propagate a bit faster; slightly more DNS queries. |
| **Wildcard IPv4 Alias** | **Off / unchecked** unless you need `*.yourname.dynu.net`. You only need one hostname like `ingresure-api.dynu.net`. |
| **Wildcard IPv6 Alias** | **Off** if you are not using IPv6. |
| **Enable IPv6 Address** | **Off** unless you configured **IPv6** on OCI and want an **AAAA** record. |
| **Email Notification** | **Your choice** — On = Dynu may email you for some events; Off = less inbox noise. Not required for the app to work. |

If the UI shows **two similar blocks** (e.g. duplicate IPv4/IPv6 sections), it is often **one row for IPv4 record** and **one for IPv6** — fill **IPv4** only for our guide; leave IPv6 blank/disabled unless you know you need it.

**Dynu docs:** [Dynamic DNS](https://www.dynu.com/DynamicDNS) · [IP update API](https://www.dynu.com/DynamicDNS/IPUpdateAPI) (useful when your OCI public IP changes).

### Step A3 — Open firewall ports on OCI (Security List or NSG)

OCI blocks traffic by default until you add **ingress** rules. Your VM usually uses either a **Security List** on the subnet **or** a **Network Security Group (NSG)** on the VNIC (sometimes both — a packet must be allowed by **all** that apply).

#### A3.0 — Find **your laptop’s public IP** (for SSH)

You will allow SSH only from this address (safer than opening SSH to the whole world).

1. On your laptop, open a browser and search **“what is my ip”**, or visit `https://ifconfig.me` / `https://api.ipify.org`.
2. Copy the IPv4 address (e.g. `203.0.113.50`).  
3. In OCI rules you will use **`203.0.113.50/32`** (the `/32` means “only this one IP”).

**Note:** If your home IP changes (ISP DHCP), SSH may stop working until you update the rule or use a bastion/VPN.

#### A3.1 — See whether your instance uses a Security List or NSG

1. Oracle Cloud **Console** → **Compute** → **Instances**.
2. Click your **instance name**.
3. Scroll to **Resources** → click **Attached VNICs** (or open the primary VNIC).
4. Note:
   - **Subnet** name (e.g. `subnet-xxx`).
   - **Network security groups** — if one or more are listed, you will add rules there **and/or** on the subnet’s security list (see below).

**Quick rule:** If an **NSG** is attached, add the rules to that **NSG**. If the instance only has a subnet (no NSG), use the subnet’s **Security List**. If **both** exist, add the **same** ingress rules to the **NSG** (often the stricter one); if something still fails, also check the **Security List** on that subnet.

#### A3.2 — Add rules via **Security List** (common default)

1. **Networking** → **Virtual cloud networks**.
2. Click your **VCN** (the one your instance uses).
3. Under **Resources** (left), click **Security Lists**.
4. Click the security list attached to your instance’s **subnet** (often named like **Default Security List for …**).
5. Click **Add Ingress Rules** and add **three separate rules** (or one row per rule, depending on UI):

| Source | IP protocol | Source port range | Destination port range | Description |
|--------|-------------|-------------------|------------------------|-------------|
| **`YOUR_IP/32`** | TCP | All | **22** | SSH from your laptop only |
| **`0.0.0.0/0`** | TCP | All | **80** | HTTP (Let’s Encrypt) |
| **`0.0.0.0/0`** | TCP | All | **443** | HTTPS (Caddy / API) |

- **Source CIDR** = first column.  
- **Destination port range** = single port: `22`, `80`, or `443`.

6. Click **Add Ingress Rules** / **Save**.

#### A3.3 — Add rules via **Network Security Group (NSG)**

1. **Networking** → **Virtual cloud networks** → click your **VCN**.
2. Under **Resources** → **Network Security Groups**.
3. Click the **NSG** that is attached to your instance VNIC (from A3.1).
4. **Add Rule** → **Ingress rule** — same three rules as the table in **A3.2** (SSH from `YOUR_IP/32`, TCP 80 and 443 from `0.0.0.0/0`).

#### A3.4 — Egress (outbound)

Most default Security Lists already allow **all egress** to `0.0.0.0/0`. If `apt`, `git clone`, or `docker pull` fails, open that Security List → **Egress Rules** and ensure there is a rule allowing outbound traffic (often **All protocols**, destination `0.0.0.0/0`).

#### A3.5 — What **not** to do for this guide

| Do **not** (for this Caddy setup) | Why |
|-----------------------------------|-----|
| Open **TCP 8000** to `0.0.0.0/0` | The API listens on **8000 only inside the VM**; Caddy on **443** faces the internet. Opening 8000 exposes the app without going through Caddy. |
| Open **SSH 22** to `0.0.0.0/0` | Anyone on the internet can try to log in. Use **`YOUR_IP/32`** only. |

#### A3.6 — Sanity check

- Instance has a **public IPv4** (you used it in Dynu).
- VCN route table for the subnet sends **0.0.0.0/0** to an **Internet Gateway** (default for “public subnet” setups). If there is no route to the internet, Let’s Encrypt and `apt` will fail.

After saving rules, wait **~30–60 seconds** and test from your laptop: `ssh ubuntu@YOUR_INSTANCE_PUBLIC_IP` (or `opc@…` on Oracle Linux).

### Step A4 — Note your **exact Vercel app URL**

1. Open **vercel.com** → your project.
2. **Settings** → **Domains** (or open the production URL from the dashboard).
3. Copy the **https** URL, e.g. `https://ingresure.vercel.app` (no trailing slash).

You need this exact string for **`CORS_ORIGINS`** on the server.

---

## Part B — On the OCI VM (SSH + Docker + app)

### Step B1 — SSH into the VM

On **your laptop**:

```bash
ssh ubuntu@YOUR_PUBLIC_IP
```

If login fails, try user **`opc`** (Oracle Linux):

```bash
ssh opc@YOUR_PUBLIC_IP
```

### Step B2 — Install Docker + Compose (Ubuntu)

Run on the VM:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg git
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
```

**Log out and SSH in again** (so `docker` works without `sudo`), or use `sudo docker` for the next commands.

**Oracle Linux:** follow [Docker Engine install](https://docs.docker.com/engine/install/) for your distro instead of the block above.

### Step B3 — Clone the repo

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/IngreSure.git
cd IngreSure
```

Use your real Git URL. If the repo is private, use SSH clone or a personal access token.

### Step B4 — Create `backend/.env`

```bash
cp backend/.env.example backend/.env
nano backend/.env
```

**Set at least:**

```bash
# USDA (required for many ingredient lookups)
USDA_FDC_API_KEY=paste_your_key_here

# EXACTLY your Vercel site (https, no trailing slash). If you have preview URLs too, comma-separate:
CORS_ORIGINS=https://your-app.vercel.app

# Safer error messages in production
ENVIRONMENT=production
```

Replace **`https://your-app.vercel.app`** with the URL from **Step A4**.

**Optional Supabase** (if you use it): uncomment and set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.

**LLM:** On a small VM, skip Ollama. The API still works; some replies use **templates** instead of the LLM.

**Redis/Celery:** On **Always Free Micro (1 GB)**, **do not** add `REDIS_URL` — skip the `cache` profile.

Save: in `nano`, `Ctrl+O`, Enter, `Ctrl+X`.

### Step B5 — Start the backend container

From **`~/IngreSure`** (repo root):

```bash
docker compose up -d --build backend
```

Wait ~1–3 minutes on first build. Check:

```bash
docker compose ps
curl -sS http://127.0.0.1:8000/health
```

You should see JSON/`ok` from **inside the VM only**.

If it fails:

```bash
docker compose logs backend
```

---

## Part C — HTTPS with Caddy (so Vercel can use `https://…`)

### Step C1 — Install Caddy (on the VM, not in Docker)

```bash
sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt-get update
sudo apt-get install -y caddy
```

### Step C2 — Caddyfile

Replace **`ingresure-api.dynu.net`** with **your** Dynu hostname (exactly as shown in the Dynu control panel):

```bash
sudo nano /etc/caddy/Caddyfile
```

Put **only** this (replace the hostname with yours — Dynu or your own domain, **exactly** as in DNS):

```caddy
{
    default_bind 0.0.0.0
}

ingresure-api.dynu.net {
    reverse_proxy 127.0.0.1:8000
}
```

**Why `default_bind 0.0.0.0`:** Caddy may otherwise listen only on IPv6 (`[::]:443` / `[::]:80`). IPv4 clients to your public IP then get **connection refused**. The **global** block applies to **every** listener (HTTPS, HTTP→HTTPS redirect, and Let’s Encrypt on **80**); a site-level `bind` alone can still leave **80/443** off IPv4 in some setups.

After edits: `sudo caddy fmt --overwrite /etc/caddy/Caddyfile`, `sudo caddy validate --config /etc/caddy/Caddyfile`, then **`sudo systemctl restart caddy`** (use **restart** if `ss` still shows no `0.0.0.0:443` after **reload**).

**Sanity check on the VM:** `sudo ss -tlnp4 | grep -E ':80|:443'` should list **Caddy** on **`0.0.0.0:80`** and **`0.0.0.0:443`**. If you only see **`[::]:80`** / **`[::]:443`** (check with `sudo ss -tlnp | grep -E ':80|:443'`), IPv4 is still wrong. If **nothing** on 80/443: `sudo systemctl status caddy` and `sudo journalctl -u caddy -b --no-pager | tail -60` — the service may have exited (permissions, bad path, TLS/DNS errors).

A copy-paste template also lives in the repo: [`deploy/Caddyfile.example`](deploy/Caddyfile.example).

Save and exit.

### Step C3 — Start Caddy

```bash
sudo systemctl enable caddy
sudo systemctl restart caddy
sudo systemctl status caddy
```

First time, Caddy contacts **Let’s Encrypt**. That needs:

- DNS **your Dynu hostname** (e.g. `ingresure-api.dynu.net`) → your OCI public IP (Dynu step A2)
- Ports **80** and **443** open (A3)

Test from **your laptop**:

```bash
curl -sS https://ingresure-api.dynu.net/health
```

Use your real Dynu host. If you get certificate errors, wait a few minutes and check DNS with `ping ingresure-api.dynu.net` (should show your OCI IP).

---

## Part D — Vercel (connect frontend to API)

### Step D1 — Environment variable

1. **vercel.com** → your project → **Settings** → **Environment Variables**.
2. Add or edit **`BACKEND_URL`**:
   - Value: **`https://ingresure-api.dynu.net`** (your Dynu URL, **no** trailing slash).
3. Apply to **Production** (and **Preview** if you want preview deploys to hit the same API).

### Step D2 — Redeploy

1. **Deployments** → open the latest production deployment → **⋯** → **Redeploy** (use existing build or rebuild).

---

## Part E — Verify everything

| # | What to do | Pass criteria |
|---|------------|----------------|
| 1 | `curl https://YOUR.dynu.net/health` from laptop | HTTP 200, healthy body |
| 2 | Open **`https://your-app.vercel.app`** in browser | Site loads |
| 3 | Send a chat message (ingredient question) | Reply returns, no red errors |
| 4 | Browser **DevTools** → **Network** | No **CORS** errors on API calls |

If CORS fails: **`CORS_ORIGINS`** on the server must **exactly** match the browser origin (including `https` and no trailing slash). After editing `.env`:

```bash
cd ~/IngreSure
docker compose restart backend
```

---

## Part F — When your OCI public IP changes (free tier / DHCP)

If Oracle assigns a **new** public IP:

1. **Dynu control panel** → your DDNS hostname → set **IPv4** to the new public IP → save.  
   Or use Dynu’s **IP update API** / a small cron script (see [Dynu IP update API](https://www.dynu.com/DynamicDNS/IPUpdateAPI)).
2. Wait a few minutes for DNS to update.
3. No change needed to Vercel **`BACKEND_URL`** (hostname stays the same).

---

## Part G — Optional: Redis + Celery (bigger VM only)

Only if you have **enough RAM** (not typical on 1 GB Micro):

1. In **`backend/.env`** add: `REDIS_URL=redis://redis:6379/0`
2. `docker compose --profile cache up -d --build`
3. Restart Caddy if needed (usually unchanged).

---

## Path B — Cloudflare Tunnel (HTTPS without opening 443 on OCI)

Useful if you **cannot** open inbound 80/443.

1. Create a Cloudflare account; install **`cloudflared`** on the VM ([Cloudflare Tunnel docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)).
2. Run a tunnel to `http://127.0.0.1:8000`.
3. Cloudflare gives you an **`https://…`** URL — put that in Vercel **`BACKEND_URL`**.
4. **CORS_ORIGINS** still lists your **`https://….vercel.app`**.

(Exact commands change over time; follow Cloudflare’s current quick tunnel or named tunnel guide.)

---

## Path C — Demo: HTTP + public IP (not recommended)

Only for quick tests:

1. NSG: allow **TCP 8000** from `0.0.0.0/0` (high risk — anyone can hit your API).
2. Vercel **`BACKEND_URL`** = `http://YOUR_PUBLIC_IP:8000` (no `s` in http).
3. **CORS_ORIGINS** still `https://your-app.vercel.app`.

Next.js **server** `fetch` to HTTP often works; traffic is **not** encrypted to OCI. Use **Dynu + HTTPS** (this guide) or buy a domain for anything public-facing.

---

## Checklist summary (do in order)

- [ ] A1 Public IP noted  
- [ ] A2 Dynu hostname → that IP  
- [ ] A3 NSG 22 / 80 / 443  
- [ ] A4 Vercel URL copied  
- [ ] B1 SSH  
- [ ] B2 Docker  
- [ ] B3 Clone repo  
- [ ] B4 `backend/.env` (`USDA_FDC_API_KEY`, `CORS_ORIGINS`, `ENVIRONMENT`)  
- [ ] B5 `docker compose up -d --build backend`  
- [ ] C1–C3 Caddy + `Caddyfile` hostname = Dynu  
- [ ] `curl https://YOUR.dynu.net/health` OK  
- [ ] D1 Vercel `BACKEND_URL` = that https URL  
- [ ] D2 Redeploy  
- [ ] E Browser test  

---

## Appendix: OCI VCN — fix and verify (SSH + HTTP/HTTPS)

Use this when **port 443/80** from the internet fails but **Caddy listens on `*:443`** on the VM (rules or routing on OCI are wrong).

### A. Instance must have a **public IPv4**

1. **Console** → **Compute** → **Instances** → your instance (e.g. `backend-ingresure`).
2. Under **Instance access** / **Primary VNIC**, open the **subnet** link and note the name.
3. Confirm **Public IPv4 address** is shown (not “—” / empty).

- **No public IP:** assign one (**Edit VNIC** → **Assign public IPv4 address**) or create a **reserved public IP** and associate it to the VNIC. Without it, the internet cannot reach your VM.

### B. Subnet must be **public** (route to Internet Gateway)

1. **Networking** → **Virtual cloud networks** → your **VCN**.
2. **Subnets** → open the subnet your instance uses.
3. Note **Route table** name → open it.
4. There must be a rule:

| Destination | Target |
|-------------|--------|
| **0.0.0.0/0** | **Internet Gateway** (your VCN’s IGW, state: Available) |

- **Missing 0.0.0.0/0 → IGW:** add it. Without it, inbound responses and outbound internet (Let’s Encrypt, `apt`) break or behave oddly.

### C. **Internet Gateway** exists and is **attached**

1. Same **VCN** → **Internet Gateways**.
2. One IGW should exist, **Available**, attached to this VCN.
3. If you create a new IGW, attach it and point the **subnet route table** `0.0.0.0/0` to it.

### D. **Security List** on that subnet (ingress)

1. **Subnets** → your subnet → **Default Security List** (or the security list shown).
2. **Ingress rules** must include (CIDRs as in Step A3):

| Source | Protocol | Dest ports |
|--------|----------|------------|
| Your IP/32 | TCP | **22** |
| 0.0.0.0/0 | TCP | **80** |
| 0.0.0.0/0 | TCP | **443** |

3. **Egress:** allow traffic out (e.g. **All protocols** → `0.0.0.0/0`) or at least TCP 443 to Let’s Encrypt and your package mirrors.

### E. **Network Security Group (NSG)** on the VNIC (if any)

1. **Compute** → **Instances** → instance → **Attached VNICs** → primary VNIC.
2. If **Network security groups** lists one or more NSGs, open **each** and add the **same** ingress rules as in **D** (NSGs **stack** with the subnet security list — both apply).

### F. Common mistakes

| Symptom | Check |
|---------|--------|
| Works on VM `curl 127.0.0.1:443` but **not** from laptop | **Public IP**, **route 0.0.0.0/0 → IGW**, **ingress 443** on the **actual** subnet + NSG. |
| Wrong IP in DNS | **Public** IP in console = **A record** for your API hostname. |
| Changed rules but no effect | Wait **1–2 minutes**; confirm you edited the **VNIC’s** subnet / NSG, not another VCN. |

### G. Verify from your **laptop** (replace `PUBLIC_IP`)

```bash
nc -vz4 PUBLIC_IP 22
nc -vz4 PUBLIC_IP 80
nc -vz4 PUBLIC_IP 443
```

(`-4` forces IPv4 so you’re not testing IPv6 by accident.)

- All **succeeded** → OCI path is open; remaining issues are **DNS**, **Caddy/TLS**, or **app**.
- **443 timeout** → NSG / security list / route / no public IP (packet dropped).
- **443 refused** (immediate) → Often **no IPv4 listener on 443** even when `ss` shows a socket. On the **VM** run:
  - `sudo ss -tlnp4 | grep -E ':80|:443'` — you want **`0.0.0.0:80`** and **`0.0.0.0:443`** with **caddy**. If **empty**, add a **global** `{ default_bind 0.0.0.0 }` block at the **top** of `/etc/caddy/Caddyfile` (see Step C2), then `sudo systemctl restart caddy`. Compare with `sudo ss -tlnp | grep -E ':80|:443'` to spot IPv6-only listeners.
  - While you run `nc` from the laptop: `sudo tcpdump -ni $(ip -4 route | awk '/default/ {print $5; exit}') tcp port 443` — **no packets** = wrong public IP or OCI firewall/route; **SYN in** then **RST** = host/firewall/listener issue; check `sudo iptables -L INPUT -n -v` for **DROP/REJECT** on 443.
- Confirm **PUBLIC_IP** matches **Compute → instance → Primary VNIC → Public IPv4** (not an old or reserved IP on another resource).

### H. OCI **Network Path Analyzer** (optional)

**Networking** → **Network path analyzer** → create analysis: **Source** = internet or a test instance, **Destination** = your instance **private IP**, protocol **TCP** port **443**. Use the result to see where the path is dropped.

---

## Remaining “plan” tasks (what this guide covers)

| Task | Status after you finish above |
|------|-------------------------------|
| OCI API running | Done |
| HTTPS for API | Done (Dynu + Caddy) |
| Vercel `BACKEND_URL` | Done |
| `CORS_ORIGINS` | Done |
| LLM second VM | Optional later ([DEPLOY.md](DEPLOY.md)) |
| Multi-user DB for profiles | Optional later |

More topology options: **[DEPLOY.md](DEPLOY.md)**. Cutover / stage status: architecture tracker + [`docs/item16_legacy_cutover_spec.md`](docs/item16_legacy_cutover_spec.md).
