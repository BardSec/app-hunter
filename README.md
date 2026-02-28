# Entra App Auditor

A security and compliance auditing tool for Microsoft Entra ID (formerly Azure AD), designed for IT administrators in K-12 school districts.

## Features

| Feature | Description |
|---|---|
| **App Inventory** | Lists all app registrations and enterprise apps with key metadata |
| **Permission Auditor** | Surfaces all API permissions with risk classification (Critical / High / Medium / Low) |
| **Credential Tracker** | Flags client secrets and certificates expiring within 30/60/90 days or already expired |
| **Ownerless App Detection** | Highlights apps with no assigned owner |
| **Compliance View** | Filtered view of apps most relevant to FERPA/COPPA review |

## Quick Start (Mock Mode — No Tenant Required)

```bash
cp .env.example .env
docker compose up
```

Open [http://localhost:3000](http://localhost:3000).

Mock mode ships with 12 realistic K-12 district apps including expired credentials, ownerless apps, and critical-risk permissions.

## Connecting to a Real Entra ID Tenant

### 1. Register an app in Entra ID

In the Azure portal → Entra ID → App registrations → New registration:
- Name: `Entra App Auditor`
- Supported account types: **Accounts in this organizational directory only**
- No redirect URI needed for app-only mode

### 2. Grant API permissions (app-only mode)

Add the following **Application** permissions on Microsoft Graph:
- `Application.Read.All`
- `Directory.Read.All`
- `AuditLog.Read.All`

Grant admin consent.

### 3. Create a client secret

Certificates & secrets → New client secret. Copy the value immediately.

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
MOCK_MODE=false
AUTH_MODE=app
TENANT_ID=<your-tenant-id>
CLIENT_ID=<your-client-id>
CLIENT_SECRET=<your-client-secret>
VITE_AUTH_MODE=app
```

```bash
docker compose up
```

## Auth Modes

| Mode | Description | Config |
|---|---|---|
| `mock` | Built-in demo data, no Entra ID needed | `MOCK_MODE=true` |
| `app` | App-only auth via client credentials | `AUTH_MODE=app` + `CLIENT_SECRET` |
| `delegated` | User signs in via MSAL.js; token passed to backend | `AUTH_MODE=delegated`, `VITE_AUTH_MODE=delegated` |

## Running Locally Without Docker

**Backend:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env   # edit as needed
flask run
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Architecture

```
Entra-app-hunter/
├── backend/               Flask API
│   ├── data/              Mock data (K-12 realistic scenarios)
│   ├── services/          Graph API wrapper, risk analyzer, credential tracker
│   └── routes/            /api/apps, /api/dashboard, /api/compliance
└── frontend/              React + Vite + Tailwind
    └── src/
        ├── components/    Shared UI, layout, app table, detail panel
        ├── pages/         Dashboard, AppInventory, Permissions, Credentials, Compliance
        ├── hooks/         React Query data hooks
        └── lib/           API client, utilities
```

## Risk Classification

| Level | Examples |
|---|---|
| **Critical** | `Directory.ReadWrite.All`, `User.ReadWrite.All`, `Mail.ReadWrite`, `Application.ReadWrite.All` |
| **High** | `Directory.Read.All`, `User.Read.All`, `Mail.Read`, `AuditLog.Read.All` |
| **Medium** | `User.ReadBasic.All`, `Calendars.ReadWrite`, `People.Read` |
| **Low** | `User.Read`, `openid`, `profile`, `email` |

## Compliance Criteria

Apps are surfaced in the Compliance view when they meet any of:
- Risk level is **Critical** or **High**
- App has **no assigned owner**
- Sign-in audience allows **external accounts** (MultiOrg or Personal MS)
