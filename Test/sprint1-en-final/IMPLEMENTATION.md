# COMP9900 Frontend & Backend — Implemented Features

> This document describes **implemented** frontend and backend functionality in the current codebase, cross-referenced against [DESIGN.md](./DESIGN.md).  
> Suitable for Sprint demos, proposal appendices, final reports, or team onboarding.

---

## 1. Document purpose

- Describe the actual backend API and business-logic delivery scope
- Describe the actual frontend pages and interactions
- Map features to the design document and note simplified or missing items

---

## 2. System overview

| Module | Stack | Status |
|---|---|---|
| Backend API | FastAPI + SQLAlchemy + PostgreSQL | ✅ Runnable |
| Frontend dashboard | React + TypeScript + Vite + Recharts | ✅ Runnable |
| Data ingestion | CSV upload (three types) | ✅ Implemented |
| Authentication | JWT Bearer token | ✅ Implemented (MVP mock) |
| Prediction | Rule + statistical feature engine | ✅ MVP implemented |
| Alerts | Six rule types | ✅ Implemented |
| Demo data | R001 / R002 / R003 + seed script | ✅ Implemented |

**Default access**

- Frontend: http://localhost:5173
- Backend docs: http://localhost:8000/docs
- Credentials: `admin` / `admin123`

---

## 3. Backend implemented features

### 3.1 Layered architecture

The backend follows the layered structure defined in the design document:

```
Router (Controller) → Service → Repository → PostgreSQL
                          ↓
                    Analytics Layer (prediction engine)
```

| Layer | Implemented content |
|---|---|
| **Router** | Six route groups: auth, residents, dashboard, upload, alerts, reports |
| **Service** | Seven services: resident, dashboard, baseline, ingestion, prediction, alerts, reports |
| **Repository** | Six repositories: residents, events, vitals, summaries, predictions, alerts |
| **Analytics** | `prediction_engine.py` — explainable rule-based prediction |

### 3.2 REST API catalogue

| Endpoint | Method | Status | Description |
|---|---|---|---|
| `/api/health` | GET | ✅ | Health check |
| `/api/auth/login` | POST | ✅ | Username/password login; returns JWT |
| `/api/residents` | GET | ✅ | Resident list with bed status, active alert count, risk level |
| `/api/residents/{id}/dashboard` | GET | ✅ | Dashboard summary: status, sleep summary, events, vitals, baseline |
| `/api/residents/{id}/prediction` | GET | ✅ | 15/30/60-minute bed-exit risk + `explanation` |
| `/api/residents/{id}/alerts` | GET | ✅ | Alert history for one resident |
| `/api/alerts` | GET | ✅ | Global alert list (Alert Centre) |
| `/api/alerts/{id}/acknowledge` | POST | ✅ | Acknowledge alert |
| `/api/upload/bed-events` | POST | ✅ | Upload bed in/out event CSV |
| `/api/upload/vitals` | POST | ✅ | Upload vital-sign CSV |
| `/api/upload/sleep-summary` | POST | ✅ | Upload daily sleep summary CSV |
| `/api/reports/{resident_id}` | GET | ✅ | Daily report + 7-day weekly trend |

### 3.3 Authentication and security

| Feature | Implementation |
|---|---|
| JWT auth | All endpoints except `/api/auth/login` and `/api/health` require Bearer token |
| Password storage | bcrypt hash |
| Unauthenticated access | Returns HTTP 401 |
| Input validation | All three CSV upload types validate field format and ranges |
| Resident ID validation | Upload rejects `resident_id` values not present in the database |

### 3.4 Data ingestion (IngestionService)

| Data type | Validation rules | Target table |
|---|---|---|
| Bed events | `bed_status` ∈ IN_BED / OUT_OF_BED / NO_PERSON; `activity_status` ∈ STATIC / ACTIVE; parseable timestamp | `bed_status_events` |
| Vital signs | Heart rate 30–200 bpm; breathing rate 5–40 breaths/min | `vital_sign_samples` |
| Sleep summary | Required `sleep_score`, efficiency, bed-exit count, etc. | `daily_sleep_summary` |

