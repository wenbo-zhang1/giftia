<div align="center">

# Giftia — AI 情感陪伴助手

**拥有多层认知记忆系统的 AI 情感伴侣，基于艾宾浩斯遗忘曲线、RRF 混合检索、用户档案卡与 LangGraph 三 Agent 协作工作流**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Workflow-1C3C3C?style=flat)](https://github.com/langchain-ai/langgraph)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF?style=flat&logo=vite&logoColor=white)](https://vitejs.dev)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/Version-v0.2-blue.svg)](./CHANGELOG.md)

</div>

---

## 项目简介

**Giftia** 是一个 AI 情感陪伴助手，不只是聊天机器人——她能真正「记住」关于你的事，并像朋友一样关心你的情绪。名字源自《可塑性记忆》中拥有感情的人形智能机器人，当今社会的请与爱太过稀缺与昂贵，希望未来一天人类能开发出真正的情感陪伴机器人。

与传统聊天 AI 不同，Giftia 拥有**多层认知记忆系统**——用户档案卡 + 三层分级记忆（核心/重要/常规）+ 时间标签 + 艾宾浩斯遗忘曲线 + RRF 混合检索。她能模拟人类记忆的编码、存储、检索、遗忘四个阶段：你告诉她的事情，她不会轻易忘记；不重要的事情，她会慢慢淡忘。

Giftia 由三个协作的 AI Agent 驱动：**情感分析 Agent** 与 **记忆检索 Agent** 并行工作，然后**对话生成 Agent** 综合这些信息，用心地与你对话。

---

## 核心特性

- **多层认知记忆系统** — 用户档案卡（结构化画像）+ 三层分级记忆（核心/重要/常规）+ 时间标签 + 艾宾浩斯遗忘曲线，模拟人类记忆的编码-存储-检索-遗忘全流程
- **用户档案卡** — 自动从对话中提取身份信息、喜好偏好、人际关系、情感模式，生成结构化用户画像，每次对话自动注入
- **记忆分层与遗忘** — 核心记忆（永不遗忘 S=10）、重要记忆（慢速遗忘 S=2）、常规记忆（正常遗忘 S=1），按重要性和情感强度自动分级
- **记忆时间标签** — 自动识别「昨天」「去年夏天」「大学时期」等时间表达，为记忆附加时间上下文
- **情感分析引擎** — 规则+LLM 混合情感分析，支持语境翻转（「喜欢+没结果」→ 难过而非开心），情感标签自动传递给记忆存储
- **工作记忆层** — 跨对话持久化的短期上下文，解决切换对话后 AI "失忆"的问题
- **记忆查看器** — Web 端可查看档案卡、全部记忆（含层级/情感/时间标签）、工作记忆摘要
- **三 Agent 协作工作流** — 情感分析与记忆检索并行执行，对话生成 Agent 综合信息流式回复
- **RRF 混合检索** — 语义 + 关键词多路召回 → RRF 融合（k=60）→ 多特征 Reranking（RRF 0.5 + 时间衰减 0.2 + 情感匹配 0.15 + 重要性 0.1 + 层级权重 0.05）
- **流式逐 Token 输出** — 基于 `asyncio.Queue` 实现逐 token 推送，回复像真人打字一样自然
- **可观测性** — 请求耗时中间件 + `/api/metrics` 端点，暴露各端点 QPS / 平均延迟 / 错误率
- **自定义人设** — Web 端侧栏点击按钮即可修改 AI 性格、身份和说话风格，立即生效
- **多模型支持** — DeepSeek / OpenAI / 智谱 / 通义千问 / SiliconFlow，切换只需改两个变量
- **深度思考模式** — 支持各模型 thinking 模式，通过 `MODEL_PROFILES` 配置，新增模型零代码改动
- **多模态对话** — 图片上传，AI 能「看懂」你分享的图片（需视觉模型），微信风格图片气泡
- **安全认证** — 双级密钥认证（访问密钥 + 管理员密钥），保护对话数据安全

---

## 版本迭代

### v0.2 — 多层认知记忆系统 `当前版本`

> 从双层存储架构升级为完全本地的多层认知记忆系统，新增用户档案卡、记忆分层、时间标签、记忆查看器，移除 Mem0 外部依赖。

**新增**
- 用户档案卡（`user_profile.py`）— 自动提取 identity / preferences / relationships / emotional_profile，结构化用户画像
- 记忆分层（`memory_layer.py`）— 核心记忆（S=10）/ 重要记忆（S=2）/ 常规记忆（S=1），按重要性和情感强度自动分级
- 记忆时间标签（`temporal_metadata.py`）— 识别「昨天」「去年夏天」「大学时期」等时间表达
- 记忆查看器（`MemoryViewerModal`）— Web 端查看档案卡 + 全部记忆（含层级/情感/时间标签）+ 工作记忆摘要
- 情感分析语境翻转 — 「喜欢 + 没结果」→ 难过而非开心，「努力 + 失败」→ 难过而非希望
- 情感标签传递 — 情感分析 Agent 结果自动传递给记忆存储，不再退回关键词匹配
- 档案卡 API（`GET/PUT /api/profile/{user_id}`）+ 记忆详情 API（`GET /api/memory/{user_id}/detail`）+ 层级管理 API
- 数据库迁移脚本（`migration_v2.py`）— v1 → v2 平滑升级，补 schema_version 记录

**移除**
- Mem0 云端记忆 — 本地系统已完整覆盖其能力（事实提取 + 向量生成 + 混合检索），移除后系统更简单、更快、无外部依赖

**修复**
- 前端 useEffect 无限循环导致 429 速率限制
- 流式聊天消息状态管理（消息 ID 精确定位，防止用户消息消失和重复回复）
- `run_emotion_workflow_streaming` 中 `profile_manager` 未传递导致的 NameError

---

### v0.1 — 认知记忆系统 `初始版本`

> 基础架构搭建：三 Agent 工作流 + 认知记忆模型 + Mem0 双层存储 + Web 前端。

- 艾宾浩斯遗忘曲线 — `R = e^(-t/S)`，记忆保留率按时间自然衰减
- RRF 混合检索 — 语义 + 关键词多路召回 → RRF 融合 → 多特征 Reranking
- 查询改写 — LLM 将口语化输入扩展为 2-3 个检索查询
- 工作记忆层 — 跨对话持久化的短期上下文（`working_memory.py`）
- Mem0 双层存储 — 云端向量检索 + 本地 SQLite 语义检索，冗余备份
- 三 Agent 协作工作流（LangGraph）— 情感分析 ‖ 记忆检索 → 对话生成
- 流式逐 Token 输出 — SSE 推送 + `asyncio.Queue`
- Web 前端（React + TypeScript + Vite）— 对话界面 + 侧栏管理
- 多模型支持 — DeepSeek / OpenAI / 智谱 / 通义千问 / SiliconFlow
- 自定义人设 + 多模态对话 + 安全认证 + 可观测性

---

## 系统架构

```
                          用户输入
                             │
                 ┌───────────┴───────────┐
                 │                       │
          ┌──────▼──────┐        ┌───────▼──────┐
          │ 情感分析 Agent│        │ 记忆检索 Agent │  ← 并行执行
          └──────┬──────┘        └───────┬──────┘
                 │                       │
                 └───────────┬───────────┘
                             │
           ┌─────────┼─────────┼─────────┐
           │         │         │         │
       档案卡    记忆上下文    情感摘要   工作记忆
           │         │         │         │
           └─────────┴─────────┴─────────┘
                             │
                    ┌────────▼────────┐
                    │   对话生成 Agent   │  ← 综合信息，流式生成共情回复
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    记忆存储      │  ← 事实提取 + 情感标签传递 + 时间标签 + 层级分配
                    └─────────────────┘
```

### 记忆检索流程（RAG）

```
用户输入 → 查询改写（LLM 生成 2-3 个检索查询）
         → 每个查询并行跑语义 + 关键词两路召回
         → RRF 融合排序（k=60）
         → 多特征 Reranking（RRF 0.5 + 时间衰减 0.2 + 情感匹配 0.15 + 重要性 0.1 + 层级权重 0.05）
         → Top N 记忆注入 Prompt
```

### 记忆分层架构

```
┌─ 工作记忆（当前状态摘要，每次对话注入，覆盖式更新）
│
├─ 档案卡（结构化用户画像，每次对话注入，增量式更新）
│   └─ identity / preferences / relationships / emotional_profile
│
└─ 长期记忆（原始事实，按需检索，按层级遗忘）
    ├─ 核心记忆（重要性≥0.8 或 情感强度≥0.8）  ← S=10，几乎不忘
    ├─ 重要记忆（重要性≥0.6 或 情感强度≥0.7）  ← S=2，慢速遗忘
    └─ 常规记忆（其余）                          ← S=1，正常遗忘
```

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | React 18 + TypeScript + Vite 5 | 响应式 SPA，温暖治愈风格 UI |
| **状态管理** | Zustand | 轻量级状态管理 |
| **后端** | FastAPI + Uvicorn | 高性能异步 API，SSE 流式响应 |
| **Agent 编排** | LangGraph + LangChain | 三 Agent 工作流（情感分析与记忆检索并行） |
| **LLM 客户端** | langchain-openai (ChatOpenAI) | 统一接口，支持多模型 |
| **记忆系统** | 多层认知记忆模型 | 档案卡 + 三层分级 + 时间标签 + 遗忘曲线 + RRF 混合检索 + Reranking |
| **语义向量** | 智谱 Embedding API (embedding-3) | 余弦相似度记忆匹配 |
| **存储** | SQLite (WAL 模式) | 对话 & 记忆 & 档案卡持久化，增量写入 |
| **测试** | pytest (70 tests) + Vitest (22 tests) | 后端核心算法 + 前端交互测试 |
| **CI** | GitHub Actions | ruff lint + pytest + eslint + tsc build + vitest |

---

## 快速启动

### 环境要求

- Python 3.11+
- Node.js 18+

### 1. 克隆项目

```bash
git clone https://github.com/wenbo-zhang1/giftia.git
cd giftia
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入 API Key：

```env
DEEPSEEK_API_KEY=sk-your-key-here
# ZHIPU_API_KEY=your-zhipu-key-here    # 语义向量检索需要
```

### 3. 启动服务

```bash
# Windows
.\start.bat

# macOS / Linux
chmod +x start.sh && ./start.sh
```

启动后访问 `http://localhost:3000`。API 文档：`http://127.0.0.1:8000/docs`

---

## 配置说明

### 切换 LLM 模型

修改 `backend/model_config.py`：

```python
CHAT_MODEL = "deepseek-v4-flash"
CHAT_BASE_URL = "https://api.deepseek.com/v1"
```

系统根据 `base_url` 自动识别提供商并匹配 API Key。

| 提供商 | base_url 关键词 | .env 变量名 |
|--------|----------------|-------------|
| DeepSeek | `deepseek` | `DEEPSEEK_API_KEY` |
| OpenAI | `openai.com` | `OPENAI_API_KEY` |
| 智谱 AI | `bigmodel.cn` | `ZHIPU_API_KEY` |
| 通义千问 | `dashscope` | `DASHSCOPE_API_KEY` |
| SiliconFlow | `siliconflow` | `SILICONFLOW_API_KEY` |

### 访问认证

```env
GIFTIA_ACCESS_KEY=your-secret-key   # 前端访问密钥
GIFTIA_ADMIN_KEY=your-admin-key     # 管理员密钥（日志、Metrics、Prompt 修改）
```

---

## 项目目录结构

```
giftia/
├── backend/                        # 后端（Python / FastAPI）
│   ├── server.py                   # FastAPI 主服务：路由、认证、SSE、Metrics 中间件
│   ├── emotion_graph.py            # LangGraph 三 Agent 工作流 + 流式执行
│   ├── memory_manager.py           # 记忆系统核心：遗忘曲线、RRF 混合检索、Reranking、事实提取
│   ├── memory_layer.py             # 记忆分层：核心/重要/常规，遗忘强度与检索权重
│   ├── temporal_metadata.py        # 时间标签：时间表达识别、时间上下文提取
│   ├── user_profile.py             # 用户档案卡：结构化画像、自动更新
│   ├── working_memory.py           # 工作记忆：跨对话上下文持久化
│   ├── llm_config.py               # LLM 客户端工厂
│   ├── model_config.py             # 模型配置中心：Provider 检测、Key 解析
│   ├── model_presets.py            # 预设模型列表
│   ├── file_processor.py           # 图片处理：格式校验、多模态检测
│   ├── conversation_store.py       # 会话持久化（SQLite）
│   ├── migration_v2.py             # 数据库迁移脚本（v1 → v2：档案卡 + 分层 + 时间标签）
│   └── tests/                      # 单元测试（70 tests）
│       ├── test_core.py            # 遗忘曲线、Provider 检测、序列化
│       ├── test_api.py             # API 端点、SSE、速率限制
│       ├── test_rag.py             # RRF 检索、查询改写、Reranking、工作记忆
│       └── test_memory_upgrade.py  # 档案卡、时间标签、记忆分层、迁移脚本
├── frontend/                       # 前端（React / TypeScript / Vite）
│   └── src/
│       ├── App.tsx                 # 根组件（布局 + 认证门控）
│       ├── api.ts                  # API 调用层（含 SSE 流式）
│       ├── store.ts                # Zustand 状态管理
│       ├── types.ts                # TypeScript 类型定义
│       └── components/             # UI 组件（13 个，含记忆查看器）
├── .github/workflows/ci.yml        # CI：ruff + pytest + eslint + build + vitest
├── .env.example                    # 环境变量模板
├── requirements.txt                # Python 依赖
└── README.md
```

---

## API 接口

### 对话

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| `POST` | `/api/chat/{user_id}` | 发送消息（SSE 流式返回） | Access Key |
| `GET` | `/api/conversations/{user_id}` | 获取对话列表 | Access Key |
| `GET` | `/api/conversations/{user_id}/{conv_id}` | 获取对话详情 | Access Key |
| `POST` | `/api/conversations/{user_id}` | 新建对话 | Access Key |
| `PATCH` | `/api/conversations/{user_id}/{conv_id}` | 重命名对话 | Access Key |
| `DELETE` | `/api/conversations/{user_id}/{conv_id}` | 删除对话 | Access Key |

### 用户与记忆

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| `GET` | `/api/users` | 获取用户列表 | Access Key |
| `POST` | `/api/users?user_id=xxx` | 创建用户 | Access Key |
| `GET` | `/api/memory/{user_id}/stats` | 获取记忆统计 | Access Key |
| `GET` | `/api/memory/{user_id}/detail` | 获取全部记忆详情（按层级分组） | Access Key |
| `GET` | `/api/memory/{user_id}/layers` | 获取各层级记忆统计 | Access Key |
| `PATCH` | `/api/memory/{user_id}/{memory_id}/layer` | 手动调整记忆层级 | Access Key |
| `DELETE` | `/api/memory/{user_id}` | 清除所有记忆 | Access Key |
| `GET` | `/api/profile/{user_id}` | 获取用户档案卡 | Access Key |
| `PUT` | `/api/profile/{user_id}` | 手动更新档案卡 | Access Key |

### 配置与系统

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| `GET` | `/api/config/model` | 获取当前模型配置 | Access Key |
| `GET` | `/api/config/model-presets` | 获取预设模型列表 | Access Key |
| `GET` | `/api/config/prompt` | 获取当前人设 Prompt | Access Key |
| `PUT` | `/api/config/prompt` | 修改人设 Prompt | Admin Key |
| `GET` | `/api/logs` | 获取服务日志 | Admin Key |
| `GET` | `/api/metrics` | 服务指标（QPS / 延迟 / 错误率） | Admin Key |
| `GET` | `/api/health` | 健康检查（含 LLM 连通性） | 无 |

### SSE 事件格式

```json
{"type": "status", "text": "Giftia 正在感受你的情绪并回忆..."}
{"type": "token", "text": "你"}
{"type": "reply", "text": "完整的回复文本"}
{"type": "done", "conversation_id": "uuid"}
{"type": "error", "text": "错误信息"}
```

---

## 核心算法：艾宾浩斯遗忘曲线

```
R = e^(-t/S)
```

- **R**：记忆保留率（0-1）
- **t**：经过时间（小时）
- **S**：记忆强度 = 基础强度 `0.3` + 重要性加成 `importance × 0.5` + 复习次数加成 `min(access_count × 0.15, 1.0)`

记忆生命周期：编码（事实提取 + 情感标注 + 重要性评分 + 层级分配 + 语义向量 + 时间标签）→ 存储（SQLite）→ 检索（RRF + Reranking）→ 衰减（遗忘曲线，按层级差异化）→ 巩固（保留率 < 0.3 时触发）→ 清理（保留率 < 0.1 且未巩固则移除）

---

## 开发指南

```bash
# 后端开发（热重载）
python backend/server.py

# 前端开发（HMR）
cd frontend && npm run dev

# 后端测试
cd backend && python -m pytest tests/ -v

# 前端测试
cd frontend && npx vitest run

# 代码质量
cd frontend && npm run lint && npm run build
```

---

## 常见问题

**Q: 启动报错「未找到 API Key」？**
A: 检查 `.env` 文件，确保至少配置了当前模型对应的 API Key。

**Q: 记忆检索效果不好？**
A: 需配置 `ZHIPU_API_KEY`（语义向量检索）。未配置时降级到纯关键词匹配，检索效果会下降。

**Q: 切换模型后 Embedding 报 401？**
A: Embedding 使用独立的 `EMBED_PROVIDER`（默认 `zhipu`），与对话模型解耦，需单独配置 `ZHIPU_API_KEY`。

**Q: 流式回复卡住？**
A: 检查后端日志，可能是 LLM API 超时或限流。对话过长可开启新对话。

---

## 贡献指南

1. Fork 本项目
2. 创建功能分支：`git checkout -b feature/your-feature-name`
3. 提交代码：`git commit -m '描述你的改动'`
4. 推送并创建 Pull Request

PR 提交前请确保：前端 `npm run lint && npm run build` 通过，后端 `python -m pytest tests/ -v` 通过。

---

## License

[AGPL-3.0License](./LICENSE) | Copyright (c) 2026 wenbo-zhang1
