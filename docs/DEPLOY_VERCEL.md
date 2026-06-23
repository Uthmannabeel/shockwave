# Deploy the site to Vercel

The Shockwave site is a Flask app, but the live engine needs Orbit Local (a
binary + a local graph) which can't run on Vercel. So we ship a **static export**
(`web-static/`) with a few **baked real analyses**, so the Blast Monitor works
with zero backend. For live analysis on their own code, users run `shockwave-web`
locally.

`web-static/` is already built and committed. To rebuild after changing the site:

```bash
orbit index /path/to/flask            # so baked data is real
python scripts/build_static.py        # → web-static/
```

## Option A — Vercel dashboard (recommended, auto-redeploys on push)

1. Go to **https://vercel.com** and sign in (GitHub login is easiest).
2. **Add New… → Project**.
3. **Import** your repo (GitHub `Uthmannabeel/shockwave`, or your GitLab project).
4. In **Configure Project**:
   - **Framework Preset:** `Other`
   - **Root Directory:** click *Edit* → set to **`web-static`**
   - **Build Command:** leave empty (override → none)
   - **Output Directory:** leave default
5. **Deploy.** You'll get a URL like `https://shockwave-xxxx.vercel.app`.

Clean URLs (`/how`, `/app`, …) are handled by `web-static/vercel.json`.

## Option B — Vercel CLI

```bash
npm i -g vercel
cd web-static
vercel login
vercel --prod
```

## After deploying
- Add the live URL to the repo (README badge) and the Devpost submission.
- The Blast Monitor on the hosted site uses baked snapshots (setupmethod / route /
  dispatch_request); everything else shows a "run locally" prompt — by design.
