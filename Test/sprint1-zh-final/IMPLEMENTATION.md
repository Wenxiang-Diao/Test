# COMP9900 前后端功能实现说明

> 本文档描述当前代码库中**已实现**的前后端功能，与 [DESIGN.md](./DESIGN.md) 中的设计目标对照。  
> 适用于 Sprint 汇报、Proposal 附录、Final Report 或团队 onboarding。

---

## 1. 文档目的

- 说明后端 API 与业务逻辑的实际交付范围
- 说明前端页面与交互的实际交付范围
- 标注与设计文档的对应关系，以及尚未实现或简化的部分

---

## 2. 系统总览

| 模块 | 技术栈 | 当前状态 |
|---|---|---|
| 后端 API | FastAPI + SQLAlchemy + PostgreSQL | ✅ 可运行 |
| 前端仪表盘 | React + TypeScript + Vite + Recharts | ✅ 可运行 |
| 数据接入 | CSV 上传（三类） | ✅ 已实现 |
| 认证 | JWT Bearer Token | ✅ 已实现（MVP mock） |
| 预测模块 | 规则 + 统计特征引擎 | ✅ MVP 已实现 |
| 告警模块 | 六类规则引擎 | ✅ 已实现 |
| 演示数据 | R001 / R002 / R003 + seed 脚本 | ✅ 已实现 |

**默认访问**

- 前端：http://localhost:5173
- 后端文档：http://localhost:8000/docs
- 账号：`admin` / `admin123`

---

## 3. 后端已实现功能

### 3.1 架构分层

后端按设计文档采用分层结构：

```
Router (Controller) → Service → Repository → PostgreSQL
                          ↓
                    Analytics Layer（预测引擎）
```

| 层级 | 已实现内容 |
|---|---|
| **Router** | 认证、居民、看板、上传、告警、报告 6 组路由 |
| **Service** | 居民聚合、看板、基线、接入、预测、告警、报告 7 个服务 |
| **Repository** | 居民、事件、体征、摘要、预测、告警 6 个仓储 |
| **Analytics** | `prediction_engine.py` 可解释规则预测 |

### 3.2 REST API 清单

| 接口 | 方法 | 实现状态 | 功能说明 |
|---|---|---|---|
| `/api/health` | GET | ✅ | 健康检查 |
| `/api/auth/login` | POST | ✅ | 用户名密码登录，返回 JWT |
| `/api/residents` | GET | ✅ | 居民列表，含床位状态、活跃告警数、风险等级 |
| `/api/residents/{id}/dashboard` | GET | ✅ | 看板汇总：状态、睡眠摘要、事件、体征、基线 |
| `/api/residents/{id}/prediction` | GET | ✅ | 15/30/60 分钟离床风险预测 + explanation |
| `/api/residents/{id}/alerts` | GET | ✅ | 单个居民的告警历史 |
| `/api/alerts` | GET | ✅ | 全局告警列表（告警中心用） |
| `/api/alerts/{id}/acknowledge` | POST | ✅ | 确认告警 |
| `/api/upload/bed-events` | POST | ✅ | 上传离床/在床事件 CSV |
| `/api/upload/vitals` | POST | ✅ | 上传生命体征 CSV |
| `/api/upload/sleep-summary` | POST | ✅ | 上传每日睡眠摘要 CSV |
| `/api/reports/{resident_id}` | GET | ✅ | 日报 + 近 7 天周报趋势 |

### 3.3 认证与安全

| 功能 | 实现说明 |
|---|---|
| JWT 认证 | 除 `/api/auth/login` 和 `/api/health` 外，其余接口需 Bearer Token |
| 密码存储 | bcrypt 哈希 |
| 未认证访问 | 返回 HTTP 401 |
| 输入校验 | 三类 CSV 上传均有字段格式与范围校验 |
| 居民 ID 校验 | 上传时校验 `resident_id` 必须存在于数据库 |

### 3.4 数据接入（IngestionService）

| 数据类型 | 校验规则 | 写入表 |
|---|---|---|
| 离床事件 | `bed_status` ∈ IN_BED/OUT_OF_BED/NO_PERSON；`activity_status` ∈ STATIC/ACTIVE；timestamp 可解析 | `bed_status_events` |
| 生命体征 | 心率 30–200 bpm；呼吸率 5–40 次/分 | `vital_sign_samples` |
| 睡眠摘要 | 必填 sleep_score、效率、离床次数等 | `daily_sleep_summary` |

