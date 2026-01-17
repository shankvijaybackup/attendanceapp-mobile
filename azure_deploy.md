# Deploying to Azure App Service

If you prefer Azure over Render (to avoid the "sleep" issue or if you have an existing subscription), follow these steps.

## Option 1: VS Code Extension (Easiest)

1. **Install Extension**: Install "Azure App Service" extension in VS Code.
2. **Sign In**: Click the Azure icon -> Sign in to your Azure/Microsoft account.
3. **Create App**:
    * Right-click on your Subscription -> **"Create App Service Web App..."**
    * **Name**: `dr-reddy-attendance-demo` (must be unique).
    * **Runtime**: `Python 3.10` (or 3.11).
    * **Pricing Tier**: `F1` (Free) or `B1` (Basic - recommended for demos to avoid quotas).
4. **Deploy**:
    * Once created, right-click the new App -> **"Deploy to Web App..."**
    * Select your project folder (`attendance_service`).
    * Click "Yes" to update workspace settings if asked.
5. **Startup Configuration** (Vital!):
    * Go to **Azure Portal** -> Your App -> **Configuration** -> **General Settings**.
    * **Startup Command**: `python -m uvicorn app.main:app --host 0.0.0.0`
    * Save.

## Option 2: Azure CLI

If you have `az` CLI installed:

```bash
# 1. Login
az login

# 2. Create Resource Group
az group create --name AttendanceDemoGroup --location eastus

# 3. Create App Service Plan (Free Tier F1)
az appservice plan create --name AttendanceDemoPlan --resource-group AttendanceDemoGroup --sku F1 --is-linux

# 4. Create Web App
az webapp create --resource-group AttendanceDemoGroup --plan AttendanceDemoPlan --name dr-reddy-attendance --runtime "PYTHON:3.10"

# 5. Configure Startup Command
az webapp config set --resource-group AttendanceDemoGroup --name dr-reddy-attendance --startup-file "python -m uvicorn app.main:app --host 0.0.0.0"

# 6. Deploy Code (via ZIP)
# Zip your folder contents first, then:
az webapp deployment source config-zip --resource-group AttendanceDemoGroup --name dr-reddy-attendance --src deployment.zip
```

### 💡 Tip: Keeping Render Awake (Free)

If you stick with Render but hate the "sleep" mode:

1. Deploy to Render (Free).
2. Sign up for [UptimeRobot](https://uptimerobot.com/) (Free).
3. Create a Monitor that pings your Render URL (e.g., `https://yourapp.onrender.com/api/simulate`) every 5 minutes.
4. This keeps the app "awake" so it doesn't spin down!
