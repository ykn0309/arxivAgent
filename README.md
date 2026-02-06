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
- 进入"设置"页面
- 配置LLM API（base_url, api_key, model）
- 点击"测试连接"确保配置正确

### 2. 设置研究兴趣
- 描述您的研究方向或技术兴趣
- 系统会使用LLM精炼为专业的兴趣点描述

### 3. 选择关注分类
- 从arXiv CS分区中选择感兴趣的子分区
- 系统提供各分区的详细介绍供参考

### 4. 开始使用
- 配置完成后即可开始推荐
- 系统会在后台自动爬取相关论文

## 使用说明

### 推荐页面
- 采用短视频式的卡片展示
- 每次显示一篇论文的详细信息
- 支持三种操作：喜欢、不喜欢、稍后再说
- 喜欢的论文会加入收藏列表
- 稍后再说的论文可在列表中重新评估
- 显示推荐理由（LLM生成的为什么推荐该论文）
- 展示中文标题和摘要翻译

### 列表管理
- **收藏列表**：查看所有标记为喜欢的论文
- **稍后再说**：管理暂时不确定的论文
- 支持分页浏览和删除操作
- 可将稍后再说的论文移动到收藏
- **论文详情查看**：点击论文标题展开详情面板，查看完整的中英文信息和推荐理由

### 设置管理
- **LLM配置**：管理语言模型API设置
- **兴趣点**：查看和修改研究兴趣
- **分类设置**：调整关注的arXiv分区
- **收藏总结**：查看基于收藏的自动总结
- **系统维护**：手动触发爬取和清理缓存

## API接口文档

### 配置管理
- `GET /api/config/status` - 获取配置状态
- `POST /api/config/llm` - 更新LLM配置
- `POST /api/config/llm/test` - 测试LLM连接
- `POST /api/config/interests` - 更新用户兴趣
- `POST /api/config/categories` - 更新关注分类

### 推荐系统
- `GET /api/recommendation/next` - 获取下一条推荐
- `POST /api/recommendation/feedback` - 提交用户反馈
- `GET /api/recommendation/status` - 获取待评估论文数量

### 列表管理
- `GET /api/list/favorites` - 获取收藏列表
- `GET /api/list/maybe-later` - 获取稍后再说列表
- `POST /api/list/move-to-favorite` - 移动到收藏
- `POST /api/list/delete-favorite` - 删除收藏
- `POST /api/list/delete-maybe-later` - 删除稍后再说

### 列表管理（实现细节）
- 列表接口仍然可用用于查看和管理收藏/稍后再说的论文，但在实现层面，用户的标记现在统一存储在 `papers.user_status` 字段中（取值：`none`、`favorite`、`maybe_later`、`dislike`）。
- 现有 API：`GET /api/list/favorites`、`GET /api/list/maybe-later` 等行为不变，但它们查询的是 `papers` 表中的 `user_status` 字段，而不再依赖独立的 `favorites` / `maybe_later` 表。
- 对外接口：
- `POST /api/list/move-to-favorite` - 将指定 `paper_id` 的论文标记为 `favorite`
- `POST /api/list/delete-favorite` - 将指定 `paper_id` 的论文标记回 `none`
- `POST /api/list/delete-maybe-later` - 将指定 `paper_id` 的论文标记回 `none`

### 系统维护
- `POST /api/system/clean-cache` - 清理缓存
- `POST /api/system/crawl-now` - 立即爬取

## 数据库结构

### 主要表结构
- **papers**: 存储爬取的论文信息（包含用户标记）
  - 新增字段: `recommendation_reason`（推荐理由）、`chinese_title`（中文标题）、`chinese_abstract`（中文摘要）
  - 用户标记字段: `user_status`（字符串，取值：`none`、`favorite`、`maybe_later`、`dislike`），用于替代历史上的独立 `favorites` / `maybe_later` 表
- **config**: 系统配置信息

## 开发指南

### 项目结构
```
arxivAgent/
├── app.py                  # Flask主应用
├── config.py              # 配置文件
├── requirements.txt       # Python依赖
├── models/                # 数据模型
│   ├── paper.py          # 论文相关模型
│   └── user.py           # 用户相关模型
├── services/              # 业务服务
│   ├── arxiv_service.py  # arXiv爬虫服务
│   ├── llm_service.py    # LLM服务
│   └── recommendation_service.py  # 推荐服务
├── utils/                 # 工具类
│   └── database.py       # 数据库工具
├── templates/             # HTML模板
│   └── index.html
├── static/                # 静态资源
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── api.js
│       └── main.js
└── data/                  # 数据文件
    └── arxiv_agent.db    # SQLite数据库
```

### 扩展开发
1. **添加新的推荐算法**：修改`recommendation_service.py`
2. **扩展LLM支持**：在`llm_service.py`中添加新的模型支持
3. **自定义爬虫逻辑**：修改`arxiv_service.py`
4. **前端功能增强**：在`static/js/`目录下添加新功能

## 常见问题

### Q: 推荐的论文为什么推荐它？
A: 进行推荐时，系统会生成该论文的推荐理由。可以在以下位置查看：
- 推荐页面：卡片中直接显示推荐理由
- 列表页面：点击论文标题打开详情面板，查看完整的推荐理由说明

### Q: 如何查看论文的中文标题和摘要？
A: 系统会在推荐过程中自动生成中文翻译，并保存到数据库。可通过以下方式查看：
- 推荐页面：标题和摘要会以中英对照形式显示
- 列表页面：点击论文标题打开详情面板，查看完整的中英文翻译

### Q: 推荐结果不准确怎么办？
A: 可以尝试：
- 重新精炼用户兴趣点描述
- 调整关注的arXiv分类
- 更新收藏列表总结

### Q: 爬取不到最新论文？
A: 检查：
- arXiv API是否正常
- 网络连接是否稳定
- 时间窗口设置是否合理

### Q: LLM调用失败？
A: 确认：
- API密钥是否正确
- 基础URL是否可达
- 模型名称是否支持

## 贡献指南

欢迎提交Issue和Pull Request来改进项目！

## 许可证

MIT License

## 联系方式

如有问题或建议，请通过GitHub Issues联系。
