# BLACK ERP

抖店电商**内部协同管理系统**：供应商/规格成本主数据、订单成本核算与利润计算、客服发票与售后登记、经营驾驶舱与日报，内置角色权限与全量操作审计。

> 仅面向 PC 端内部使用；部署形态为 **内网 Windows 服务器 + Docker Compose**（远程访问可选 frp 穿透）。

## 功能模块

| 模块 | 菜单 | 说明 |
|---|---|---|
| 工作台 | 待办 / 快捷入口 | 按角色聚合常用操作 |
| 客服工作台 | 售后登记 · 发票管理 · 供应商对接 | 发票满 8 天未回传自动提醒 |
| 成本报价 | 供应商管理 · 规格成本表 · 店铺产品登记 · ROI 计算 | 规格为 `SP+6位编码` 全系统主键；支持 XLSX 模板导入 |
| 财务核算 | 订单上传与计算 · 计算批次 | CSV 上传 → Celery 异步计算 → 匹配四级（规则→规格→最长命中→仅最长）→ 批次汇总 |
| 经营驾驶舱 | 利润总览 · 经营日报 | 日报每日 09:00 自动生成 |
| 系统管理 | 账号管理 · 角色权限 · 附加成本规则 · 操作日志 | 角色 admin/boss/cs/po/op/fin；写操作全量审计 |

**核算口径要点**：偏远地区附加运费按件计（海南/青海/内蒙/宁夏/甘肃 +4，新疆/西藏 +20）；退货仍计入成本，售后单数仅作展示指标。

## 技术栈

| 层 | 选型 |
|---|---|
| 前端 | Vue 3 · TypeScript · Vite · Element Plus · Pinia |
| 后端 | FastAPI · SQLAlchemy 2 (async) · Pydantic v2 · Celery |
| 存储 | MySQL 8 · Redis 7（会话 + 任务队列） |
| 部署 | Docker Compose · nginx · frp（可选） |

## 快速开始

**环境要求**：Windows 10/Server 2016+ · [Docker Desktop](https://www.docker.com/) 4.x+ · Node 18+（构建前端）

```bat
:: 1. 克隆代码
git clone git@github.com:leesnail/black_erp.git
cd black_erp

:: 2. 一键部署（依次执行环境检查 → 生成 .env → 构建前端 → 初始化数据库 → 启动 → 验证）
deploy\scripts\00_deploy_all.bat
```

脚本会在生成 `.env` 后暂停，提示你修改生产密码；也可分步执行 `01`→`06`（各步幂等，失败可单独重跑）。详见 [部署文档](docs/部署/部署文档.md)。

**验证部署**：浏览器打开 `http://<服务器IP>/`，健康检查 `http://<服务器IP>/health`。

### 默认账号

| 账号 | 密码 | 角色 |
|---|---|---|
| `admin` | `Admin@12345` | 超级管理员 |
| `finance` | `Fin@12345` | 财务 |

> ⚠️ **首次登录后请立即在「账号管理」重置密码**；生产环境 `.env` 中的数据库口令、`SECRET_KEY` 必须更换。

### 常用运维脚本

| 脚本 | 作用 |
|---|---|
| `deploy\scripts\11_start.bat` / `12_stop.bat` | 启动 / 停止（数据卷保留） |
| `deploy\scripts\13_logs.bat` | 跟随 app / worker / beat 日志 |
| `deploy\scripts\10_backup.bat` | 备份数据库 + 上传件 + 配置 → `backup\<时间戳>\` |

## 本地开发

```powershell
# 后端（依赖本机或 Docker 的 MySQL/Redis，见 .env.example）
cd backend
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.init_db        # 建表 + 种子（幂等；dev 模式启动也会自动执行）
uvicorn app.main:app --reload

# Celery（成本计算/报表任务）
celery -A app.tasks.celery_app worker -Q celery -l info

# 前端（dev 代理 /api → :8000）
cd frontend
npm install
npm run dev
```

## 项目结构

```
black_erp/
├── backend/                 # FastAPI 后端（app/api · app/services · app/tasks）
├── frontend/                # Vue3 前端（views · components · api · stores）
├── deploy/
│   ├── scripts/             # 编号部署/运维 bat 脚本
│   ├── nginx.conf           # 反代与 SPA 配置
│   └── frp*.example         # 内网穿透配置样例
├── docker-compose.yml       # mysql / redis / app / worker / beat / nginx
└── docs/                    # 全套设计文档（见下）
```

## 文档

| 文档 | 内容 |
|---|---|
| [需求文档](docs/产品设计/BLACK-ERP-需求文档.md) | 业务背景、功能需求清单、口径确认项 |
| [产品设计](docs/产品设计/README.md) | 模块设计、数据模型、页面原型（SVG） |
| [架构设计](docs/架构设计/架构设计文档.md) | 总体架构、部署拓扑、切片计划 |
| [安全设计](docs/架构设计/安全设计文档.md) | 鉴权模型、PII 脱敏、审计与密钥规范 |
| [后端开发文档](docs/开发设计/后端开发文档.md) | API 契约、服务/任务设计、测试要点 |
| [前端开发文档](docs/开发设计/前端开发文档.md) | 页面/组件契约、状态流、权限裁剪 |
| [部署文档](docs/部署/部署文档.md) | 脚本部署、原生 Windows、frp、备份与排障 |

## License

内部项目，未开源授权。
