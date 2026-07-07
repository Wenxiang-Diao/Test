# COMP9900 睡眠监测仪表盘 — 系统设计文档

> 整合自 `proposal_backend_section.md`、`proposal_storyboard_section.md`、`design.md` 及 `proposal参考.pdf`

---

## 1. 项目概述

面向护理人员与家属的**决策支持原型**，处理睡眠监测设备三类数据：

| 数据类型 | 核心字段 |
|---|---|
| 离床/在床事件 | `resident_id`, `timestamp`, `bed_status`, `activity_status`, `confidence` |
| 生命体征样本 | `resident_id`, `timestamp`, `heart_rate_bpm`, `breathing_rate_per_min`, `confidence` |
| 每日睡眠摘要 | `date`, `sleep_score`, `total_sleep_minutes`, `sleep_efficiency`, `bed_exit_count`, `avg_heart_rate`, `avg_breathing_rate` 等 |

MVP 通过 **CSV 上传** 接入数据，后续可切换为模拟 REST API 或实时流，下游逻辑不变。

---

## 2. 技术栈

| 层级 | 技术 | 职责 |
|---|---|---|
| 前端 | React + TypeScript + Vite | 仪表盘、图表、告警、报告 |
| 后端 | Python FastAPI | API、业务逻辑、告警、预测封装 |
| 数据库 | PostgreSQL 16 | 持久化存储 |
| 分析 | Pandas / NumPy / scikit-learn | 基线计算、规则预测、告警引擎 |
| 环境 | Conda `comp9900` | Python 依赖隔离 |

---

## 3. 系统架构

### 3.1 两条数据流

1. **数据接入流**：CSV/模拟 API → 校验/解析/清洗 → Repository → PostgreSQL
2. **前端请求流**：React → Controller → Service → Repository → PostgreSQL → 原路返回

数据库不直接推送前端，所有读取经 Service 层中转。

### 3.2 后端分层

```
Controller（HTTP 路由、认证、入参校验）
    ↓
Service（业务逻辑、跨模块编排）
    ↓
Repository（SQL 读写）
    ↓
PostgreSQL

Analytics Layer（基线、预测、告警规则）← Service 边界调用
```

| 分层 | 职责 |
|---|---|
| Controller | 路由分发、认证检查、状态码 |
| Service | 看板聚合、基线、告警、预测、报告 |
| Repository | 纯 SQL，无业务判断 |
| Analytics | 特征提取、概率预测、规则引擎 |

### 3.3 前端页面结构

```
App Layout
├── LoginPage
├── ResidentOverviewPage      ← GET /api/residents
├── ResidentDashboardPage     ← GET /api/residents/{id}/dashboard
│   ├── StatusCard
│   ├── SleepSummaryCards
│   ├── BedExitTimeline
│   ├── VitalSignCharts
│   └── PredictionPanel       ← GET /api/residents/{id}/prediction
├── AlertCentrePage           ← GET alerts + POST acknowledge
└── ReportPage                ← GET /api/reports/{resident_id}
```

---

## 4. 数据库 Schema

| 表 | 说明 |
|---|---|
| `residents` | 居民（R001、R002…，去标识化） |
| `devices` | 设备与居民绑定 |
| `bed_status_events` | 离床/在床事件 |
| `vital_sign_samples` | 心率、呼吸率样本 |
| `daily_sleep_summary` | 每日睡眠摘要 |
| `predictions` | 预测结果持久化 |
| `alerts` | 告警记录（含 acknowledged 状态） |
| `users` | 登录用户（MVP mock auth） |

---

## 5. REST API 清单

| 接口 | 方法 | Sprint | 说明 |
|---|---|---|---|
| `/api/auth/login` | POST | 1 | 用户登录 |
| `/api/residents` | GET | 1 | 居民列表（含状态、告警数、风险） |
| `/api/upload/bed-events` | POST | 1 | 上传离床事件 CSV |
| `/api/upload/vitals` | POST | 1 | 上传生命体征 CSV |
| `/api/upload/sleep-summary` | POST | 1 | 上传睡眠摘要 CSV |
| `/api/residents/{id}/dashboard` | GET | 2 | 看板汇总数据 |
| `/api/residents/{id}/prediction` | GET | 2 | 离床风险预测 |
| `/api/residents/{id}/alerts` | GET | 2 | 居民告警历史 |
| `/api/alerts` | GET | 2 | 全局告警列表 |
| `/api/alerts/{id}/acknowledge` | POST | 2 | 确认告警 |
| `/api/reports/{resident_id}` | GET | 3 | 日报/周报 |

### 关键响应格式

**预测** `{ probability, risk_level, windows: [{minutes, probability, risk_level}], explanation }`

**告警** `{ alert_type, severity, reason, timestamp, suggested_action, acknowledged }`

---

## 6. 业务规则摘要

### 6.1 基线服务
- 按居民计算近 **7 天** 和 **30 天** 滚动均值
- 用于告警阈值与预测特征，非固定群体标准

### 6.2 告警规则（六类）
1. 离床持续时间超出基线
2. 30 天内离床次数异常增加
3. 心率/呼吸率持续偏离个体范围
4. 睡眠期间未检测到人员
5. 设备置信度过低（`confidence < 0.5`）
6. 高 bed-exit 预测风险

### 6.3 预测模块
- 15 / 30 / 60 分钟窗口概率
- 风险等级：低 / 中 / 高
- 必须包含可读 `explanation`

---

## 7. 安全与伦理

- 看板/告警/预测接口需登录（401 未认证）
- 上传数据严格校验字段格式
- 演示数据匿名（R001…），不含 PII
- 前端展示「非医疗诊断」免责声明
- 原型仅为决策支持，不可替代临床判断

---

## 8. 本地开发

```bash
# 1. Conda 环境
conda activate comp9900

# 2. 数据库
docker compose up -d

# 3. 后端
cd backend && pip install -r requirements.txt
python scripts/init_db.py      # 建表 + seed
uvicorn app.main:app --reload --port 8000

# 4. 前端
cd frontend && npm install && npm run dev
```

- 后端文档：http://localhost:8000/docs
- 前端：http://localhost:5173
- 默认账号：`admin` / `admin123`

---

## 9. 目录结构

```
9900/
├── DESIGN.md                 # 本文档
├── docker-compose.yml
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── analytics/
│   │   └── routers/
│   ├── scripts/
│   │   ├── init_db.py
│   │   └── seed_data.py
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/
│       ├── components/
│       └── api/
└── data/sample/              # 示例 CSV
```

---

## 10. Sprint 交付顺序

| Sprint | 后端 | 前端 |
|---|---|---|
| 1 | Auth + Upload + Residents | Login + Overview |
| 2 | Dashboard + Prediction + Alerts | Dashboard 五组件 + Alert Centre |
| 3 | Reports + 聚合优化 | Report 页 + 筛选增强 |