上传成功后自动触发告警规则评估。

### 3.5 业务服务

#### 居民服务（ResidentService）
- 聚合每位居民的**最新床位状态**
- 统计**未确认告警数量**与**最高告警等级**
- 读取**最新预测结果**作为风险等级展示

#### 看板服务（DashboardService）
- 从 `daily_sleep_summary` 读取：sleep_score、total_sleep_minutes、sleep_efficiency、bed_exit_count、avg_heart_rate、avg_breathing_rate
- 从 `bed_status_events` 取最新记录作为当前 bed_status / activity_status
- 返回近 12 小时 bed_events 与 vital_samples 供前端图表使用
- 附带 7/30 天基线对比数据

#### 基线服务（BaselineService）
- 按居民计算近 **7 天** 与 **30 天** 滚动均值
- 输出：睡眠时长、效率、离床次数、心率/呼吸率均值及 ± 标准差区间
- 供告警规则与预测引擎共用

#### 预测服务（PredictionService + PredictionEngine）
- 输出 15 / 30 / 60 分钟三个时间窗口的概率与风险等级（低/中/高）
- 生成可读 `explanation` 字符串
- 结果持久化到 `predictions` 表
- **MVP 实现**：基于规则与统计特征，接口边界已预留，可替换为 Wenxiang 的 ML 模块

#### 告警规则服务（AlertRuleService）
已实现六类告警（与设计文档对应）：

| 告警类型 | 触发逻辑（简化描述） |
|---|---|
| 离床时间过长 | 当前 OUT_OF_BED 且持续时间超过 30 天基线 1.5 倍 |
| 离床次数异常 | 当晚 bed_exit_count 超过 30 天均值 1.5 倍 |
| 心率持续偏高 | 近 1 小时内 ≥3 条读数偏离个体基线 |
| 未检测到人员 | 睡眠时段 bed_status = NO_PERSON |
| 设备置信度低 | 最新事件 confidence < 0.5 |
| 设备数据质量 | 连续多条体征 confidence < 0.5 |

每条告警包含：`alert_type`、`severity`、`reason`、`timestamp`、`suggested_action`。

#### 报告服务（ReportService）
- **日报**：指定日期睡眠摘要全字段
- **周报**：近 7 天 sleep / efficiency / bed_exit / 体征趋势，含 30 天基线参考

### 3.6 数据库

| 表 | 用途 |
|---|---|
| `users` | 登录用户 |
| `residents` | 居民（R001、R002、R003） |
| `devices` | 设备绑定 |
| `bed_status_events` | 离床/在床事件 |
| `vital_sign_samples` | 生命体征 |
| `daily_sleep_summary` | 每日睡眠摘要 |
| `predictions` | 预测结果 |
| `alerts` | 告警记录 |

初始化脚本：`backend/scripts/init_db.py`（支持 `--reset` 重建演示数据）

---

## 4. 前端已实现功能

### 4.1 页面与路由

| 路由 | 页面 | 对应用户故事 / 设计 |
|---|---|---|
| `/login` | 登录页 | PROJ-1 |
| `/residents` | 居民总览页 | PROJ-2、PROJ-15 |
| `/residents/:id/dashboard` | 居民看板页 | PROJ-4、PROJ-6、PROJ-8 |
| `/alerts` | 告警中心 | PROJ-10、PROJ-11、PROJ-13 |
| `/reports/:residentId` | 报告页 | PROJ-14、PROJ-16 |

所有业务页面包裹在 `AppLayout` 中，含顶栏导航与退出登录。

### 4.2 各页面功能详情

#### 登录页（LoginPage）
- 用户名 / 密码表单
- 错误凭据原地提示，不跳转
- 成功后写入 JWT 至 localStorage，跳转居民总览
- 展示「非医疗诊断」免责声明

#### 居民总览页（ResidentOverviewPage）
- 网格卡片展示所有居民
- 每张卡片显示：姓名、床位状态（色块）、最后更新时间、活跃告警数、风险等级
- 筛选：**全部 / 有活跃告警 / 高风险**
- 点击卡片进入该居民看板

#### 居民看板页（ResidentDashboardPage）
两个 Tab：

**Tab 1：看板概览**
| 组件 | 功能 |
|---|---|
| StatusCard | 当前 bed_status 大色块 + activity_status + 最后更新时间 |
| SleepSummaryCards | 六项睡眠指标卡片 |
| VitalSignCharts | 心率 / 呼吸率折线图，叠加 30 天基线区间 |
| 历史对比区 | 7/30 天睡眠时长与离床次数均值 |

