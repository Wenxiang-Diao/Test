# COMP9900 睡眠监测仪表盘

## 快速启动

### 1. Conda 环境

```bash
# 方式 A：从 environment.yml 一键创建
conda env create -f environment.yml

# 方式 B：手动创建
conda create -n comp9900 python=3.11 -y
conda activate comp9900
conda install -c conda-forge nodejs=20 -y
pip install -r backend/requirements.txt
```

### 2. 数据库

中文版使用独立 PostgreSQL 实例（与 `sprint1-en` 互不干扰）：

| 项目 | 值 |
|---|---|
| 端口 | **5433** |
| 数据库名 | `sleep_monitor` |
| 容器名 | `comp9900-postgres-zh` |

```bash
docker compose up -d
```

### 3. 后端

```bash
cd backend
pip install -r requirements.txt
python scripts/init_db.py
uvicorn app.main:app --reload --port 8000
```

API 文档：http://localhost:8000/docs

### 4. 前端

```bash
cd frontend
npm install
npm run dev
```

访问：http://localhost:5173

**默认账号**：`admin` / `admin123`

### 与英文版同时运行

| 版本 | 数据库端口 | 后端 | 前端 |
|---|---|---|---|
| sprint1-zh | 5433 | 8000 | 5173 |
| sprint1-en | 5434 | 8001 | 5174 |

两个版本数据完全独立，互不影响。

## 项目结构

详见 [DESIGN.md](./DESIGN.md)
