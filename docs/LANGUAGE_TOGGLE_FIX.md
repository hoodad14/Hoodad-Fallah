# Language toggle fix (v1.6.1)

## Root cause

The language button markup and translation runtime were present in the source tree, but `Dockerfile.frontend` copied only `index.html`, `styles.css`, `app.js`, and the font into the Nginx image. Therefore `/i18n.js` returned 404 in the Dockerized site, leaving the visible button without its click handler.

## Fix

- Copy `i18n.js` into `/usr/share/nginx/html/`.
- Serve `/i18n.js` with `Cache-Control: no-store`.
- Use frontend image tag `1.6.1`.
- Change the browser cache-busting query to `i18n.js?v=1.6.1`.

## Test

```powershell
docker compose down --remove-orphans
docker image rm arenapass-frontend:1.4.0 2>$null
docker compose build --no-cache frontend
docker compose up -d
```

Then open `http://127.0.0.1:8080`, press `Ctrl+F5`, and confirm that clicking `FA` changes the page to English/LTR and clicking `EN` restores Persian/RTL.
