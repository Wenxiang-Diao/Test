# Sprint 1 Delivery Package

This folder contains the complete **Sprint 1** delivery for the COMP9900 sleep monitoring project.

## Folder structure

```
sprint1-en/
├── README.md              # Quick start guide
├── SPRINT1.md             # This file — delivery package index
├── DESIGN.md              # System design document
├── IMPLEMENTATION.md      # Frontend/backend implemented features
├── docker-compose.yml     # PostgreSQL (port 5433)
├── environment.yml        # Conda environment definition
├── docs/                  # Proposal reference documents
│   ├── proposal_backend_section.md
│   ├── proposal_storyboard_section.md
│   ├── design.md          # Copy of DESIGN.md
│   └── proposal-reference.pdf
├── backend/               # FastAPI backend
└── frontend/              # React frontend
```

## Quick start

```bash
conda activate comp9900   # or: conda env create -f environment.yml
docker compose up -d
cd backend && pip install -r requirements.txt && python scripts/init_db.py && uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

- Frontend: http://localhost:5173
- Backend API docs: http://localhost:8000/docs
- Login: `admin` / `admin123`

## Sprint 1 delivery scope

This package ships a full-stack MVP beyond the original Sprint 1 API-only milestone:

| Area | Delivered |
|---|---|
| **Backend** | Auth, resident list, three CSV upload endpoints, dashboard, prediction, alerts, reports |
| **Frontend** | Login, Resident Overview, Resident Dashboard (5 sub-components), Alert Centre, Report pages |
| **Data** | Demo seed for residents R001, R002, R003 via `backend/scripts/init_db.py` |
| **Docs** | Design, implementation, and proposal reference materials |

For a feature-by-feature breakdown aligned with the design document, see [IMPLEMENTATION.md](./IMPLEMENTATION.md).

For architecture, API contracts, database schema, and sprint roadmap, see [DESIGN.md](./DESIGN.md).
