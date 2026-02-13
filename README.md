# arxivAgent - 智能论文推荐工具

## 项目介绍

arxivAgent是一个基于LLM的arXiv论文推荐工具，专为计算机科学方向的研究生设计。它能够根据用户的兴趣点，利用大型语言模型从arXiv论文库中智能筛选和推荐用户可能感兴趣的论文。

## 核心功能

### 🤖 智能推荐
- 基于LLM的论文筛选和推荐
- 双重推荐依据：用户初始兴趣点 + 收藏列表总结
- 单篇论文判断机制，确保推荐精准度

### 📚 论文管理
- 收藏列表管理（支持分页查看）
- 稍后再说功能
- 增量式收藏总结
- 论文详情查看（点击标题展开完整信息）
- 自动生成推荐理由（解释为什么推荐该论文）
- 中文标题、摘要和推荐理由持久化存储

### ⚙️ 个性化配置
- LLM API配置（支持OpenAI兼容接口）
- arXiv分类选择（支持所有CS子分区）
- 用户兴趣点精炼
- 收藏总结自动更新
- 实时显示待评估论文进度（导航栏指示器）

### 🔄 自动化维护
- 定期论文爬取（时间窗口管理）
- 缓存清理功能
- 状态监控和配置检查

## 技术架构

### 后端技术栈
- **框架**: Flask (Python)
- **数据库**: SQLite
- **LLM集成**: OpenAI API兼容接口
- **爬虫**: arXiv官方API

### 前端技术栈
- **核心**: HTML5 + CSS3 + Vanilla JavaScript
- **响应式设计**: 移动端适配
- **用户体验**: 流畅的交互动画

## 快速开始

### 1. 环境准备
```bash
# 克隆项目
git clone <repository-url>
cd arxivAgent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 启动应用
```bash
# 方式一：使用启动脚本
./run.sh

# 方式二：直接运行
python app.py
```

### 3. 访问应用
打开浏览器访问：http://localhost:5001

> 注：如果使用了其他端口配置，请替换为对应的端口号

## 首次使用指南

### 1. 配置LLM
# arxivAgent — 智能论文推荐工具

简要说明：arxivAgent 使用爬虫抓取 arXiv 论文并通过配置的 LLM（大型语言模型）对论文进行评估与排序，向用户推送推荐论文、生成推荐理由与中文翻译，并支持基本的论文库管理操作。

主要面向：研究人员 / 研究生，关注计算机科学方向的论文推荐与日常管理。

---

## 亮点功能
- 智能推荐：基于用户兴趣与收藏摘要，由 LLM 判定并生成“推荐理由”。
- 翻译与持久化：对被推荐的论文生成中文标题与摘要并保存到数据库。
- 论文管理：收藏、稍后再说、不感兴趣（dislike）、批量操作与分页浏览。
- 后台评估：可在服务启动时或手动触发对未评估论文的 LLM 批量评估。
- 可配置：通过设置页面配置 LLM、兴趣点与关注的 arXiv 子分区。

---

## 快速开始（开发 / 本地运行）

1. 克隆仓库并进入目录：

```bash
git clone <repo-url>
cd arxivAgent
```

2. 创建并激活 Python 虚拟环境：

```bash
python -m venv venv
source venv/bin/activate   # macOS / Linux
# venv\Scripts\activate  # Windows
```

3. 安装依赖：

```bash
pip install -r requirements.txt
```

4. 运行应用：

```bash
./run.sh      # 或： python app.py
```

5. 在浏览器打开：

http://localhost:5001

---

## 初次配置（使用步骤）

1. 打开 `设置`：配置 LLM（Base URL、API Key、Model），并点击“测试连接”。
2. 在“研究兴趣”中填写并保存您的研究方向（系统会调用 LLM 精炼兴趣点）。
3. 在“关注分类”选择需要抓取的 arXiv 子分区。
4. 切换到“论文库”或“推荐”开始使用：
   - 推荐页：逐条查看 LLM 推荐、理由、中文翻译，并使用“喜欢/不喜欢/稍后再说”。
   - 论文库：使用筛选（未评估/已评估/未读/喜欢/不喜欢/稍后）和分页管理全量论文。

提示：系统会在后台对未评估论文进行评估（需在启动时配置 LLM），并在导航栏显示“未读”（已评估且被推荐但未被用户处理的数量）与“正在处理”（待评估数量）。

---

## 常用 CLI / API（快速参考）

- 启动爬取（管理界面或 API）：
  - 管理界面按钮（论文库 -> 抓取最新论文）
  - API：`POST /api/admin/crawl-now` 或 `POST /api/system/crawl-now`

- 推荐与反馈：
  - `GET /api/recommendation/next` — 获取下一篇推荐
  - `POST /api/recommendation/feedback` — 提交用户反馈（favorite / maybe_later / dislike）

- 管理论文：
  - `GET /api/admin/papers?status=unread&page=1&per_page=50` — 管理界面分页（注意：`unread` = 已由LLM评估且被推荐，但用户未标记）
  - `POST /api/admin/delete-unprocessed` — 删除所有未处理的论文（未被评估且未被用户标记）
  - `POST /api/admin/delete-others` — 删除除了收藏和稍后再说之外的所有论文
  - `POST /api/admin/mark-unread-read` — 将所有未读论文标记为已读

- 状态：
  - `GET /api/recommendation/status` — 返回 { pending, recommended_unseen, last_run, last_evaluated_count }

更多接口详见代码中的路由（`app.py`）。

---

## 数据与行为说明（重要）

- 数据库：SQLite（默认位于 `data/`）。主要表 `papers`，包含论文元信息、LLM 评估标记、推荐理由、中文翻译及用户标记。
- 未读定义：`llm_evaluated = 1` 且 `is_recommended = 1`，并且未被用户标记为 `favorite` / `maybe_later` / `disliked`。
- 去重策略：使用 `INSERT OR IGNORE` 和 `arxiv_id` 唯一索引避免重复爬取相同论文。

---

## 开发人员说明

- 主要代码位置：
  - 后端入口：`app.py`
  - 爬虫：`services/arxiv_service.py`
  - LLM 调用：`services/llm_service.py`
  - 推荐逻辑：`services/recommendation_service.py`
  - 数据库工具：`utils/database.py`
  - 前端：`templates/index.html`、`static/js/*`、`static/css/*`

- 本地调试提示：
  - 更改 LLM 配置后若需要立即触发评估，可重启服务或手动通过管理接口触发评估逻辑。

---

## 贡献与支持

欢迎通过 Issues 或 Pull Requests 贡献改进建议或补丁。

---

许可证：MIT
