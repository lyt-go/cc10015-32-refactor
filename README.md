# 多维分析实验平台

面向实验设计、指标计算、样本分析、效果评估与结论发布的数据分析实验平台。

这是一个前后端分离的管理平台：前端 Vue 3 + Vite + TypeScript，后端 FastAPI（Python）。
两边各自独立启动，前端 dev server 已关掉自动打开页面，启动后按终端打印的地址手工打开。

## 目录结构

```text
.
├── frontend/                 Vue 3 + Vite + TypeScript 前端
│   ├── src/views/            每个业务模块一个页面
│   ├── src/api/              统一请求封装
│   ├── src/stores/           会话与筛选状态
│   └── vite.config.ts        dev server 配置（open: false）
├── backend/                  FastAPI（Python） 后端
│   ├── app/routers/          每个业务模块一组接口
│   ├── app/services/         业务规则与状态流转
│   └── app/store.py          内存数据仓库与示例数据
├── .gitignore
└── docker-compose.yml
```

## 启动

### 后端

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
./run.sh
```

健康检查：`curl http://127.0.0.1:8000/api/health`

### 前端

```bash
cd frontend
npm ci
npm run dev
```

前端默认监听 `http://127.0.0.1:5173/`，dev server 不会自动打开浏览器，
需要自己访问。`/api` 由 vite 代理到后端 `http://127.0.0.1:8000`。

## 业务模块

| 模块 | 目录 | 业务对象 | 主要字段 |
| --- | --- | --- | --- |
| 实验设计 | `experiment` | 实验方案 | 方案编号、实验名称、对照组说明 |
| 样本分群 | `sample_group` | 样本分群 | 分群编号、分群名称、筛选条件 |
| 指标定义 | `metric_def` | 指标定义 | 指标编号、指标名称、计算公式 |
| AB结果分析 | `ab_result` | 分析报告 | 报告编号、实验编号、分析指标 |
| 分群对比 | `segment_compare` | 对比任务 | 任务编号、分群A、分群B |
| 多维下钻 | `drill_down` | 下钻维度 | 维度编号、维度名称、下钻层级 |
| 数据筛选 | `data_filter` | 筛选规则 | 规则编号、数据来源、筛选字段 |
| 归因分析 | `attr_analysis` | 归因任务 | 任务编号、目标指标、候选因子 |
| 异常检测 | `anomaly_detect` | 检测规则 | 规则编号、监控指标、检测算法 |
| 预测模型 | `forecast_model` | 模型配置 | 模型编号、预测对象、历史窗口 |
| 数据导出 | `data_export` | 导出任务 | 任务编号、数据来源、导出格式 |
| 同期群追踪 | `cohort_track` | 同期群定义 | 群组编号、群组名称、首次行为 |
| 可视化配置 | `chart_config` | 图表配置 | 图表编号、图表类型、数据来源 |
| 洞察报告 | `insight_report` | 洞察报告 | 报告编号、分析主题、数据来源 |
| 数据新鲜度 | `data_freshness` | 新鲜度监控 | 监控编号、数据表名、最新分区 |
| 口径注册 | `metric_alias` | 口径版本 | 版本编号、指标编号、变更说明 |
| 实验因子 | `expr_factor` | 因子配置 | 因子编号、因子名称、因子层级 |
| 评估看板 | `evaluate_board` | 看板配置 | 看板编号、看板名称、关联实验 |

## 约定

- 每个模块的前端页面在 `frontend/src/views/<模块>/index.vue`，后端接口在
  `backend/app/routers/<模块>.py`，业务规则在 `backend/app/services/<模块>.py`。
- 列表接口统一返回 `{ items, total, page, size }`，动作接口统一返回 `{ ok, message }`。
- 状态流转只允许在 `app/services` 里改，路由层不做业务判断。

## 留存矩阵与洞察结论

同期群追踪与洞察报告共用一条留存计算路径，周期窗口与指标口径只维护一处：

| 位置 | 作用 |
| --- | --- |
| `app/retention_core.py` | 纯计算：成员边界、周期窗口、`RET-V031` / `RET-V032` 两种周期口径 |
| `app/retention_definitions.py` | 同期群定义、口径版本、残留与 V032 留档的原始数据 |
| `app/retention_seed.py` | 由计算结果生成矩阵、版本表、留档与洞察结论示例数据 |
| `app/services/retention.py` | 共用读取/重算路径、矩阵替换事务、历史核对 |
| `app/services/analysis_board.py` | 分析看板类模块共用的列表/运行/详情/摘要实现 |

数据表：

- `retention_matrix`：留存矩阵数据表，历史周期口径 `RET-V031` 的历史列。
- `retention_matrix_v032`：新周期口径的独立版本表，不覆盖历史列。
- `retention_matrix_snapshot`：整列重算前的历史列快照。
- `retention_v032_archive`：V032 留档，记录每次矩阵替换/清理/恢复的结果与指纹。
- `retention_history`：历史留档，保存原成员边界与历史周期列，重跑时只认这份。
- `insight_conclusion`：洞察结论数据表，报告关键发现的周期留存率来自矩阵。

接口：

- `GET /api/retention_matrix?version=V031|V032`：按版本读取矩阵。
- `GET /api/retention_matrix/history-check`：核对矩阵是否复现历史结果。
- `GET /api/retention_matrix/archive`、`/archive-check`：V032 留档与按留档核对。
- `POST /api/retention_matrix/replace`：`策略=historical_first|recompute` 执行矩阵替换。
- `POST /api/retention_matrix/clean-residue`、`/restore`：清理未清残留 / 用快照恢复历史列。
- `GET /api/insight_report/conclusions`、`/verify`：洞察结论表与报告样例核对。

两条口径冲突的处理方式（V032）：

- 历史周期口径优先：矩阵保留旧列结果，行上附 `新口径差异`（`历史口径` / `新口径` / `差异`）。
- 按新指标口径整列重算：矩阵替换为当前口径，替换前先写 `retention_matrix_snapshot`。

矩阵替换在一个事务里完成；只要检测到越界周期列（例如 `第99期`），整笔回滚并写入留档，
矩阵与版本表保持原样。重跑历史同期群沿用 `retention_history` 里的成员边界，不读取当前群组定义。

领域：数据工程
子方向：数据分析与数据应用
