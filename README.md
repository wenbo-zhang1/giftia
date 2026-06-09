<div align="center">

# Giftia — AI 情感陪伴助手

**拥有认知记忆系统的 AI 情感伴侣，基于艾宾浩斯遗忘曲线、RRF 混合检索与 LangGraph 三 Agent 协作工作流**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Workflow-1C3C3C?style=flat)](https://github.com/langchain-ai/langgraph)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF?style=flat&logo=vite&logoColor=white)](https://vitejs.dev)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)

</div>

---

## 项目简介

**Giftia** 是一个 AI 情感陪伴助手，不只是聊天机器人——她能真正「记住」关于你的事，并像朋友一样关心你的情绪。名字源自《可塑性记忆》中拥有感情的人形智能机器人，当今社会的请与爱太过稀缺与昂贵，希望未来一天人类能开发出真正的情感陪伴机器人。

与传统聊天 AI 不同，Giftia 拥有**认知记忆系统**——融合 RRF 混合检索、艾宾浩斯遗忘曲线、查询改写、多特征 Reranking 与多级降级的混合架构。她能模拟人类记忆的编码、存储、检索、遗忘四个阶段：你告诉她的事情，她不会轻易忘记；不重要的事情，她会慢慢淡忘。

Giftia 由三个协作的 AI Agent 驱动：**情感分析 Agent** 与 **记忆检索 Agent** 并行工作，然后**对话生成 Agent** 综合这些信息，用心地与你对话。

---

## 核心特性

- **认知记忆系统** — RRF 混合检索（语义 + 关键词多路召回）+ 查询改写 + 多特征 Reranking（时间衰减 / 情感匹配 / 重要性），模拟人类记忆的编码-存储-检索-遗忘全流程
- **工作记忆层** — 跨对话持久化的短期上下文，解决切换对话后 AI "失忆"的问题
- **双层存储冗余** — Mem0 云端向量检索 + 本地 SQLite 语义检索，任一故障不影响系统运行
- **三 Agent 协作工作流** — 情感分析与记忆检索并行执行，对话生成 Agent 综合信息流式回复
- **艾宾浩斯遗忘曲线** — 记忆保留率按 `R = e^(-t/S)` 自然衰减，高重要性记忆衰减更慢
- **流式逐 Token 输出** — 基于 `asyncio.Queue` 实现逐 token 推送，回复像真人打字一样自然
- **可观测性** — 请求耗时中间件 + `/api/metrics` 端点，暴露各端点 QPS / 平均延迟 / 错误率
- **自定义人设** — Web 端侧栏点击按钮即可修改 AI 性格、身份和说话风格，立即生效
- **多模型支持** — DeepSeek / OpenAI / 智谱 / 通义千问 / SiliconFlow，切换只需改两个变量
- **深度思考模式** — 支持各模型 thinking 模式，通过 `MODEL_PROFILES` 配置，新增模型零代码改动
- **多模态对话** — 图片上传，AI 能「看懂」你分享的图片（需视觉模型），微信风格图片气泡
- **安全认证** — 双级密钥认证（访问密钥 + 管理员密钥），保护对话数据安全

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
                ┌────────────┼────────────┐
                │            │            │
             记忆上下文      情感摘要     工作记忆
                │            │            │
                └────────────┼────────────┘
                             │
                    ┌────────▼────────┐
                    │   对话生成 Agent   │  ← 综合信息，流式生成共情回复
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    记忆存储      │  ← 提取关键事实，后台异步写入长期记忆
                    └─────────────────┘
```

### 记忆检索流程（RAG）

```
用户输入 → 查询改写（LLM 生成 2-3 个检索查询）
         → 每个查询并行跑语义 + 关键词两路召回
         → RRF 融合排序（k=60）
         → 多特征 Reranking（RRF 分数 0.5 + 时间衰减 0.2 + 情感匹配 0.15 + 重要性 0.15）
         → Top N 记忆注入 Prompt
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
| **记忆系统** | 认知记忆模型 | 遗忘曲线 + RRF 混合检索 + 查询改写 + Reranking |
| **云端记忆** | Mem0 | 云端向量检索，跨设备同步 |
| **语义向量** | 智谱 Embedding API (embedding-3) | 余弦相似度记忆匹配 |
| **存储** | SQLite (WAL 模式) | 对话 & 记忆持久化，增量写入 |
| **测试** | pytest (76 tests) + Vitest (22 tests) | 后端核心算法 + 前端交互测试 |
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
# MEM0_API_KEY=your-mem0-key-here      # 云端记忆（可选）
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
│   ├── memory_manager.py           # 记忆系统核心：遗忘曲线、RRF 混合检索、Reranking、Mem0 桥接
│   ├── working_memory.py           # 工作记忆：跨对话上下文持久化
│   ├── llm_config.py               # LLM 客户端工厂
│   ├── model_config.py             # 模型配置中心：Provider 检测、Key 解析
│   ├── model_presets.py            # 预设模型列表
│   ├── file_processor.py           # 图片处理：格式校验、多模态检测
│   ├── conversation_store.py       # 会话持久化（SQLite）
│   └── tests/                      # 单元测试（76 tests）
│       ├── test_core.py            # 遗忘曲线、Provider 检测、序列化
│       ├── test_api.py             # API 端点、SSE、速率限制
│       └── test_rag.py             # RRF 检索、查询改写、Reranking、工作记忆
├── frontend/                       # 前端（React / TypeScript / Vite）
│   └── src/
│       ├── App.tsx                 # 根组件（布局 + 认证门控）
│       ├── api.ts                  # API 调用层（含 SSE 流式）
│       ├── store.ts                # Zustand 状态管理
│       ├── types.ts                # TypeScript 类型定义
│       └── components/             # UI 组件（12 个）
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
| `DELETE` | `/api/memory/{user_id}` | 清除所有记忆 | Access Key |

### 配置与系统

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| `GET` | `/api/config/model` | 获取当前模型配置 | Access Key |
| `GET` | `/api/config/model-presets` | 获取预设模型列表 | Access Key |
| `GET` | `/api/config/prompt` | 获取当前人设 Prompt | Access Key |
| `PUT` | `/api/config/prompt` | 修改人设 Prompt | Admin Key |
| `GET` | `/api/logs` | 获取服务日志 | Admin Key |
| `GET` | `/api/metrics` | 服务指标（QPS / 延迟 / 错误率） | Admin Key |
| `GET` | `/api/health` | 健康检查（含 LLM/Mem0 连通性） | 无 |

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

记忆生命周期：编码（事实提取 + 情感标注 + 重要性评分 + 语义向量）→ 存储（双写）→ 检索（RRF + Reranking）→ 衰减（遗忘曲线）→ 巩固（保留率 < 0.3 时触发）→ 清理（保留率 < 0.1 且未巩固则移除）

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

**Q: 记忆功能不工作？**
A: 需配置 `ZHIPU_API_KEY`（语义检索）和/或 `MEM0_API_KEY`（云端记忆）。两者都未配置时降级到关键词匹配。

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

[MIT License](./LICENSE) | Copyright (c) 2026 wenbo-zhang1