After a successful upload, alert rules are evaluated automatically.

### 3.5 Business services

#### ResidentService
- Aggregates each resident's **latest bed status**
- Counts **unacknowledged alerts** and **highest alert severity**
- Reads the **latest prediction** as the displayed risk level (`Low` / `Medium` / `High`)

#### DashboardService
- Reads from `daily_sleep_summary`: `sleep_score`, `total_sleep_minutes`, `sleep_efficiency`, `bed_exit_count`, `avg_heart_rate`, `avg_breathing_rate`
- Uses the latest `bed_status_events` row for current `bed_status` / `activity_status`
- Returns the last 12 hours of `bed_events` and `vital_samples` for charts
- Includes 7/30-day baseline comparison data

#### BaselineService
- Computes rolling **7-day** and **30-day** means per resident
- Outputs: sleep duration, efficiency, bed-exit count, heart/breathing rate means and ± standard deviation bands
- Shared by alert rules and the prediction engine

#### PredictionService + PredictionEngine
- Outputs probability and risk level for **15 / 30 / 60** minute windows
- Risk levels: **Low / Medium / High**
- Generates a readable `explanation` string
- Persists results to the `predictions` table
- **MVP implementation**: rule and statistical features; interface boundary ready for ML module swap

#### AlertRuleService
Six alert types implemented (aligned with the design document):

| Alert type | Trigger logic (simplified) |
|---|---|
| Prolonged out-of-bed | Currently OUT_OF_BED and duration exceeds 1.5× 30-day baseline |
| Abnormal bed-exit count | Tonight's `bed_exit_count` exceeds 1.5× 30-day mean |
| Sustained elevated heart rate | ≥3 readings in the last hour deviate from individual baseline |
| No person detected | `bed_status = NO_PERSON` during sleep hours |
| Low device confidence | Latest event `confidence < 0.5` |
| Poor device data quality | Multiple consecutive vital samples with `confidence < 0.5` |

Each alert includes: `alert_type`, `severity`, `reason`, `timestamp`, `suggested_action`.

#### ReportService
- **Daily report**: all sleep summary fields for a given date
- **Weekly report**: 7-day trends for sleep, efficiency, bed exits, and vitals, with 30-day baseline reference

### 3.6 Database

| Table | Purpose |
|---|---|
| `users` | Login users |
| `residents` | Residents (R001, R002, R003) |
| `devices` | Device bindings |
| `bed_status_events` | Bed in/out events |
| `vital_sign_samples` | Vital signs |
| `daily_sleep_summary` | Daily sleep aggregates |
| `predictions` | Prediction results |
| `alerts` | Alert records |

Init script: `backend/scripts/init_db.py` (supports `--reset` to rebuild demo data)

---

## 4. Frontend implemented features

### 4.1 Pages and routes

| Route | Page | Design reference |
|---|---|---|
| `/login` | Login Page | PROJ-1 |
| `/residents` | Resident Overview Page | PROJ-2, PROJ-15 |
| `/residents/:id/dashboard` | Resident Dashboard Page | PROJ-4, PROJ-6, PROJ-8 |
| `/alerts` | Alert Centre Page | PROJ-10, PROJ-11, PROJ-13 |
| `/reports/:residentId` | Report Page | PROJ-14, PROJ-16 |

All business pages are wrapped in `AppLayout` with top navigation and logout.

### 4.2 Page details

#### Login Page (`LoginPage`)
- Username / password form
- Invalid credentials show an inline error without navigation
- On success, JWT stored in `localStorage`; redirects to Resident Overview
- Displays non-medical-diagnosis disclaimer

#### Resident Overview Page (`ResidentOverviewPage`)
- Grid of cards for all residents
- Each card shows: name, bed status (colour badge), last updated, active alert count, risk level
- Filters: **All / Active Alerts / High Risk**
- Card click navigates to that resident's dashboard

#### Resident Dashboard Page (`ResidentDashboardPage`)
Two tabs:

**Tab 1 — Dashboard Overview**

