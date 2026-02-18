# AI Compliance Agent

> Automated website compliance analysis for ECOMMBX merchant site requirements.  
> Internal service for NBCgate — validates merchant websites against a 30+ item checklist and generates professional DOCX reports.

---

## Overview

AI Compliance Agent crawls merchant websites, uses **Gemini AI** to extract regulatory data, then applies **deterministic rules** across 8 compliance sections. The result is a detailed checklist report with pass/fail/warning status for each item.

### Key Features

| Feature | Description |
|---------|-------------|
| **30+ Compliance Checks** | 8 sections: Company Info, Contacts, Policies, Product Description, Checkout, Receipt, Updates, Mobile |
| **Custom Checklist Upload** | Upload PDF/DOCX/TXT checklists → AI parses into rules → analyze site against custom rules |
| **Weighted Scoring** | 0–100 score with section weights; status: COMPLIANT / NEEDS_REVIEW / NON-COMPLIANT |
| **DOCX Report** | Professional document with per-section tables, color-coded statuses (✅❌⚠️ℹ️), found values, recommendations |
| **Policy Generator** | Auto-generates missing policies (Terms, Privacy, Refund, Cancellation, Payment) via Gemini AI |
| **Jurisdiction Support** | EU/GDPR, UK, Cyprus, US, General — jurisdiction-specific clauses |
| **Widget** | JS snippet for merchants to embed policies on their site; generate tokens via UI or API |
| **API v1** | Authenticated API with rate limiting for portal integration |
| **Web UI** | Tabbed interface at `/` — Standard Checklist, Custom Checklist Upload, Widget Generator |

---

## Architecture

```
portal.nbcgate.com (Next.js)
         │
         │  Authorization: Bearer <API_KEY>
         ▼
┌─────────────────────────────┐
│   AI Compliance Agent       │
│   FastAPI on Railway        │
│                             │
│  /api/v1/compliance/check   │──▶ Playwright Crawler
│  /api/v1/policies/generate  │──▶ Gemini 2.5 Flash
│  /api/widget/{token}/*.js   │──▶ Policy Widget
│                             │
│  PostgreSQL (Railway)       │
└─────────────────────────────┘
         ▲
         │  <script src=".../policies.js">
         │
    Merchant Site
```

### Tech Stack

- **Runtime**: Python 3.11+
- **Framework**: FastAPI (async)
- **AI**: Google Gemini 2.5 Flash via `google-genai` SDK
- **Database**: PostgreSQL (Railway) / SQLite (local dev)
- **ORM**: SQLAlchemy 2.0 (async)
- **Crawler**: Playwright (headless Chromium)
- **Reports**: python-docx
- **File Parsing**: pypdf (PDF), python-docx (DOCX)
- **Auth**: Bearer token (API key)
- **Form Data**: python-multipart (file uploads)

---

## Setup & Run

### Prerequisites
- Python 3.11+
- (Optional) Docker for deployment

### Quick Start (Local)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Install Playwright browser
playwright install chromium

# 3. Configure (optional — works with defaults)
cp .env.example .env

# 4. Run server
uvicorn app.main:app --reload

# 5. Open http://127.0.0.1:8000
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./compliance.db` | Database connection (auto-converts `postgresql://` to `postgresql+asyncpg://`) |
| `LLM_PROVIDER` | `mock` | AI provider: `mock`, `gemini`, or `openai` |
| `GEMINI_API_KEY` | — | Required if `LLM_PROVIDER=gemini` |
| `API_SECRET_KEY` | `dev-secret-key-...` | API key for `/api/v1/*` endpoints. **Change in production!** |
| `ALLOWED_ORIGINS` | `http://localhost:8000,...` | Comma-separated CORS origins (use `*` for open access) |
| `ENVIRONMENT` | `development` | `development` or `production` |
| `PORT` | `8000` | Server port (Railway sets this automatically) |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## API Reference

### Authentication

All `/api/v1/*` endpoints require:

```
Authorization: Bearer <API_SECRET_KEY>
Content-Type: application/json
```

The web form endpoint `/api/compliance/check` does **not** require authentication.

---

### Compliance Check

#### `POST /api/v1/compliance/check`

Run a full compliance check (rate limited: **1 per client per day**).

**Request:**
```json
{
  "url": "https://merchant-site.com",
  "company_name": "Merchant Ltd",
  "client_id": "merchant_123"
}
```

**Response (200):**
```json
{
  "report_id": "rpt_a1b2c3d4e5f6",
  "score": 65,
  "status": "NEEDS_REVIEW",
  "summary": "Site needs improvements in Policies and Checkout sections.",
  "checklist": [
    {
      "section": "1. Company Information",
      "item": "Legal company name",
      "rule_id": "CMP-001",
      "status": "pass",
      "found_value": "Merchant Ltd",
      "recommendation": null
    },
    {
      "section": "3. Policies",
      "item": "Privacy Policy",
      "rule_id": "POL-002",
      "status": "fail",
      "found_value": "Not found",
      "recommendation": "Add a Privacy Policy page."
    }
  ],
  "download_url": "/api/v1/compliance/reports/rpt_a1b2c3d4e5f6/download"
}
```

