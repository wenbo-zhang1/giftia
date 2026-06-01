# 贡献指南 — 吉芙提尔 (giftia)

感谢你对 **吉芙提尔 (giftia)** 的关注！吉芙提尔是一个 AI 情感陪伴助手，拥有基于艾宾浩斯遗忘曲线的长期记忆系统。我们欢迎一切形式的贡献：Bug 报告、功能建议、代码提交、文档改进。

---

## 开发环境搭建

### 前置要求

- **Python** 3.11+
- **Node.js** 18+
- **npm** 9+（或 pnpm）
- **Git**

### 克隆与安装

```bash
git clone https://github.com/wenbo-zhang1/giftia.git
cd Giftia
```

**后端依赖：**

```bash
pip install -r requirements.txt
```

**前端依赖：**

```bash
cd frontend
npm install
```

### 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入至少一个 LLM API Key（如 `DEEPSEEK_API_KEY`），以及 `EMBEDDING_API_KEY`（用于语义记忆检索）。

### 启动开发环境

```bash
# 终端 1：启动后端（FastAPI + Uvicorn）
cd backend
python server.py

# 终端 2：启动前端（Vite HMR）
cd frontend
npm run dev
```

- 后端默认运行在 `http://127.0.0.1:8000`
- 前端默认运行在 `http://localhost:3000`
- API 文档：`http://127.0.0.1:8000/docs`

---

## 代码风格

### 前端 (TypeScript / React)

本项目使用 **ESLint + Prettier** 进行代码规范检查与格式化。

- ESLint 配置文件：[frontend/eslint.config.js](file:///f:/train%20of%20agent/frontend/eslint.config.js)
- Prettier 配置文件：[frontend/.prettierrc](file:///f:/train%20of%20agent/frontend/.prettierrc)

```bash
# 代码检查
npm run lint

# 自动格式化
npm run format

# 类型检查 + 构建（同时校验 TypeScript 类型）
npm run build
```

**规则概要：**

- 使用 2 空格缩进
- 使用单引号
- 行末不加分号
- 组件文件使用 PascalCase（如 `ChatArea.tsx`）
- 工具/类型文件使用 camelCase（如 `api.ts`、`types.ts`）
- CSS 文件与对应组件同名（如 `ChatArea.css`）
- 优先使用函数组件 + Hooks，避免 class 组件

### 后端 (Python)

使用 **pytest** 作为测试框架。

```bash
cd backend
python -m pytest tests/ -v
```

**规则概要：**

- 遵循 PEP 8 风格
- 使用 4 空格缩进
- 函数/变量使用 snake_case
- 类使用 PascalCase
- 类型注解优先（已有部分模块使用）
- 异步接口使用 `async/await`

---

## 提交信息规范

提交信息可使用**中文或英文**，格式为：

```
<类型>: <简要描述>
```

**类型（type）示例：**

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | 修复 Bug |
| `refactor` | 重构（不改变功能） |
| `docs` | 文档修改 |
| `style` | 代码格式（不影响逻辑） |
| `test` | 测试相关 |
| `chore` | 构建/依赖/工具变更 |

**示例：**

```
feat: 支持 Claude 模型接入
fix: 修复长对话上下文溢出问题
docs: 更新 API 接口文档
refactor: 抽取记忆评分逻辑为独立模块
```

---

## 分支命名规范

| 分支类型 | 命名格式 | 示例 |
|----------|----------|------|
| 功能分支 | `feature/<描述>` | `feature/multi-model-support` |
| 修复分支 | `fix/<描述>` | `fix/memory-leak` |
| 重构分支 | `refactor/<描述>` | `refactor/emotion-analyzer` |
| 文档分支 | `docs/<描述>` | `docs/api-reference` |

---

## Pull Request 流程

1. **Fork** 本仓库到你的 GitHub 账号
2. 从 `main` 分支创建你的功能/修复分支
3. 在分支上进行开发
4. 提交前确保通过以下检查：
   - 前端：`npm run lint` 无错误
   - 前端：`npm run build` 构建成功
   - 后端：`python -m pytest tests/ -v` 全部通过
5. 推送分支并创建 Pull Request 到 `main` 分支
6. 填写 PR 模板中的描述信息

### PR 检查清单

- [ ] 代码通过 ESLint 检查（`npm run lint`）
- [ ] TypeScript 类型检查通过（`npm run build`）
- [ ] 后端测试通过（`python -m pytest tests/ -v`）
- [ ] 新功能有对应的测试（如适用）
- [ ] 文档已更新（如适用）
- [ ] Commit 信息清晰有意义

---

## 问题反馈

- **Bug 报告**：使用 [Bug Report](https://github.com/wenbo-zhang1/giftia/issues/new?template=bug_report.md) 模板
- **功能建议**：使用 [Feature Request](https://github.com/wenbo-zhang1/giftia/issues/new?template=feature_request.md) 模板

---

## 行为准则

本项目遵循 [贡献者公约 (Contributor Covenant v2.1)](./CODE_OF_CONDUCT.md)。参与本项目的所有人都应遵守其规定。

---

## 许可证

吉芙提尔 (giftia) 使用 [MIT License](./LICENSE) 开源。你贡献的代码也将以 MIT License 发布。