| Component | Function |
|---|---|
| Status Card | Large bed-status colour block + `activity_status` + last updated |
| Sleep Summary Cards | Six sleep metric cards |
| Vital-sign Charts | Heart rate / breathing rate line charts with 30-day baseline band |
| History comparison | 7/30-day average sleep duration and bed-exit count |

**Tab 2 — Bed-exit Timeline & Prediction**

| Component | Function |
|---|---|
| Bed-exit Timeline | List of tonight's OUT_OF_BED events |
| Prediction Panel | 15/30/60-minute probability, risk level (`Low`/`Medium`/`High`), `explanation` |

In-page links to **View Report** and **Alert Centre**.

#### Alert Centre Page (`AlertCentrePage`)
- All-resident alert list, newest first
- Filters: **All / Unacknowledged / High / Medium / Low**
- Expandable detail: reason, suggested action
- **Acknowledge Alert** button calls the acknowledge API

#### Report Page (`ReportPage`)
- **Daily report**: eight sleep metric cards
- **Weekly report**: 7-day sleep duration line chart with 30-day baseline reference
- Disclaimer displayed

### 4.3 Frontend infrastructure

| Module | Description |
|---|---|
| `api/client.ts` | Axios wrapper; attaches JWT; 401 redirects to login |
| `utils/format.ts` | Bed status and risk level colour mapping; time formatting |
| Route guard | Unauthenticated access to business pages redirects to `/login` |
| Vite proxy | Dev environment proxies `/api` to `localhost:8000` |

---

## 5. Frontend–backend feature matrix

| Design feature | Backend | Frontend |
|---|---|---|
| User login | ✅ JWT | ✅ Login Page |
| Resident list | ✅ GET /api/residents | ✅ Overview cards |
| Current bed status | ✅ dashboard | ✅ Status Card |
| Six sleep summary metrics | ✅ dashboard | ✅ Sleep Summary Cards |
| Vital-sign trend charts | ✅ dashboard.vital_samples | ✅ Vital-sign Charts |
| 7/30-day baseline comparison | ✅ baseline | ✅ Dashboard history section |
| Bed-exit timeline | ✅ dashboard.bed_events | ✅ Bed-exit Timeline |
| Bed-exit risk prediction | ✅ prediction | ✅ Prediction Panel |
| Alert list and acknowledge | ✅ alerts API | ✅ Alert Centre Page |
| Daily / weekly reports | ✅ reports API | ✅ Report Page |
| CSV data upload | ✅ upload API | ⬜ No upload UI (use Swagger / Postman) |
| Non-medical disclaimer | ✅ in API responses | ✅ shown on pages |

---

## 6. Gaps vs design document / future work

Features described in the design document or proposal but simplified or without UI in the current build:

| Item | Current state | Notes |
|---|---|---|
| Prediction model | Rule engine MVP | Standardised API; ready for ML module swap |
| Authentication | Mock single user | Structure compatible with future auth |
| CSV upload UI | No frontend page | Backend endpoints complete; test via `/docs` |
| Mocked REST / real-time stream | Not implemented | Ingestion layer abstracted for future extension |
| PDF export | Not implemented | Report page UI only |
| WebSocket push | Not implemented | Design uses REST pull / on-demand queries |
| Multi-user roles | Not implemented | Single `admin` role only |

---

## 7. How to verify

```bash
conda activate comp9900
docker compose up -d

# Backend
cd backend && uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev
```

1. Open http://localhost:5173 and log in with `admin` / `admin123`
2. On Resident Overview, inspect R001 / R002 / R003 cards
3. Open R003 dashboard → expect active alerts; confirm in Alert Centre
4. Switch dashboard tabs to view charts and prediction panel
5. On Report page, switch between daily and weekly views
6. API testing: http://localhost:8000/docs

Reset demo data:

```bash
python backend/scripts/init_db.py --reset
```

---

## 8. Document maintenance

Update this document when:

- Sprint 2 integrates a real ML prediction module → update §3.5 PredictionService
- Frontend adds a CSV upload page → update §4 and §5 matrix
- New user roles or WebSocket support is added → update §6 gaps

---

*Last updated: aligned with the current codebase (Sprint 1–3 full-stack MVP)*
