<div align="center">

# Giftia  — AI 情感陪伴助手

**一个拥有认知记忆系统的 AI 情感伴侣，基于艾宾浩斯遗忘曲线、语义向量检索与 LangGraph 三 Agent 协作工作流**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Workflow-1C3C3C?style=flat)](https://github.com/langchain-ai/langgraph)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF?style=flat&logo=vite&logoColor=white)](https://vitejs.dev)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)

</div>

---

## 目录

- [项目简介](#项目简介)
- [核心特性](#核心特性)
- [系统架构](#系统架构)
- [记忆系统详解](#记忆系统详解)
- [技术栈](#技术栈)
- [快速启动](#快速启动)
- [配置说明](#配置说明)
- [使用说明](#使用说明)
- [项目目录结构](#项目目录结构)
- [核心算法：艾宾浩斯遗忘曲线](#核心算法艾宾浩斯遗忘曲线)
- [API 接口](#api-接口)
- [开发指南](#开发指南)
- [常见问题](#常见问题)
- [贡献指南](#贡献指南)
- [License](#license)

---

## 项目简介

**Giftia**是一个 AI 情感陪伴助手，不只是聊天机器人——她能真正「记住」关于你的事，并像朋友一样关心你的情绪。
她的名字源自《可塑性记忆》中拥有感情的人形智能机器人，希望未来有一天，人类能开发出真正的情感陪伴机器人，现在的社会，情与爱太昂贵了。

与传统聊天 AI 不同，Giftia 拥有**认知记忆系统**——融合向量语义检索、艾宾浩斯遗忘曲线、情感增强与多级降级的混合架构。她能模拟人类记忆的编码、存储、检索、遗忘四个阶段：你告诉她的事情，她不会轻易忘记；不重要的事情，她会慢慢淡忘。这种设计让每次对话都更有连贯性和人情味。

Giftia 由三个协作的 AI Agent 驱动：**情感分析 Agent** 与 **记忆检索 Agent** 并行工作，然后**对话生成 Agent** 综合这些信息，用心地与你对话。

你可以在 Web 端修改 Giftia 的「人设」——性格、身份、说话风格——让她成为独属于你的情感伴侣。

---

## 核心特性

- **认知记忆系统** — 融合向量语义检索（Embedding）、艾宾浩斯遗忘曲线、情感增强与多级降级的混合记忆架构，模拟人类记忆的编码-存储-检索-遗忘全流程。
- **双层存储冗余** — Mem0 云端向量检索 + 本地 SQLite 语义检索，任一故障不影响系统运行，自动降级保障记忆始终可用。
- **三 Agent 协作工作流** — 情感分析 Agent 与记忆检索 Agent 并行执行，对话生成 Agent 综合信息流式生成回复，各司其职。
- **流式逐 Token 输出** — 基于 `asyncio.Queue` 实现逐 token 推送，让回复像真人打字一样自然流畅。
- **自定义人设** — 在 Web 端侧栏点击按钮即可修改 AI 的性格、身份和说话风格，修改后立即生效，无需重启服务。
- **多模型支持** — 支持 DeepSeek / OpenAI / 智谱 AI / 通义千问 / SiliconFlow 等主流 LLM，切换模型只需改两个变量。
- **深度思考模式** — 支持各模型的 thinking 模式（智谱、DeepSeek、Qwen 等），通过 `MODEL_PROFILES` 配置，新增模型零代码改动。
- **多模态对话** — 支持图片上传，AI 能「看懂」你分享的图片（需使用支持视觉的模型），图片以微信风格附在消息气泡中。
- **安全认证** — 内置双级密钥认证机制（访问密钥 + 管理员密钥），保护你的对话数据安全。
- **SQLite 持久化** — 对话记录和记忆数据存入 SQLite 数据库，增量写入 + WAL 模式支持并发读写，数据安全可靠。

---

## 系统架构

### 工作流架构

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
             记忆上下文      情感摘要     对话历史
                │            │            │
                └────────────┼────────────┘
                             │
                    ┌────────▼────────┐
                    │   对话生成 Agent   │  ← 综合信息，流式生成共情回复
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    记忆存储      │  ← 提取关键事实，写入长期记忆
                    └────────┬────────┘
                             │
                        用户收到回复
```

### 记忆系统架构

```
用户对话 → 事实提取（规则 + LLM 双路提取）→ 记忆写入
                                                   │
                                        ┌──────────┼──────────┐
                                        │          │          │
                                  本地记忆存储   Mem0 云端   语义向量索引
                                   (SQLite)    (向量检索)   ( Embedding)
                                        │          │          │
                                        └──────────┼──────────┘
                                                   │
                                        记忆检索时（三级保障）：
                                  1. 语义 Embedding 检索（余弦相似度 × 0.7 + 重要性 × 0.3）
                                  2. 关键词匹配检索（fallback 降级）
                                  3. 最近记忆回退（兜底保障）
                                        │          │
                                  艾宾浩斯遗忘曲线  情感增强
                                  （自动衰减清理）  （11种情感标签）
                                        │          │
                                        └──────────┼──────────┘
                                                   │
                                            输出记忆上下文
```

### 数据存储架构

```
giftia.db (SQLite, WAL 模式)
├── conversations 表    — 用户对话记录（user_id, data JSON）
└── memories 表         — 用户长期记忆（user_id, memory_id, data JSON）
                            含 embedding 向量、情感标签、重要性评分、tags 等

prompt_config.json       — 自定义人设 Prompt
```

---

## 记忆系统详解

Giftia 的记忆系统采用**认知记忆模型**（Cognitive Memory Model），模拟人类记忆的四个阶段：

### 编码（Encoding）

从对话中提取值得长期记住的信息，采用**规则 + LLM 双路提取**：

1. **规则提取**：扫描"我叫"、"我喜欢"等信息关键词和"焦虑"、"孤独"等情感关键词，快速捕获明确事实
2. **LLM 提取**：调用大模型从对话中提取 7 类事实（情感状态、具体事件、人际关系、偏好习惯、身份生活、担忧困扰、互动记忆）
3. **兜底机制**：如果都没提取到，将用户消息前 60 字作为对话摘要存入，确保不丢失信息

每条记忆自动附加：
- **情感标签**：11 种情感类型 + 情感强度（0-1）
- **重要性评分**：四维度评估（情感强度 0.4 + 信息密度 0.3 + 用户关注度 0.2 + 内容长度 0.1）
- **语义向量**：调用 Embedding模型 API 生成 1024 维向量
- **关键词标签**：从内容中自动提取的关键词（最多 5 个）

### 存储（Storage）

**双层冗余写入**：

| 存储层 | 技术 | 用途 |
|--------|------|------|
| Mem0 云端 | 向量数据库 | 云端语义检索，跨设备同步 |
| 本地存储 | SQLite (WAL) | 离线可用，情感增强，遗忘曲线 |

写入流程：`事实提取 → Mem0 云端写入 + 本地 SQLite 写入（含情感/重要性/embedding）`

### 检索（Retrieval）

**三级保障检索**，确保记忆始终可用：

| 级别 | 方式 | 触发条件 | 特点 |
|------|------|---------|------|
| 1 | 语义匹配 | Embedding API 可用 | 最精准，"人生好苦"能匹配到"买荔枝失望" |
| 2 | 关键词匹配 | API 不可用或无向量数据 | 降级方案，字面匹配 |
| 3 | 最近记忆回退 | 两路都无结果 | 兜底保障，返回最近 N 条记忆 |

语义匹配评分公式：`score = 余弦相似度 × 0.7 + 重要性 × 0.3`

历史记忆无 embedding 时**按需懒加载**：首次检索时批量补算向量，补算后持久化到磁盘。

### 遗忘（Forgetting）

基于**艾宾浩斯遗忘曲线** `R = e^(-t/S)`：

- 记忆保留率随时间自然衰减
- 高重要性、多次检索的记忆衰减更慢（间隔重复效应）
- 当用户记忆数超过 50 条时，自动触发遗忘曲线清理
- 保留率低于 0.1 且未巩固的记忆被自动清理

### 降级策略

系统在各个层面都有自动降级机制：

| 故障场景 | 降级行为 |
|---------|---------|
| Embedding API 不可用 | 语义匹配 → 关键词匹配 |
| Mem0 云端不可用 | 双路检索 → 纯本地检索 |
| LLM 事实提取失败 | LLM 提取 → 规则提取 → 对话摘要 |
| 两路检索都无结果 | 返回最近记忆（兜底） |

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | React 18 + TypeScript + Vite 5 | 响应式 SPA，温暖治愈风格 UI |
| **状态管理** | Zustand | 轻量级状态管理，支持持久化 |
| **Markdown 渲染** | react-markdown + remark-gfm | 支持富文本消息展示 |
| **后端** | FastAPI + Uvicorn | 高性能异步 API，SSE 流式响应 |
| **Agent 编排** | LangGraph + LangChain | 三 Agent 工作流（情感分析与记忆检索并行） |
| **LLM 客户端** | langchain-openai (ChatOpenAI) | 统一接口，支持多模型 |
| **记忆系统** | 认知记忆模型 | 遗忘曲线 + 语义向量 + 情感增强 + 多级降级 |
| **云端记忆** | Mem0 | 云端向量检索，跨设备同步 |
| **语义向量** | 智谱 Embedding API (embedding-3) | 余弦相似度记忆匹配 |
| **存储** | SQLite (WAL 模式) | 对话 & 记忆持久化，增量写入 |
| **代码质量** | ESLint + Prettier | TypeScript 代码规范 |
| **测试** | pytest | 单元测试（遗忘曲线、Provider 检测、序列化等） |

---

## 快速启动

### 环境要求

- Python 3.11+
- Node.js 18+
- npm 或 pnpm

### 1. 克隆项目

```bash
git clone https://github.com/wenbo-zhang1/giftia.git
cd Giftia
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 API Key：

```env
# === 会话模型 API Key（至少配置一个） ===
DEEPSEEK_API_KEY=sk-your-deepseek-key-here
# OPENAI_API_KEY=sk-your-openai-key-here
# ZHIPU_API_KEY=your-zhipu-key-here
# DASHSCOPE_API_KEY=your-qwen-key-here
# SILICONFLOW_API_KEY=your-siliconflow-key-here

# === Mem0 记忆服务 API Key（可选，不配置则仅使用本地记忆） ===
MEM0_API_KEY=your-mem0-key-here

# === 访问认证（可选） ===
# GIFTIA_ACCESS_KEY=your-secret-key
# GIFTIA_ADMIN_KEY=your-admin-key
```

> **注意**：语义向量使用智谱 Embedding API，需配置 `ZHIPU_API_KEY`（与对话模型的 API Key 共用），如使用其他厂商模型，需配置对应的 API Key 。

### 3. 启动服务

#### 方式一：一键启动（推荐）

项目提供了启动脚本，自动检查环境、安装依赖并启动前后端服务：

```bash
# Windows
.\start.bat

# macOS / Linux
chmod +x start.sh
./start.sh
```

启动后访问 `http://localhost:3000` 即可使用。

#### 方式二：手动启动

分别启动后端和前端：

```bash
# 启动后端
pip install -r requirements.txt
python backend/server.py
```

后端默认运行在 `http://127.0.0.1:8000`。启动日志中会显示 Mem0 连接状态、Embedding 初始化状态、多模态支持情况等信息。

API 文档自动生成，可访问 `http://127.0.0.1:8000/docs` 查看 Swagger UI。

```bash
# 启动前端
cd frontend
npm install
npm run dev
```

前端默认运行在 `http://localhost:3000`，通过 Vite proxy 自动代理 `/api` 请求到后端。

### 4. 访问应用

打开浏览器访问 `http://localhost:3000`。

如果配置了访问密钥，首次使用需要输入密钥才能进入应用。

---

## 配置说明

### 切换 LLM 模型

模型配置在 `backend/model_config.py` 中：

```python
CHAT_MODEL = "deepseek-v4-flash"
CHAT_BASE_URL = "https://api.deepseek.com/v1"
```

修改以上两个变量即可切换模型。系统会根据 `base_url` 自动识别提供商，并从 `.env` 中匹配对应的 API Key。

### 支持的模型提供商

| 提供商 | base_url 关键词 | .env 变量名 |
|--------|----------------|-------------|
| DeepSeek | `deepseek` | `DEEPSEEK_API_KEY` |
| OpenAI | `openai.com` | `OPENAI_API_KEY` |
| 智谱 AI | `bigmodel.cn` | `ZHIPU_API_KEY` |
| 通义千问 | `dashscope` | `DASHSCOPE_API_KEY` |
| SiliconFlow | `siliconflow` | `SILICONFLOW_API_KEY` |

### 模型特性配置

`model_config.py` 中的 `MODEL_PROFILES` 字典定义了各模型的特殊参数（如 thinking 思考模式）：

```python
MODEL_PROFILES = {
    "glm-4.6v": {"thinking": {"type": "enabled"}},
    "deepseek": {
        "extra_body": {"thinking": {"type": "enabled"}},
        "reasoning_effort": "high",
    },
    "qwen": {"extra_body": {"enable_thinking": True, "return_reasoning": True}},
    "gpt-4o": {},
}
```

- 精确匹配优先，找不到则前缀匹配（如 `glm-4.6v-flash` 匹配 `glm-4.6v` 的配置）
- 当模型启用 thinking 模式时，`temperature` 自动限制为 `1.0`，`top_p` 参数自动移除
- 新增模型只需在 `MODEL_PROFILES` 中添加一行配置，客户端代码无需修改

### 自定义 AI 人设

在 Web 端侧边栏点击「自定义人设」按钮，在弹窗中修改 Prompt 后保存，立即生效。人设保存在 `backend/prompt_config.json` 中。

### 访问认证

```env
# 访问密钥 — 配置后前端需输入此密钥才能使用
GIFTIA_ACCESS_KEY=your-secret-key

# 管理员密钥 — 用于访问日志、修改 Prompt 等敏感操作
GIFTIA_ADMIN_KEY=your-admin-key
```

- 不配置 `GIFTIA_ACCESS_KEY` 则无需认证
- 配置了 `GIFTIA_ACCESS_KEY` 但不配置 `GIFTIA_ADMIN_KEY` 时，访问密钥同时充当管理员密钥
- API 请求需在 Header 中携带 `X-Access-Key`（普通接口）或 `X-Admin-Key`（管理员接口）

### CORS 跨域配置

```env
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

多个源用逗号分隔。默认允许本地开发端口。

---

## 使用说明

### 基本对话

1. 打开应用后，在输入框中输入消息，按 Enter 发送。
2. AI 会并行分析你的情绪和检索相关记忆，然后生成回复——这个过程以流式方式呈现，你会看到回复逐字出现。
3. 输入框上方会短暂显示状态提示（「Giftia 正在感受你的情绪并回忆...」→「Giftia 正在组织语言...」）。

### 管理对话

- **新建对话**：点击侧边栏顶部的「+」按钮。
- **切换对话**：点击侧边栏中任意对话即可切换。
- **重命名对话**：右键点击对话标题或点击编辑图标。
- **删除对话**：在对话上使用删除操作。

### 自定义人设

1. 点击侧边栏底部的「自定义人设」按钮。
2. 在弹窗中修改 Prompt（系统提示词）。默认 Prompt 定义了 AI 的身份、说话风格和行为准则。
3. 点击保存后立即生效，接下来的对话将使用新的人设。
4. 清空 Prompt 并保存可恢复默认人设。

### 切换模型

点击侧边栏底部的模型名称标签，在弹窗中选择预设模型或自定义模型配置。

### 上传图片

如果当前模型支持多模态（如 GLM-4.6V、GPT-5.5 等），输入框旁会显示图片上传按钮。点击后选择图片即可在对话中分享，图片以微信风格附在消息气泡内。

### 查看日志

点击侧边栏的「查看日志」按钮，可打开日志弹窗查看系统运行日志，方便排查记忆系统等问题。弹窗支持拖拽调整大小。

### 查看记忆统计

鼠标悬停在侧边栏用户区域上，可查看当前用户的记忆数量、巩固程度和平均重要性评分。

---

## 项目目录结构

```
giftia/
├── backend/                        # 后端（Python / FastAPI）
│   ├── server.py                   # FastAPI 主服务：路由、认证、SSE 流式事件
│   ├── emotion_graph.py            # LangGraph 三 Agent 工作流定义 + 流式执行
│   ├── memory_manager.py           # 记忆系统核心：遗忘曲线、语义向量、Mem0 桥接、增量写入
│   ├── llm_config.py               # LLM 客户端工厂：创建 ChatOpenAI 实例
│   ├── model_config.py             # 模型配置中心：模型选择、Provider 检测、Key 解析
│   ├── model_presets.py            # 预设模型列表（Web 端模型切换用）
│   ├── file_processor.py           # 图片处理：格式校验、缩放大图、多模态检测
│   ├── conversation_store.py       # 会话持久化：SQLite 存取对话记录
│   ├── prompt_config.json          # 自定义人设 Prompt 持久化文件
│   ├── giftia.db                   # SQLite 数据库（对话 + 记忆 + 向量）
│   ├── legacy/                     # 历史代码归档
│   │   └── app.py                  # 旧版 Streamlit 应用
│   └── tests/                      # 单元测试
│       └── test_core.py            # 遗忘曲线、Provider 检测、序列化测试
├── frontend/                       # 前端（React / TypeScript / Vite）
│   ├── src/
│   │   ├── App.tsx                 # 根组件：布局 + ErrorBoundary 错误边界
│   │   ├── App.css                 # 根组件样式
│   │   ├── main.tsx                # 入口文件
│   │   ├── api.ts                  # API 调用层：封装所有后端接口
│   │   ├── store.ts                # Zustand 状态管理：全局状态 + 持久化
│   │   ├── types.ts                # TypeScript 类型定义
│   │   ├── index.css               # 全局样式变量（色彩、字体、圆角等）
│   │   └── components/             # UI 组件
│   │       ├── Sidebar.tsx         # 侧边栏：对话列表、新建对话、人设入口
│   │       ├── ChatArea.tsx        # 聊天区域：消息列表、流式渲染
│   │       ├── ChatInput.tsx       # 输入框：消息发送、图片上传
│   │       ├── MessageBubble.tsx   # 消息气泡：微信风格图片展示
│   │       ├── PromptDialog.tsx    # 自定义人设编辑弹窗
│   │       ├── ModelDialog.tsx     # 模型切换弹窗（含多模态说明）
│   │       ├── LogViewerModal.tsx  # 日志查看弹窗（可拖拽调整大小）
│   │       ├── StatsCard.tsx       # 记忆统计卡片
│   │       └── UserSection.tsx     # 用户信息区域
│   ├── vite.config.ts              # Vite 配置（端口 3000、API 代理、超时设置）
│   ├── eslint.config.js            # ESLint 配置
│   ├── .prettierrc                 # Prettier 配置
│   ├── tsconfig.json               # TypeScript 配置
│   └── package.json                # 项目依赖 + 脚本
├── .env.example                    # 环境变量模板
├── .env                            # 环境变量（不入版本控制）
├── .gitignore                      # Git 忽略配置
├── requirements.txt                # Python 依赖列表
└── README.md                       # 项目文档（本文件）
```

### 核心模块详解

#### `server.py` — FastAPI 主服务

- **职责**：HTTP API 路由、访问认证中间件、SSE 流式事件推送
- **生命周期**：启动时初始化 MemoryManager、Mem0Bridge、LangGraph 工作流
- **认证**：双级密钥（`X-Access-Key` / `X-Admin-Key`），不配置则开放访问
- **流式处理**：使用 `StreamingResponse` + `text/event-stream`，逐 token 推送回复
- **用户管理**：用户列表从 SQLite 数据库读取，确保与记忆存储一致

#### `emotion_graph.py` — LangGraph 工作流

- **职责**：定义三 Agent 工作流图、Agent Prompt、流式执行逻辑
- **工作流节点**：`emotion_analysis` ∥ `memory_retrieval` → `dialogue_generation` → `memory_storage`
- **并行优化**：情感分析与记忆检索通过 `asyncio.gather()` 并行执行
- **流式输出**：使用 `asyncio.Queue` 实现真正的逐 token 流式生成
- **长对话优化**：超过 30 轮对话自动生成摘要，避免上下文溢出

#### `memory_manager.py` — 记忆系统核心

- **EbbinghausCurve**：艾宾浩斯遗忘曲线 `R = e^(-t/S)`，含记忆巩固检测和重要性衰减
- **EmbeddingService**：调用智谱 Embedding API 生成语义向量，单例模式，支持批量处理，API 不可用时自动降级
- **EmotionAnalyzer**：基于关键词的情感分析器，识别 11 种情感标签 + 程度副词/否定词处理
- **ImportanceScorer**：多维度记忆重要性评分（情感强度 0.4 + 信息密度 0.3 + 用户关注度 0.2 + 内容长度 0.1）
- **MemoryManager**：记忆的增删查改，增量写入（`_dirty` 追踪），语义匹配 + 关键词匹配双路检索，自动遗忘清理
- **Mem0Bridge**：与 Mem0 云端的桥接适配器，联合检索 + 事实提取（规则 + LLM 双路）+ 三级保障
- **持久化**：SQLite（`giftia.db`）存储，WAL 模式，增量写入，线程安全

#### `llm_config.py` — LLM 客户端工厂

- **职责**：创建统一的 `ChatOpenAI` 实例
- **模型特性自动注入**：根据 `MODEL_PROFILES` 配置自动设置 thinking、reasoning_effort 等参数
- **温度参数处理**：启用 thinking 模式时自动 `temperature=1.0`，移除 `top_p`
- **节点级 thinking 控制**：情感分析和记忆检索节点关闭 thinking（加速），对话生成节点保持 thinking（质量）

#### `model_config.py` — 模型配置中心

- **职责**：集中管理模型名称、URL、API Key 映射、模型特性
- **设计原则**：`.env` 只存 API Key，模型切换只改 `CHAT_MODEL` 和 `CHAT_BASE_URL`
- **Provider 自动检测**：根据模型名/URL 自动识别提供商并匹配 API Key
- **Embedding 独立配置**：`EMBED_PROVIDER` 确保向量服务与对话模型解耦

---

## 核心算法：艾宾浩斯遗忘曲线

Giftia 的记忆系统模拟了人类记忆的衰减与巩固过程，核心公式为：

```
R = e^(-t/S)
```

- **R**：记忆保留率（0-1）
- **t**：经过时间（小时）
- **S**：记忆强度系数，由三部分组成：
  - 基础强度 `0.3`
  - 重要性加成 `importance × 0.5`
  - 复习次数加成 `min(access_count × 0.15, 1.0)`（间隔重复效应）

### 记忆生命周期

1. **编码**：从对话中提取关键事实 → 情感标注 → 重要性评分 → 生成语义向量 → 提取关键词标签
2. **存储**：Mem0 云端 + 本地 SQLite 双写，增量持久化
3. **检索**：语义匹配（余弦相似度 × 0.7 + 重要性 × 0.3）→ 关键词匹配（fallback）→ 最近记忆兜底
4. **衰减**：随时间推移，保留率下降；高重要性、多次复习的记忆衰减更慢
5. **巩固**：当保留率低于 0.3 阈值时触发巩固，巩固后记忆更稳定
6. **清理**：记忆数 > 50 时自动触发遗忘曲线清理，保留率 < 0.1 且未巩固的记忆被移除

---

## API 接口

### 对话接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| `POST` | `/api/chat/{user_id}` | 发送消息（SSE 流式返回） | Access Key |
| `GET` | `/api/conversations/{user_id}` | 获取对话列表 | Access Key |
| `GET` | `/api/conversations/{user_id}/{conv_id}` | 获取对话详情 | Access Key |
| `POST` | `/api/conversations/{user_id}` | 新建对话 | Access Key |
| `PATCH` | `/api/conversations/{user_id}/{conv_id}` | 重命名对话 | Access Key |
| `DELETE` | `/api/conversations/{user_id}/{conv_id}` | 删除对话 | Access Key |

### 用户与记忆接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| `GET` | `/api/users` | 获取用户列表（从 SQLite 读取） | Access Key |
| `POST` | `/api/users?user_id=xxx` | 创建用户 | Access Key |
| `GET` | `/api/memory/{user_id}/stats` | 获取记忆统计 | Access Key |
| `DELETE` | `/api/memory/{user_id}` | 清除所有记忆 | Access Key |

### 配置与系统接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| `GET` | `/api/config/model` | 获取当前模型配置 | Access Key |
| `GET` | `/api/config/model-presets` | 获取预设模型列表 | Access Key |
| `GET` | `/api/config/prompt` | 获取当前人设 Prompt | Access Key |
| `PUT` | `/api/config/prompt` | 修改人设 Prompt | Admin Key |
| `GET` | `/api/logs` | 获取服务日志 | Admin Key |
| `GET` | `/api/health` | 健康检查 | 无 |

### SSE 事件格式

对话接口返回的 SSE 事件包含以下类型：

```json
{"type": "status", "text": "Giftia 正在感受你的情绪并回忆..."}
{"type": "status", "text": "Giftia 正在组织语言..."}
{"type": "token", "text": "你"}
{"type": "reply", "text": "完整的回复文本"}
{"type": "done", "conversation_id": "uuid"}
{"type": "error", "text": "错误信息"}
```

---

## 开发指南

### 获取最新代码

```bash
git pull origin main
```

### 安装依赖

```bash
# Python 依赖
pip install -r requirements.txt

# 前端依赖
cd frontend && npm install
```

### 启动开发环境

```bash
# 后端（支持热重载）
python backend/server.py

# 前端（HMR 热更新）
cd frontend && npm run dev
```

### 运行单元测试

```bash
cd backend
python -m pytest tests/ -v
```

测试覆盖内容：
- 艾宾浩斯遗忘曲线（保留率计算、衰减、巩固判断）
- Provider 自动检测（模型名/URL 识别）
- 模型特性配置（精确匹配 / 前缀匹配）
- 情感类型枚举（中英文映射、Emoji 转换）
- MemoryItem 序列化与反序列化

### 构建前端生产版本

```bash
cd frontend
npm run build
```

构建产物输出到 `frontend/dist/`，可直接部署到静态服务器，配合后端 API 使用。

### 代码质量

```bash
# TypeScript 类型检查 + 构建
npm run build

# ESLint 代码检查
npm run lint

# Prettier 代码格式化
npm run format
```

### 提交规范

- 提交前运行 `npm run lint` 和 `npm run build` 确保代码质量
- 后端修改后运行 `python -m pytest tests/ -v` 确保测试通过
- Commit message 使用中文或英文，简要描述改动内容

---

## 常见问题

### Q: 启动后端报错「未找到 API Key」？

A: 检查 `.env` 文件是否存在于项目根目录，确保至少配置了当前模型对应的 API Key。系统会根据 `model_config.py` 中的 `CHAT_BASE_URL` 自动识别提供商并匹配对应的 Key。

### Q: 前端访问后端报 CORS 错误？

A: 开发模式下，Vite 已配置 `/api` 代理到 `http://127.0.0.1:8000`，确保前端通过 `http://localhost:3000` 访问。如果是其他部署方式，可在 `.env` 中配置 `CORS_ORIGINS`。

### Q: AI 回复出现幻觉（编造信息）？

A: Giftia 的 Prompt 中已内置了严格的反幻觉规则（「绝对禁止编造」「宁可装傻，绝不瞎猜」）。但如果仍然出现，可以：
1. 检查模型是否启用了 thinking 模式（DeepSeek 默认启用），thinking 模式会显著减少幻觉。
2. 在「自定义人设」中进一步加强反幻觉约束。
3. 尝试切换到推理能力更强的模型。

### Q: 记忆功能不工作，跨会话后 AI 忘记之前聊过什么？

A: 检查以下配置：
1. `.env` 中是否配置了 `MEM0_API_KEY`（云端记忆检索的核心依赖）
2. `.env` 中是否配置了 `ZHIPU_API_KEY`（本地语义检索 + Embedding 的依赖）
3. 如果两者都未配置，系统使用关键词匹配 + 最近记忆回退作为兜底，但准确性会降低。
4. 查看后端日志中的 `[记忆检索]` 和 `[DEBUG]` 信息排查。

### Q: 切换模型后 Embedding 报 401 错误？

A: Embedding 服务使用独立的 `EMBED_PROVIDER` 配置（默认 `zhipu`），与对话模型解耦。确保 `.env` 中配置了 `ZHIPU_API_KEY`，即使对话模型用的是 DeepSeek。

### Q: 流式回复卡住不动？

A: 可能原因：
1. LLM API 超时或限流，检查后端日志。
2. 网络问题导致 SSE 连接中断，刷新页面重试。
3. 对话历史过长导致上下文溢出，可以开启新对话。

### Q: 上传图片后模型不识别？

A: 只有多模态模型才支持图片。当前支持的模型包括 GLM-4.6V、GPT-4o 等。检查 `model_config.py` 中配置的模型是否在多模态白名单中。如果模型支持多模态但无法上传图片，需修改 `file_processor.py` 中的 `is_multimodal_model` 函数。

### Q: 如何备份数据？

A: 所有数据存储在 `backend/giftia.db`（SQLite 数据库）中，直接复制该文件即可备份。对话和记忆数据均在其中。

---

## 贡献指南

欢迎一切形式的贡献！无论是 Bug 报告、功能建议、代码贡献还是文档改进。

### 提交 Bug

如果你发现了 Bug，请在 GitHub Issues 中提交，并包含以下信息：

- Bug 的简要描述
- 复现步骤
- 预期行为 vs 实际行为
- 运行环境（Python 版本、Node 版本、操作系统）
- 相关的后端日志截图

### 提交功能建议

在 GitHub Issues 中使用 Feature Request 标签，描述：

- 功能的使用场景
- 期望的交互方式
- 是否有参考项目或设计

### 提交代码

1. Fork 本项目
2. 创建功能分支：`git checkout -b feature/your-feature-name`
3. 提交代码：`git commit -m '描述你的改动'`
4. 推送到分支：`git push origin feature/your-feature-name`
5. 创建 Pull Request

PR 提交前请确保：
- 前端代码通过 ESLint 检查（`npm run lint`）
- 前端构建成功（`npm run build`）
- 后端单元测试通过（`python -m pytest tests/ -v`）

### 作者

本项目由 Wenbo-Zhang 开发和维护。
联系邮箱：b1792674209@126.com

---

## License

本项目采用 [MIT License](./LICENSE) 开源，你可以自由使用、修改和分发。

Copyright (c) 2025 Giftia
