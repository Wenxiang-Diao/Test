# COMP9900 Sleep Monitoring Dashboard / 睡眠监测仪表盘

**Team W17BBR · Bread**

Web-based sleep-monitoring analytics and alerting prototype for aged-care staff and family members.  
面向护理人员与家属的 Web 睡眠监测分析与告警原型。

> **Disclaimer / 免责声明**  
> System output is for care decision support only and is not a medical diagnosis.  
> 本系统输出仅供护理决策参考，不构成医疗诊断。

---

## Repository Overview / 仓库说明

This repository contains **Sprint 1** deliverables in two language editions. Each edition is a self-contained full-stack app (FastAPI + React + PostgreSQL) with **isolated database ports** so both can run on one machine.

本仓库包含 **Sprint 1** 的两个语言版本。每个版本均为独立全栈应用（FastAPI + React + PostgreSQL），使用**不同数据库端口**，可在同一台机器并行运行。

| Directory | UI language | PostgreSQL | Backend | Frontend | Setup guide |
|-----------|-------------|------------|---------|----------|-------------|
| [`sprint1-en-final/`](./sprint1-en-final/) | English | **5434** (`sleep_monitor_en`) | **8001** | **5174** | [README](./sprint1-en-final/README.md) |
| [`sprint1-zh-final/`](./sprint1-zh-final/) | 中文 | **5433** (`sleep_monitor`) | **8000** | **5173** | [README](./sprint1-zh-final/README.md) |

**For assessment / 供评分使用：** start from **`sprint1-en-final/`** (English UI).  
**For Chinese demo / 中文演示：** use **`sprint1-zh-final/`**.

---

## Sprint 1 Features / Sprint 1 功能

- Secure login (JWT) / 安全登录（JWT）
- Resident overview with filters / 居民总览与筛选
- CSV upload (bed events, vitals, sleep summary) / CSV 数据上传
- Resident sleep dashboard / 居民睡眠看板
- Bed-exit timeline & risk prediction / 离床时间线与风险预测
- Alert centre with acknowledgement / 告警中心与确认
- Daily & weekly sleep reports / 日/周睡眠报告
- Personalised 7-day / 30-day baselines / 个性化 7/30 天基线对比
- Device confidence display on dashboard / 看板设备置信度展示

---

## Quick Start (minimal) / 快速启动（概要）

Choose one edition, then follow its folder README for full steps.  
选择一个版本，完整步骤见对应子目录 README。

```bash
conda env create -f environment.yml   # run inside chosen sprint folder / 在选定目录内执行
conda activate comp9900
docker compose up -d                  # PostgreSQL
cd backend && pip install -r requirements.txt && python scripts/init_db.py
uvicorn app.main:app --reload --port <8000|8001>
cd frontend && npm install && npm run dev
```

**Demo credentials / 演示账号:** `admin` / `admin123`

---

## Documentation / 文档索引

| Path | Description |
|------|-------------|
| `sprint1-*/DESIGN.md` | Architecture, API, database schema / 架构、API、数据库 |
| `sprint1-*/IMPLEMENTATION.md` | Implementation notes / 实现说明 |
| `sprint1-*/SPRINT1.md` | Sprint 1 scope / Sprint 1 范围 |
| `sprint1-*/docs/` | Design reference copies / 设计参考文档 |

OpenAPI (after backend starts): `http://localhost:8000/docs` (zh) or `http://localhost:8001/docs` (en).

---

## Tech Stack / 技术栈

- **Backend:** Python 3.11, FastAPI, SQLAlchemy, PostgreSQL  
- **Frontend:** React, TypeScript, Vite, Recharts  
- **Data (MVP):** CSV upload + seeded demo data (R001–R003)

---

## GitHub

Course repository: [capstone-project-9900-w17b-bread](https://github.com/unsw-cse-comp99-3900/capstone-project-9900-w17b-bread)