**Tab 2：离床时间线与预测**
| 组件 | 功能 |
|---|---|
| BedExitTimeline | 今晚 OUT_OF_BED 事件列表 |
| PredictionPanel | 15/30/60 分钟概率、风险等级、explanation |

页内可跳转「查看报告」和「告警中心」。

#### 告警中心（AlertCentrePage）
- 全部居民告警列表，按时间倒序
- 筛选：全部 / 未确认 / 高 / 中 / 低
- 点击告警展开详情：原因、建议操作
- 「确认告警」按钮，调用 acknowledge API

#### 报告页（ReportPage）
- **日报**：八项睡眠指标卡片
- **周报**：近 7 天睡眠时长折线图 + 30 天基线参考线
- 免责声明

### 4.3 前端基础设施

| 模块 | 说明 |
|---|---|
| `api/client.ts` | Axios 封装，自动附加 JWT，401 跳转登录 |
| `utils/format.ts` | 床位状态、风险等级颜色映射与时间格式化 |
| 路由守卫 | 未登录访问业务页自动重定向 `/login` |
| Vite 代理 | 开发环境 `/api` 代理至 `localhost:8000` |

---

## 5. 前后端功能对照表

| 设计功能 | 后端 | 前端 |
|---|---|---|
| 用户登录 | ✅ JWT | ✅ 登录页 |
| 居民列表 | ✅ GET /residents | ✅ 总览卡片 |
| 当前床位状态 | ✅ dashboard | ✅ StatusCard |
| 睡眠摘要六指标 | ✅ dashboard | ✅ SleepSummaryCards |
| 生命体征趋势图 | ✅ dashboard.vital_samples | ✅ VitalSignCharts |
| 7/30 天基线对比 | ✅ baseline | ✅ 看板历史对比区 |
| 离床时间线 | ✅ dashboard.bed_events | ✅ BedExitTimeline |
| 离床风险预测 | ✅ prediction | ✅ PredictionPanel |
| 告警列表与确认 | ✅ alerts API | ✅ AlertCentrePage |
| 日报 / 周报 | ✅ reports API | ✅ ReportPage |
| CSV 数据上传 | ✅ upload API | ⬜ 暂无上传 UI（可用 Swagger/Postman） |
| 非医疗诊断声明 | ✅ 响应含 disclaimer | ✅ 各页展示 |

---

## 6. 与设计文档的差异 / 待扩展项

以下功能在设计文档或 PDF 中有描述，但当前实现为 **简化版或未做 UI**：

| 项目 | 当前状态 | 说明 |
|---|---|---|
| 预测模型 | 规则引擎 MVP | 接口已标准化，可替换 Wenxiang ML 模块 |
| 认证 | mock 单用户 | 结构兼容后续正式 auth |
| CSV 上传 UI | 未做前端页面 | 后端接口完整，可通过 `/docs` 测试 |
| 模拟 REST / 实时流 | 未实现 | 接入层已抽象，后续可扩展 |
| PDF 导出 | 未实现 | 报告页仅有 UI 占位设计 |
| WebSocket 推送 | 未实现 | 设计选用 REST 轮询/按需查询 |
| 多用户角色 | 未实现 | 当前仅 admin 一种角色 |

---

## 7. 如何验证功能

```bash
conda activate comp9900
docker compose up -d

# 后端
cd backend && uvicorn app.main:app --reload --port 8000

# 前端
cd frontend && npm run dev
```

1. 浏览器打开 http://localhost:5173 ，登录 `admin` / `admin123`
2. 总览页查看 R001/R002/R003 三种状态
3. 进入 R003 看板 → 应有告警；进入告警中心可确认
4. 看板 Tab 切换查看图表与预测
5. 报告页切换日报/周报
6. API 详细测试：http://localhost:8000/docs

重置演示数据：

```bash
python backend/scripts/init_db.py --reset
```

---

## 8. 文档维护建议

建议在以下节点更新本文档：

- Sprint 2 接入真实 ML 预测模块后 → 更新 §3.5 预测服务
- 前端补上 CSV 上传页后 → 更新 §4 与 §5 对照表
- 新增用户角色或 WebSocket 后 → 更新 §6 待扩展项

---

*最后更新：与当前代码库同步（Sprint 1–3 MVP 全栈可运行版本）*
