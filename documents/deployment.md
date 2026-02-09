# Deploying CPSE to Streamlit Community Cloud

This guide outlines how to deploy the Crowd Psychology State Engine (CPSE) to the web using Streamlit Community Cloud.

## Prerequisites
1.  **GitHub Account**: The code must be hosted in a public (or private) GitHub repository.
2.  **Streamlit Account**: Sign up at [share.streamlit.io](https://share.streamlit.io/).
3.  **API Keys**: You need your `TOMTOM_API_KEY` and `OPENWEATHERMAP_API_KEY`.

## Step 1: Prepare Repository
Ensure your repository has the following files (already done):
-   `app.py`: The entry point for the dashboard.
-   `requirements.txt`: Lists all Python dependencies.
-   `config.yaml`: Configuration file.

**Push your code to GitHub:**
```bash
git add .
git commit -m "Ready for deployment"
git push origin main
```

## Step 2: Connect Streamlit Cloud
1.  Log in to [Streamlit Community Cloud](https://share.streamlit.io/).
2.  Click **"New app"**.
3.  Select your repository (`Crowd-Psychology-State-Engine`), branch (`main`), and main file path (`app.py`).

## Step 3: Configure Secrets (Critical)
**Do not skip this.** Your app will fail without API keys.

1.  Before clicking "Deploy", click on **"Advanced Settings"**.
2.  Go to the **"Secrets"** section.
3.  Paste your API keys in TOML format (similar to `.env` but with quotes):

```toml
# Streamlit Secrets (TOML format)
TOMTOM_API_KEY = "your_actual_tomtom_key_here"
OPENWEATHERMAP_API_KEY = "your_actual_weather_key_here"
```

> **Note**: Our code uses `load_config()` which checks `os.getenv()`. Streamlit automatically injects these secrets as environment variables, so no code changes are needed!

## Step 4: Deploy
1.  Click **"Deploy!"**.
2.  Wait for the implementation environment to provision (this takes 1-2 minutes).
3.  Once the app is live, you will see the dashboard.

## troubleshooting
-   **"KeyError: 'api'"**: Did you copy `config.yaml`? Ensure it's in the repo.
-   **"API Key Missing"**: Double-check Step 3. The keys must be exact.
-   **"ModuleNotFoundError"**: Check the logs to see if a package is missing from `requirements.txt`.
