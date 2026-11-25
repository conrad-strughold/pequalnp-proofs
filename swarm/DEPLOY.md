# HTTPS staging deployment

This is a single-node service, not a fully hardened unrestricted public deployment.

On a Docker-capable Linux host with a public IP, point a DNS hostname to the host. Open TCP ports 80 and 443 only. From the swarm directory set SWARM_DOMAIN to the hostname and independent random SWARM_ADMIN_TOKEN and SWARM_INVITE_TOKEN (at least 32 characters). Never commit credentials. Run docker compose up -d --build. Caddy obtains TLS certificates and proxies requests; SQLite lives in a named volume. Use docker compose ps and curl https://YOUR_DOMAIN/healthz to check operation.

The public dashboard is readable without credentials. Contribution remains invite-gated. Add upstream request throttling, monitoring, moderation and verified identities before unrestricted registration. Keep backups off-host and test restoration. The optional AI planner requires operator-supplied credentials and can incur costs. Never expose the raw application port.

Netlify static hosting is not a suitable direct host for this persistent Python/SQLite process. Use a container host with a durable disk instead.
