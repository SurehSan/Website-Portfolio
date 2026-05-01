# Deploying the dashboard

The fastest path is Streamlit Community Cloud, which is free and
deploys directly from a public GitHub repo.

---

## 1. Push to GitHub

```bash
cd ltc-dashboard
git init
git add .
git commit -m "initial build"
git branch -M main
git remote add origin https://github.com/<your-user>/ltc-dashboard.git
git push -u origin main
```

---

## 2. Connect Streamlit Community Cloud

1. Sign in at <https://share.streamlit.io> with your GitHub account.
2. **New app** → select the repo and branch.
3. **Main file path** → `app.py`.
4. **Python version** → `3.11` or higher.
5. **Advanced** → leave the secrets blank for now (no API keys).
6. **Deploy.** First build takes 1–3 minutes.

Streamlit will give you a URL like
`https://<your-app>-<hash>.streamlit.app`.

---

## 3. Custom domain (`dashboard.surehsan.com`)

Streamlit Cloud doesn't host custom domains directly, so use a CNAME:

1. In your DNS provider (Cloudflare for `surehsan.com`):
   ```
   Type:  CNAME
   Name:  dashboard
   Value: <your-app>-<hash>.streamlit.app
   Proxy: DNS only
   ```
2. Wait for propagation (~5 minutes).
3. Visit `https://dashboard.surehsan.com` — Cloudflare's edge will
   route to the Streamlit-issued certificate.

---

## 4. Build cache / redeploys

Each `git push` to `main` triggers a redeploy. To avoid surprising
diffs:

- **Pin Python version** in `requirements.txt` headers if you
  encounter compat issues.
- **Don't commit `db/ltc.db`** — Streamlit Cloud rebuilds it on
  startup if you add a `db/load.py` step to the cloud's start
  command. Or simpler: have `app.py` rebuild on first run if the DB
  file is missing (the dashboard already gracefully handles the
  missing-DB case).

---

## 5. Post-deploy checklist

- [ ] Dashboard loads at `dashboard.surehsan.com`.
- [ ] Sidebar controls re-render the charts.
- [ ] "Warehouse peek" panel shows non-empty rows.
- [ ] Portfolio break-even table renders with correct color coding.
- [ ] README link to demo updated to the live URL.
