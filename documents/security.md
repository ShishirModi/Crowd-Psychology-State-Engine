# Security & Multi-User Deployment

## 1. Multi-User Isolation
By default, Python application servers can share global state. We have refactored `app.py` to instantiate all critical services (`SignalProvider`, `Classifier`, etc.) inside `st.session_state`.

**Result**:
-   User A changing the location to "London" **does NOT** affect User B who is monitoring "New York".
-   Each user has their own independent history and metrics.

## 2. Authentication
The application is now protected by a password.

**To set the password:**
1.  **Locally**: Create `.streamlit/secrets.toml` (do not commit this):
    ```toml
    APP_PASSWORD = "my_secure_password"
    ```
2.  **Streamlit Cloud**:
    -   Go to App Settings -> **Secrets**.
    -   Add: `APP_PASSWORD = "my_secure_password"`
    -   **Multiple Passwords**: You can also provide a list:
        ```toml
        APP_PASSWORD = ["admin_pass", "guest_pass", "team_pass"]
        ```

**Mandatory**:
The application will **not start** without `APP_PASSWORD` set. The **first** password in the list grants Admin privileges.

## 3. Data Protection
-   **No Database**: Currently, all history is in-memory (`st.session_state`). When the user closes the tab, data is wiped. This prevents data leaks between sessions.
-   **Secrets**: API Keys are loaded from `st.secrets` or environment variables, never committed to code.

## 4. Application Hardening
-   **Timing Attack Protection**: Password verification uses `secrets.compare_digest` (constant-time comparison) to prevent side-channel timing attacks.
-   **Input Sanitization**: Logs are automatically scrubbed of sensitive keys (API Keys, App IDs) before being output to the console.
