# Customer Requirement Implementation Log

Date: 2026-07-06

Scope: Customer email additions for resident management and resident basic location information. Implemented in the assessment-facing English app under `Test/sprint1-en-final`.

## 1. Resident Management and Dashboard

Requirement: support customised resident management, resident registration, key care-related information, adding residents, deleting resident records when appropriate, and managing transfers while retaining historical records and pausing active monitoring.

Implemented changes:

- Backend resident model extended in `sprint1-en-final/backend/app/models/models.py`.
  - Added `medical_history`, `daily_habits`, `care_notes`, `monitoring_status`, `transfer_destination`, and `transfer_date`.
- Backend schemas extended in `sprint1-en-final/backend/app/schemas/schemas.py`.
  - Added `ResidentCreate`, `ResidentUpdate`, `ResidentTransferRequest`, and `ResidentDetail`.
- Backend repository/service/router support added in:
  - `sprint1-en-final/backend/app/repositories/repositories.py`
  - `sprint1-en-final/backend/app/services/resident_services.py`
  - `sprint1-en-final/backend/app/routers/residents.py`
- New API functionality:
  - `GET /api/residents/manage`: list active residents for management.
  - `POST /api/residents`: register a new resident.
  - `GET /api/residents/{resident_id}`: view resident profile.
  - `PUT /api/residents/{resident_id}`: update resident profile, habits, care notes, status, and location.
  - `POST /api/residents/{resident_id}/transfer`: record transfer destination/date and set monitoring status to `PAUSED`.
  - `DELETE /api/residents/{resident_id}`: soft-delete resident by setting status to `DELETED`; historical events, vitals, summaries, predictions, and alerts remain in the database.
- Frontend management page added in `sprint1-en-final/frontend/src/pages/ResidentManagementPage.tsx`.
  - Staff can register residents, edit care-related details, update monitoring status, transfer residents, and soft-delete active records.
- Frontend route/nav/API client updated in:
  - `sprint1-en-final/frontend/src/App.tsx`
  - `sprint1-en-final/frontend/src/layouts/AppLayout.tsx`
  - `sprint1-en-final/frontend/src/api/client.ts`

Verification:

- Backend syntax check passed with `python -m compileall backend\app backend\scripts`.
- Full frontend TypeScript build could not be run because neither local `node_modules` nor the bundled Node package directory contains TypeScript/Vite CLI packages.

## 2. Resident Basic Location Information

Requirement: staff can record and manage room number, building/location, floor level, and other relevant facility details.

Implemented changes:

- Backend resident model extended in `sprint1-en-final/backend/app/models/models.py`.
  - Added `room_number`, `building`, `floor_level`, and `location_notes`.
- Demo seed data updated in `sprint1-en-final/backend/scripts/init_db.py`.
  - Residents R001, R002, and R003 now include building, floor, room, care notes, medical history, and daily habits.
  - Added `ensure_resident_profile_columns()` so running `python backend/scripts/init_db.py` can add the new resident profile/location columns to an already-created PostgreSQL `residents` table without requiring a full reset.
- Dashboard response extended in:
  - `sprint1-en-final/backend/app/schemas/schemas.py`
  - `sprint1-en-final/backend/app/services/resident_services.py`
- Frontend display updated in:
  - `sprint1-en-final/frontend/src/pages/ResidentOverviewPage.tsx`: overview cards now show location and monitoring status.
  - `sprint1-en-final/frontend/src/components/StatusCard.tsx`: dashboard status card now shows monitoring status and location.
  - `sprint1-en-final/frontend/src/pages/ResidentManagementPage.tsx`: staff can edit building, floor, room, and location notes.

Notes:

- The implementation uses soft delete rather than hard delete to preserve historical monitoring records, matching the transfer/history-retention requirement.
- Existing prediction, alert, dashboard, and report endpoints continue to work against the same resident IDs.