**Error (429):**
```json
{
  "detail": "Rate limit: 1 compliance check per client per day. Try again tomorrow."
}
```

---

#### `GET /api/v1/compliance/reports/{report_id}`

Fetch a saved report as JSON.

#### `GET /api/v1/compliance/reports/{report_id}/download`

Download the compliance report as a `.docx` file.

---

### Policy Generation

#### `POST /api/v1/policies/generate`

Generate missing compliance policies using Gemini AI.

**Request:**
```json
{
  "client_id": "merchant_123",
  "company_name": "Merchant Ltd",
  "legal_address": "Limassol, Cyprus",
  "support_email": "support@merchant.com",
  "site_url": "https://merchant.com",
  "jurisdiction": "CY",
  "language": "English",
  "policies": ["privacy", "refund", "cancellation"]
}
```

**Supported policy types:** `terms`, `privacy`, `refund`, `cancellation`, `payment`

**Supported jurisdictions:** `EU`, `UK`, `CY`, `US`, `GENERAL`

**Response (200):**
```json
[
  {
    "id": "pol_x1y2z3w4v5u6",
    "client_id": "merchant_123",
    "policy_type": "privacy",
    "content_html": "<h2>Privacy Policy</h2><p>...</p>",
    "jurisdiction": "CY",
    "language": "English",
    "version": 1,
    "status": "draft"
  }
]
```

---

#### `GET /api/v1/policies/{client_id}`

List all policies for a client.

#### `GET /api/v1/policies/{client_id}/{policy_id}`

Get a single policy.

#### `PUT /api/v1/policies/{client_id}/{policy_id}`

Edit a policy's HTML content before approving.

**Request:**
```json
{
  "content_html": "<h2>Privacy Policy</h2><p>Updated content...</p>"
}
```

#### `POST /api/v1/policies/{client_id}/{policy_id}/approve`

Approve a policy for publishing via the widget.

#### `DELETE /api/v1/policies/{client_id}/{policy_id}`

Delete a policy.

---

### Widget (Public — No Auth)

#### Create Widget Token

##### `POST /api/widget/create`

Generate or retrieve a widget token for a client.

**Request:**
```json
{
  "client_id": "merchant_123",
  "domain": "merchant.com"
}
```

**Response:**
```json
{
  "token": "a1b2c3d4-e5f6-...",
  "client_id": "merchant_123"
}
```

#### Embed on Merchant Site

Add this script tag to the merchant's website:

```html
<script src="https://ai-precheck.up.railway.app/api/widget/{token}/policies.js"></script>
```

The widget:
- Injects policy links into the page footer
- Opens each policy in a styled modal overlay
- Only shows **approved** policies

#### Widget API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/widget/create` | Create widget token (client_id + domain) |
| `GET /api/widget/{token}/policies.js` | JavaScript widget script |
| `GET /api/widget/{token}/policies` | JSON list of approved policies |
| `GET /api/widget/{token}/policy/{type}` | Standalone HTML page for a policy |

---

### Web Form (No Auth)

#### `POST /api/compliance/check`

Run a compliance check and download DOCX report.

**Request:**
```json
{
  "url": "https://merchant-site.com",
  "company_name": "Merchant Ltd"
}
```

**Response:** DOCX file download.

---

#### `POST /api/compliance/check-json`

Run a compliance check and return JSON results. Supports optional custom rules.

**Request:**
```json
{
  "url": "https://merchant-site.com",
  "company_name": "Merchant Ltd",
  "custom_rules": null
}
```

With custom rules (from `/upload-checklist`):
```json
{
  "url": "https://merchant-site.com",
  "company_name": "Merchant Ltd",
  "custom_rules": [
    {
      "rule_id": "SEC-01",
      "section": "Security",
      "item": "SSL Certificate",
      "description": "Site must use HTTPS",
      "extraction_prompt": "Check if the site uses HTTPS",
      "pass_condition": "not_empty",
      "severity": "fail"
    }
  ]
}
```

**Response:** JSON `ComplianceReport` with `score`, `status`, `checklist`.

---

#### `POST /api/compliance/upload-checklist`

Upload a checklist file (PDF, DOCX, or TXT). The system parses it into structured rules using Gemini AI.

**Request:** `multipart/form-data` with `file` field.

**Response:**
```json
{
  "name": "checklist.pdf",
  "rules": [
    {
      "rule_id": "SEC-01",
      "section": "Security",
      "item": "SSL Certificate",
      "description": "Site must use HTTPS",
      "extraction_prompt": "Check if the site uses HTTPS",
      "pass_condition": "not_empty",
      "severity": "fail"
    }
  ]
}
```

