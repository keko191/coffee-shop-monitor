# UK Coffee Shop Closure Monitor (Starbucks + Costa)

Tracks the `businessStatus` field on Google's Places API for every Starbucks
and Costa Coffee in Greater London, and pings a Slack/Discord webhook
whenever one changes to `CLOSED_TEMPORARILY` or `CLOSED_PERMANENTLY` (or
reopens).

Runs automatically on a weekly schedule via GitHub Actions - no server
needed. Both brands run independently (separate store lists, separate state
files) but share the same repo, code, and schedule.

## Cost: free, if you leave the schedule as-is

Google's Places API is pay-as-you-go, but the specific field this project
needs (`businessStatus`) falls in Google's "Pro" pricing tier, which gets
**5,000 free calls per month**, then $17 per 1,000 after that.

- **~600 stores checked weekly** ≈ 2,600 calls/month → **stays inside the free tier, £0/$0**.
- ~600 stores checked daily ≈ 18,000 calls/month → roughly **$150-220/month**.

The included workflow is set to run **weekly** on purpose. Don't change it
to a daily cron unless you're fine with a real bill - closures don't happen
overnight anyway, so weekly is plenty for this use case.

The one-off store-discovery scan (`discover_stores.py`) only requests free
fields (name, address, location - not `businessStatus`), so running it
occasionally to catch new store openings costs nothing extra.

## One-time setup (~10 minutes)

### 1. Get a Google Places API key
1. Go to https://console.cloud.google.com/ and create a project.
2. Enable the **Places API (New)** for that project (APIs & Services →
   Library → search "Places API (New)" → Enable). Note: the *original*
   "Places API" is now Legacy status and can't be enabled on new projects -
   make sure you pick the one labelled "(New)". This project's code already
   targets the New API's endpoints.
3. Go to APIs & Services → Credentials → Create Credentials → API Key.
4. (Recommended) Restrict the key to the Places API (New) only, under the
   key's settings.
5. (Recommended) Set a budget alert in Cloud Billing so you get an email if
   usage ever exceeds the free tier unexpectedly - Google doesn't auto-stop
   billing on its own.

### 2. Get a webhook URL
- **Discord**: Server Settings → Integrations → Webhooks → New Webhook → Copy URL.
- **Slack**: Create an "Incoming Webhook" app at https://api.slack.com/apps → Copy the webhook URL.

Both brands post to the same webhook/channel by default; each alert names the
brand and address so you can tell them apart.

### 3. Create a GitHub repo with these files
- Create a new **private** repo (recommended).
- Push all the files in this folder to it.

### 4. Add your secrets to the repo
Go to your repo → Settings → Secrets and variables → Actions → New repository secret. Add two:
- `GOOGLE_API_KEY` = the key from step 1
- `WEBHOOK_URL` = the webhook URL from step 2

### 5. Run the initial store discovery
Go to the repo's **Actions** tab → "Discover Coffee Shop Stores (manual)" →
**Run workflow** → choose `both` (or just `starbucks`/`costa` if you only
want one for now).

This scans a grid across Greater London and builds `stores_starbucks.json`
and `stores_costa.json` (expect roughly 250-300 Starbucks and 300-400 Costa
locations - Costa has more London sites). Takes a few minutes per brand and
commits the result back to the repo automatically. This step is free.

### 6. That's it
From here, "Check Coffee Shop Status" runs automatically every Monday at
07:00 UTC for both brands, for free. Whenever a store's status flips, you'll
get a message like:

    🔴 Status change: Costa Coffee
    45 High Street, London
    OPERATIONAL → CLOSED_PERMANENTLY
    https://maps.google.com/?cid=...

You can also trigger either workflow manually any time from the Actions tab
(each manual run still counts toward the monthly free allowance the same as
a scheduled one).

## Maintenance

- **Re-run "Discover Coffee Shop Stores"** every month or two to catch newly
  opened stores (it only adds new ones, never removes - closures are tracked
  separately in the state files so you keep a full history).
- If you want a different schedule, edit the `cron` line in
  `.github/workflows/check-status.yml` ([crontab.guru](https://crontab.guru) helps
  build the expression), but see the cost section above before going more
  frequent than weekly. All times are UTC.
- Google's `businessStatus` flag is crowdsourced/algorithmic and occasionally
  wrong or briefly reverted - treat repeated/stable status changes as more
  trustworthy than a single flip.
- Want to add another chain (Pret, Caffè Nero, etc.)? Just add another entry
  to the `matrix` in both workflow files with a new `stores_<brand>.json` /
  `state_<brand>.json` pair - the scripts are already brand-agnostic.
- Pricing and free-tier thresholds are Google's to change - if it's been a
  while since you set this up, it's worth checking
  https://developers.google.com/maps/billing-and-pricing/overview to confirm
  the numbers above are still current.

## Files

| File | Purpose |
|---|---|
| `discover_stores.py` | Text-search grid scan to find all stores of a given brand in Greater London (free fields only) |
| `check_status.py` | Weekly check comparing current business status to last known status (Pro-tier field) |
| `stores_starbucks.json` / `stores_costa.json` | Discovered store place IDs (generated by discover_stores.py) |
| `state_starbucks.json` / `state_costa.json` | Last known status per store (updated automatically, don't edit by hand) |
| `.github/workflows/` | The two GitHub Actions workflows |
