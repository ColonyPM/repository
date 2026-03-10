# Repository
ColonyPM's package repository website.

## Setting up the development environment
A ``.dev.env`` file is needed:
```bash
# --- Django ---
DEBUG=1
SECRET_KEY=...
DJANGO_ALLOWED_HOSTS=yourdomain.com,localhost,...
DJANGO_CSRF_TRUSTED_ORIGINS=https://xxx.xxx

# --- GitHub OAuth ---
GH_CLIENT_ID=...
GH_CLIENT_SECRET=...

# --- Entrypoint ---
RUN_MIGRATIONS=1
DJANGO_COLLECTSTATIC=1

# --- Postgres ---
POSTGRES_DB=app_prod
POSTGRES_USER=app_user
POSTGRES_PASSWORD=...
POSTGRES_HOST=db
POSTGRES_PORT=5432


TUNNEL_TOKEN=... # optional cloudflare tunnel token for access outside of localhost
```
And to start it:
```bash
docker compose -f compose.dev.yml up
```

## Deploying to production
See ``.prod.env.example`` for what env variables are needed to deploy

```bash
docker compose -f compose.prod.yml up
```