---

#### `POST /api/compliance/generate-policy`

Generate a single policy (public demo, no auth required).

**Request:**
```json
{
  "policy_type": "privacy",
  "company_name": "Merchant Ltd",
  "url": "https://merchant.com"
}
```

**Response:**
```json
{
  "html": "<h2>Privacy Policy</h2><p>...</p>"
}
```

---

## Compliance Checklist (30+ Checks)

| # | Section | Checks |
|---|---------|--------|
| 1 | **Company Information** | Legal name, registration number, legal address, VAT, outlet location, license info, regulator |
| 2 | **Contacts** | Email, phone, physical address, contact page |
| 3 | **Policies** | Terms, Privacy, Refund, Cancellation, Payment policies; accessibility; content depth (12 sub-checks) |
| 4 | **Product/Service** | Description, prices in currency, fee disclosure, transparent process |
| 5 | **Checkout** | Final price, merchant location, T&C checkbox |
| 6 | **Receipt** | Electronic receipt / confirmation (manual verification) |
| 7 | **Update Notifications** | Customer notification process (manual verification) |
| 8 | **Mobile** | Responsive design |

### Scoring

- Total: **100 points** (weighted by section importance)
- **≥ 80** → ✅ COMPLIANT
- **50–79** → ⚠️ NEEDS_REVIEW
- **< 50** → ❌ NON-COMPLIANT

---

## Deployment (Railway)

1. Connect GitHub repository to Railway
2. Set environment variables:
   ```
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=<your-key>
   API_SECRET_KEY=<strong-secret-key>
   ALLOWED_ORIGINS=*
   ENVIRONMENT=production
   DATABASE_URL=<postgresql-url-from-railway>
   ```
3. Deploy — Dockerfile handles everything automatically
4. Database tables are created on first startup

---

## Project Structure

```
app/
├── api/
│   ├── compliance/router.py      # Web form endpoint (no auth)
│   ├── widget/router.py          # Legacy widget
│   └── v1/
│       ├── auth.py               # API key authentication
│       ├── rate_limiter.py       # 1/day per client
│       ├── compliance_router.py  # V1 compliance (auth + rate limit)
│       ├── policies_router.py    # Policy CRUD + generation
│       └── widget_router.py      # Widget JS serving
├── core/
│   └── config.py                 # Settings & env vars
├── infrastructure/
│   └── database.py               # SQLAlchemy async engine
├── modules/
│   ├── compliance/
│   │   ├── engine.py             # 30+ deterministic rules + dynamic analysis
│   │   ├── parser.py             # Checklist file parser (PDF/DOCX/TXT → rules)
│   │   └── schemas.py            # Pydantic models (incl. DynamicChecklistRule)
│   └── policies/
│       ├── models.py             # DB tables (4 models)
│       ├── generator.py          # Gemini policy generation
│       ├── service.py            # Legacy policy service
│       └── schemas.py            # Policy response schemas
├── services/
│   ├── crawler/service.py        # Playwright crawler
│   ├── llm/
│   │   ├── client.py             # LLM abstract base
│   │   ├── gemini_client.py      # Gemini 2.5 Flash
│   │   ├── mock_client.py        # Mock for testing
│   │   └── factory.py            # LLM provider factory
│   └── report/
│       └── docx_service.py       # DOCX report generator
├── static/                       # Frontend assets
├── templates/                    # Jinja2 HTML templates
└── main.py                       # FastAPI app + routing
```

---

## Integration with portal.nbcgate.com

The portal backend calls the V1 API server-to-server:

```javascript
// In portal's Next.js API route:
const API_BASE = 'https://ai-precheck.up.railway.app';
const API_KEY = process.env.AI_PRECHECK_API_KEY;

// 1. Run compliance check
const checkRes = await fetch(`${API_BASE}/api/v1/compliance/check`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${API_KEY}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    client_id: merchant.id,
    url: merchant.website_url,
    company_name: merchant.company_name,
  }),
});
const report = await checkRes.json();
// report.score, report.status, report.checklist, report.download_url

// 2. Generate missing policies
const policyRes = await fetch(`${API_BASE}/api/v1/policies/generate`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${API_KEY}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    client_id: merchant.id,
    company_name: merchant.company_name,
    legal_address: merchant.address,
    support_email: merchant.email,
    site_url: merchant.website_url,
    jurisdiction: 'CY',
    language: 'English',
    policies: ['privacy', 'refund', 'cancellation'],
  }),
});
const policies = await policyRes.json();

// 3. Approve a policy
await fetch(`${API_BASE}/api/v1/policies/${merchant.id}/${policies[0].id}/approve`, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${API_KEY}` },
});
```

---

## License

Internal use only — NBCgate / ECOMMBX.
