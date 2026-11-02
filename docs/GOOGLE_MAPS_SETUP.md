# Google Maps Platform Integration Guide — QuakeScope

This guide provides step-by-step instructions for enabling Google Maps JavaScript API in QuakeScope.

> **Zero-Dependency Fallback:**
> Google Maps is completely **optional**. QuakeScope defaults out-of-the-box to **Leaflet (CartoDB Dark Matter / OpenStreetMap)** requiring zero configuration, zero billing, and zero API keys. If no Google Maps API key is configured or if an error occurs, QuakeScope gracefully falls back to Leaflet and **never blanks the dashboard**.

---

## 1. Create a Google Cloud Project

1. Navigate to the [Google Cloud Console](https://console.cloud.google.com/).
2. Click the project dropdown at the top of the page and select **New Project**.
3. Name your project (e.g., `quakescope-earthquake-intel`) and click **Create**.
4. Select the newly created project.

---

## 2. Enable the Maps JavaScript API

1. In the Google Cloud Console, open the navigation menu and go to **APIs & Services > Library**.
2. In the search box, search for **Maps JavaScript API**.
3. Click on **Maps JavaScript API** and click **Enable**.

---

## 3. Create and Restrict Your API Key

> **Security Requirement:**
> Browser API keys are loaded by client-side web applications and are visible in network requests. Therefore, you **must apply application and API restrictions** to prevent unauthorized usage and protect your quota.

1. Navigate to **APIs & Services > Credentials**.
2. Click **+ CREATE CREDENTIALS** and select **API key**.
3. Once the key is created, click **Edit API key** (or the pencil icon).

### Application Restrictions (HTTP referrers)
Under **Set application restrictions**:
- Choose **Websites** (HTTP referrers).
- Under **Website restrictions**, click **ADD**:
  - For GitHub Pages production:
    `https://khaleelxrahman.github.io/earthquake-github-dashboard/*`
  - For local development / preview:
    `http://localhost:*/*`
    `http://127.0.0.1:*/*`

### API Restrictions
Under **API restrictions**:
- Select **Restrict key**.
- In the dropdown, select **only**:
  - `Maps JavaScript API`
- Click **Save**.

---

## 4. Set Budget Alerts and Quotas

Google Cloud provides a monthly recurring credit for Maps Platform. To protect against unexpected charges:

1. Go to **Billing > Budgets & alerts** in Google Cloud Console.
2. Click **Create Budget**.
3. Set a target budget (e.g. \$1.00 or \$10.00) and configure email notifications at 50%, 90%, and 100%.
4. Optionally, go to **APIs & Services > Maps JavaScript API > Quotas & System Limits** and cap maximum requests per day (e.g., 5,000 requests/day).

---

## 5. Configure in QuakeScope

You can provide the key using any of the following methods:

### Method A: GitHub Actions Secret (Automated Deployment)
For automated GitHub Pages builds:
1. Go to your GitHub repository: `https://github.com/KhaleelxRahman/earthquake-github-dashboard`.
2. Go to **Settings > Secrets and variables > Actions**.
3. Click **New repository secret**.
4. Set Name: `GOOGLE_MAPS_API_KEY`.
5. Set Value: Paste your restricted Google Maps API key.
6. Click **Add secret**.
The workflow `.github/workflows/deploy-pages.yml` automatically passes this secret during the build step.

### Method B: Local Build via CLI or Environment Variable
```bash
# Via Environment Variable
export GOOGLE_MAPS_API_KEY="AIzaSy..."
python data_pipeline.py --output-dir _site

# Via CLI Argument
python data_pipeline.py --google-maps-key "AIzaSy..." --output-dir _site
```

### Method C: In-Browser Session Key Entry
When viewing the dashboard:
1. Navigate to the **Live Map** tab.
2. Click **🗺️ Google Maps** in the map engine switcher.
3. If no key was baked into the build, a banner appears with an **Enter Key for Session** button.
4. Input your API key. It is saved only to `sessionStorage` in your browser and is never transmitted to external servers other than `maps.googleapis.com`.

---

## 6. Verification and Troubleshooting

| Symptom | Cause | Solution |
| :--- | :--- | :--- |
| **Notice banner appears: "Authentication failed"** | `gm_authFailure` triggered: Invalid key, billing not active, or referrer mismatch | Ensure HTTP referrer matches `https://khaleelxrahman.github.io/earthquake-github-dashboard/*`. Verify billing is enabled on GCP project. |
| **Notice banner appears: "API key is not configured"** | Build did not have `GOOGLE_MAPS_API_KEY` set | Dashboard gracefully remains on Leaflet. You can click "Enter Key for Session" or add the repository secret. |
| **Markers not rendering** | USGS data feed empty or filters too restrictive | Check Min Mag filter (set to "All") and depth filter. |
