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

## 5. Result of MVP

## 5.1 Baseline rules + Logistic Regression

### Original

current rules + balanced class weight + 0.70 logistic / 0.30 rule + threshold 0.35

| Window | PR-AUC | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|
| 15 | 0.4832 | 0.2000 | 1.0000 | 0.3333 | 5 | 20 | 0 |
| 30 | 0.3452 | 0.3333 | 1.0000 | 0.5000 | 8 | 16 | 0 |
| 60 | 0.7106 | 0.5600 | 1.0000 | 0.7179 | 14 | 11 | 0 |

### Best PR-AUC

| Window | Rule | Weight | Blend | Threshold | PR-AUC | Precision | Recall | F1 | TP | FP | FN |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 15 | current | none | 0.85 | 0.35 | 0.6033 | 0.4000 | 0.8000 | 0.5333 | 4 | 6 | 1 |
| 30 | stable_protect | none | 1.00 | 0.35 | 0.3757 | 0.2941 | 0.6250 | 0.4000 | 5 | 12 | 3 |
| 60 | current | balanced | 0.85 | 0.45 | 0.7908 | 0.6087 | 1.0000 | 0.7568 | 14 | 9 | 0 |

### Best F1
| Window | Rule | Weight | Blend | Threshold | PR-AUC | Precision | Recall | F1 | TP | FP | FN |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 15 | current | none | 0.70 | 0.45 | 0.5769 | 0.5000 | 0.8000 | 0.6154 | 4 | 4 | 1 |
| 30 | current | none | 0.70 | 0.35 | 0.3597 | 0.3478 | 1.0000 | 0.5161 | 8 | 15 | 0 |
| 60 | current | none | 1.00 | 0.35 | 0.6407 | 0.6087 | 1.0000 | 0.7568 | 14 | 9 | 0 |

## 5.2 XGBOOST
Train samples: 269, Validation samples: 107

| Window | PR-AUC | Recall | F1 |
|---|---:|---:|---:|
| 15 | 0.72 | 0.8 | 0.3333 |
| 30 | 0.7345 | 0.875 | 0.4828 |
| 60 | 0.7106 | 0.9286 | 0.7027 |

