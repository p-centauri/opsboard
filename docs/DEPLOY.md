# Deploying the public demo

One small Linux VPS runs the same Docker Compose stack as local development, with Caddy
providing HTTPS. Only ports 80/443 are public. Postgres, the API and Next.js are reachable
only inside Docker, which is what keeps the login rate limit's client IP honest (DECISIONS D13).

This flow was rehearsed locally over HTTPS: first deploy, migrate, seed, HTTP→HTTPS redirect,
secure cookie, a spoofed `X-Forwarded-For` ignored, and a demo reset. Things not yet done for
real: a public DNS name, a real certificate, and a real server.

## 1. Server
- Ubuntu 24.04 LTS, **2 GB RAM or more** (the Next.js build needs about 1–1.5 GB). On a
  1 GB machine, add 2 GB of swap before the first build.
- Any provider works (Hetzner, DigitalOcean, Vultr, …). Compare current prices when you
  order; the cheapest 2 GB plan is enough.

## 2. DNS
Create an `A` record (and `AAAA` if the server has IPv6) for the demo hostname, e.g.
`opsboard.yourdomain.com`, pointing at the server's IP. Wait until
`dig +short opsboard.yourdomain.com` returns the IP. Caddy needs that to get a certificate.

No domain yet? `<server-ip>.sslip.io` (e.g. `203.0.113.10.sslip.io`) resolves to the IP for
free and works with Let's Encrypt. Because it's shared, it can occasionally hit Let's Encrypt
rate limits.

## 3. Prepare the server (as a sudo user, not root)
```bash
sudo apt update && sudo apt -y upgrade
sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443 && sudo ufw --force enable
```
Install Docker Engine and the Compose plugin with Docker's official apt repository
(docs.docker.com/engine/install/ubuntu), then `sudo usermod -aG docker $USER` and log in again.

Note: Docker-published ports bypass ufw. That's fine here, because the only published ports
are 80/443.

## 4. Configure
```bash
git clone https://github.com/<you>/opsboard.git && cd opsboard
cp deploy/.env.production.example .env
nano .env    # SITE_ADDRESS + every CHANGE_ME (openssl rand -base64 32 | tr -d '/+=')
chmod 600 .env
```

## 5. Deploy
```bash
./deploy/deploy.sh --seed    # first time: build, migrate, start, load demo data
./deploy/deploy.sh           # every later update: pull, build, migrate, restart
```
Then open `https://<SITE_ADDRESS>/login` and use the demo buttons.

## 6. Nightly demo reset
Visitors can create and edit data, so restore the seed every night:
```bash
crontab -e
# 03:00 UTC daily
0 3 * * * /home/<you>/opsboard/deploy/reset-demo.sh >> /home/<you>/opsboard-reset.log 2>&1
```
The reset runs in one transaction (about 12 s). Requests during it wait, and everyone
signs in again afterwards.

## 7. Check it
```bash
curl -sI https://<SITE_ADDRESS>/login | grep -i strict-transport   # HSTS present
curl -s -o /dev/null -w '%{http_code}\n' http://<SITE_ADDRESS>/     # 308 → HTTPS
nc -zv <server-ip> 5432; nc -zv <server-ip> 8000                    # both must fail
```

## Operations
- **Logs:** `docker compose -f docker-compose.yml -f deploy/docker-compose.server.yml logs -f`
- **Backups:** not needed for the demo, since the data is regenerated nightly. For real data,
  add a nightly `pg_dump` to off-server storage and test a restore.
- **Updates:** OS patches with `unattended-upgrades`; app updates with `./deploy/deploy.sh`.
- **Admin account:** `admin@demo.local` with `SEED_ADMIN_PASSWORD`. Keep it private; the
  public demo only exposes viewer and manager.
