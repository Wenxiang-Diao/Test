# Sprint 1 交付包（中文版）

本文件夹为 **sprint1-zh**（中文 UI + 中文文档）。

## 目录结构

```
sprint1/
├── README.md              # 快速启动说明
├── DESIGN.md              # 系统设计文档
├── IMPLEMENTATION.md      # 前后端功能实现说明
├── docker-compose.yml     # PostgreSQL（端口 5433）
├── environment.yml        # Conda 环境配置
├── docs/                  # Proposal 相关文档
│   ├── proposal_backend_section.md
│   ├── proposal_storyboard_section.md
│   ├── design.md
│   └── proposal参考.pdf
├── backend/               # FastAPI 后端
└── frontend/              # React 前端
```

## 快速启动

```bash
conda activate comp9900   # 或 conda env create -f environment.yml
docker compose up -d
cd backend && pip install -r requirements.txt && python scripts/init_db.py && uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

- 前端：http://localhost:5173
- 后端文档：http://localhost:8000/docs
- 账号：`admin` / `admin123`

## Sprint 1 交付范围

- 认证 + 居民列表 API
- 三类 CSV 数据上传 API
- 看板 / 预测 / 告警 / 报告 API（MVP）
- 前端 5 页面 + 看板子组件
- 演示数据 seed 脚本

详见 [IMPLEMENTATION.md](./IMPLEMENTATION.md)。
