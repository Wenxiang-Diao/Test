# COMP9900 Sleep Monitoring Dashboard

## Quick Start

### 1. Conda environment

```bash
# Option A: create from environment.yml
conda env create -f environment.yml

# Option B: create manually
conda create -n comp9900 python=3.11 -y
conda activate comp9900
conda install -c conda-forge nodejs=20 -y
pip install -r backend/requirements.txt
```

### 2. Database

The English edition uses a **separate** PostgreSQL instance (isolated from `sprint1-zh`):

| Setting | Value |
|---|---|
| Port | **5434** |
| Database | `sleep_monitor_en` |
| Container | `comp9900-postgres-en` |

```bash
docker compose up -d
```

### 3. Backend

```bash
cd backend
pip install -r requirements.txt
python scripts/init_db.py
uvicorn app.main:app --reload --port 8001
```

API documentation: http://localhost:8001/docs

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Application URL: http://localhost:5174

**Default credentials**: `admin` / `admin123`

### Running both language versions

| Version | DB port | Backend | Frontend |
|---|---|---|---|
| sprint1-zh | 5433 | 8000 | 5173 |
| sprint1-en | 5434 | 8001 | 5174 |

Data is fully isolated; resetting one version does not affect the other.

## Project structure

See [DESIGN.md](./DESIGN.md) for architecture, API list, and database schema.
