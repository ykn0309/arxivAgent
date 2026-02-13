// 主要应用逻辑
class ArxivAgentApp {
    constructor() {
        this.currentTab = 'recommendation';
        this.currentListTab = 'favorites';
        this.adminPage = 1;
        this.currentPaper = null;
        this._statusInterval = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this._bindAdminEvents();
        // 初始化列表子标签的激活状态（确保默认选中收藏）
        document.querySelectorAll('.list-tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.list === this.currentListTab);
        });
        document.querySelectorAll('.list-content').forEach(content => {
            content.classList.toggle('active', content.id === `${this.currentListTab}-list`);
        });
        this.loadInitialData();
        this.loadAdminPanel();
        // 每 30 秒刷新一次推荐进度（仅数字），不刷新推荐卡片
        this._statusInterval = setInterval(() => this.loadRecommendationStatus(), 30000);
    }

    // 可用于在需要时停止自动刷新
    stopStatusAutoRefresh() {
        if (this._statusInterval) {
            clearInterval(this._statusInterval);
            this._statusInterval = null;
        }
    }

    bindEvents() {
        // 导航标签切换
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tab = e.target.dataset.tab;
                this.switchTab(tab);
            });
        });

        // 列表标签切换
        document.querySelectorAll('.list-tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const list = e.target.dataset.list;
                this.switchListTab(list);
            });
        });

        // 推荐操作按钮
        document.querySelectorAll('.action-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.target.closest('.action-btn').dataset.action;
                this.handlePaperAction(action);
            });
        });

        // 表单提交事件
        document.getElementById('llm-config-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveLLMConfig();
        });

        document.getElementById('interests-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveUserInterests();
        });

        document.getElementById('categories-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveCategories();
        });

        // 测试按钮
        document.getElementById('test-llm-btn').addEventListener('click', () => {
            this.testLLM();
        });

        // 更新总结按钮
        document.getElementById('update-summary-btn').addEventListener('click', () => {
            this.updateFavoriteSummary();
        });

        document.getElementById('save-summary-btn').addEventListener('click', () => {
            this.saveFavoriteSummary();
        });

        // 维护按钮（存在检查以防在某些视图中被移除）
        const crawlNowBtn = document.getElementById('crawl-now-btn');
        if (crawlNowBtn) crawlNowBtn.addEventListener('click', () => { this.crawlNow(); });

        const cleanCacheBtn = document.getElementById('clean-cache-btn');
        if (cleanCacheBtn) cleanCacheBtn.addEventListener('click', () => { this.cleanCache(); });

        // 刷新推荐按钮
        document.getElementById('refresh-recommendation').addEventListener('click', () => {
            this.loadNextRecommendation();
        });

        // note-modal 已移除，相关事件处理不再需要

        // 点击模态框外部关闭
        // 点击模态框外部关闭（若有其他模态框，可继续保留此行为）
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.classList.remove('active');
                }
            });
        });

        // 论文详情模态框关闭按钮
        const paperDetailCloseBtn = document.getElementById('paper-detail-close');
        if (paperDetailCloseBtn) {
            paperDetailCloseBtn.addEventListener('click', () => {
                this.closePaperDetail();
            });
        }
    }

    async loadInitialData() {
        await this.loadConfigStatus();
        await this.loadSettingsData();
        await this.loadRecommendationStatus();
        this.loadNextRecommendation();
    }

    async loadRecommendationStatus() {
        try {
            const resp = await api.getRecommendationStatus();
            if (resp.success && resp.data) {
                const rec_unseen = resp.data.recommended_unseen || 0;
                const pending = resp.data.pending || 0;
                const el = document.getElementById('recommendation-remaining');
                const processingEl = document.getElementById('recommendation-processing');
                if (el) el.textContent = `${rec_unseen}`; // 只显示已评估但未标记的数量
                if (processingEl) processingEl.textContent = `${pending}`;
            }
        } catch (e) {
            console.error('加载推荐进度失败:', e);
        }
    }

    // 标签页切换
    switchTab(tabName) {
        // 更新导航按钮状态
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        // 显示对应内容
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === `${tabName}-tab`);
        });

        this.currentTab = tabName;

        // 加载相应数据
        if (tabName === 'list') {
            this.loadListData();
        } else if (tabName === 'settings') {
            this.loadSettingsData();
        }
    }

    switchListTab(listName) {
        // 更新列表标签状态
        document.querySelectorAll('.list-tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.list === listName);
        });

        // 显示对应列表
        document.querySelectorAll('.list-content').forEach(content => {
            content.classList.toggle('active', content.id === `${listName}-list`);
        });

        this.currentListTab = listName;
        this.loadListData();
    }

    // 配置状态管理
    async loadConfigStatus() {
        try {
            const response = await api.getConfigStatus();
            if (response.success) {
                const status = response.data;
                
                document.getElementById('llm-status').textContent = 
                    status.llm_configured ? '✅ 已配置' : '❌ 未配置';
                document.getElementById('llm-status').className = 
                    `status-value ${status.llm_configured ? 'configured' : 'not-configured'}`;
                
                document.getElementById('interests-status').textContent = 
                    status.interests_configured ? '✅ 已配置' : '❌ 未配置';
                document.getElementById('interests-status').className = 
                    `status-value ${status.interests_configured ? 'configured' : 'not-configured'}`;
                
                document.getElementById('categories-status').textContent = 
                    status.categories_configured ? '✅ 已配置' : '❌ 未配置';
                document.getElementById('categories-status').className = 
                    `status-value ${status.categories_configured ? 'configured' : 'not-configured'}`;
            }
        } catch (error) {
            console.error('加载配置状态失败:', error);
        }
    }

    // 设置页面数据加载
    async loadSettingsData() {
        await Promise.all([
            this.loadLLMConfig(),
            this.loadUserInterests(),
            this.loadCategories(),
            this.loadFavoriteSummary()
        ]);
    }

    async loadLLMConfig() {
        try {
            const response = await api.getLLMConfig();
            if (response.success) {
                const config = response.data;
                document.getElementById('llm-base-url').value = config.base_url || '';
                document.getElementById('llm-model').value = config.model || '';
            }
        } catch (error) {
            console.error('加载LLM配置失败:', error);
        }
    }

    async loadUserInterests() {
        try {
            const response = await api.getUserInterests();
            if (response.success) {
                const data = response.data;
                if (data.interests) {
                    document.getElementById('refined-interests').innerHTML = 
                        `<p>${data.interests}</p>`;
                }
            }
        } catch (error) {
            console.error('加载用户兴趣失败:', error);
        }
    }

    async loadCategories() {
        try {
            const response = await api.getCategories();
            if (response.success) {
                const data = response.data;
                this.renderCategoryOptions(data.all_categories, data.current_categories);
            }
        } catch (error) {
            console.error('加载分类失败:', error);
        }
    }

    async loadFavoriteSummary() {
        try {
            const response = await api.getFavoriteSummary();
            if (response.success) {
                const data = response.data;
                document.getElementById('favorite-summary').value = data.summary || '';
            }
        } catch (error) {
            console.error('加载收藏总结失败:', error);
        }
    }

    renderCategoryOptions(allCategories, currentCategories) {
        const container = document.getElementById('categories-list');
        container.innerHTML = '';

        // 创建分类代码到中文名称的映射（使用更简洁的名称）
        const categoryNames = {
            'cs.AI': '人工智能',
            'cs.AR': '硬件架构',
            'cs.CC': '计算复杂性',
            'cs.CE': '计算工程',
            'cs.CG': '计算几何',
            'cs.CL': '自然语言处理',
            'cs.CR': '密码安全',
            'cs.CV': '计算机视觉',
            'cs.CY': '计算机社会',
            'cs.DB': '数据库',
            'cs.DC': '分布式计算',
            'cs.DL': '数字图书馆',
            'cs.DM': '离散数学',
            'cs.DS': '数据结构',
            'cs.ET': '新兴技术',
            'cs.FL': '形式语言',
            'cs.GL': '综合通论',
            'cs.GR': '计算机图形',
            'cs.GT': '博弈论',
            'cs.HC': '人机交互',
            'cs.IR': '信息检索',
            'cs.IT': '信息论',
            'cs.LG': '机器学习',
            'cs.LO': '程序逻辑',
            'cs.MA': '多智能体',
            'cs.MM': '多媒体',
            'cs.MS': '数学软件',
            'cs.NA': '数值分析',
            'cs.NE': '神经计算',
            'cs.NI': '网络架构',
            'cs.OH': '其他CS',
            'cs.OS': '操作系统',
            'cs.PF': '性能分析',
            'cs.PL': '编程语言',
            'cs.RO': '机器人学',
            'cs.SC': '符号计算',
            'cs.SD': '音频计算',
            'cs.SE': '软件工程',
            'cs.SI': '社会网络',
            'cs.SY': '系统控制'
        };

        // 按字母顺序排序分类
        const sortedCategories = Object.entries(allCategories).sort((a, b) => a[0].localeCompare(b[0]));

        sortedCategories.forEach(([code, description]) => {
            const isSelected = currentCategories.includes(code);
            const categoryName = categoryNames[code] || code;
            
            const label = document.createElement('label');
            label.className = `category-option ${isSelected ? 'selected' : ''}`;
            label.style.cursor = 'pointer';
            label.title = description;
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.checked = isSelected;
            checkbox.style.cursor = 'pointer';
            checkbox.style.marginRight = '8px';
            
            const span = document.createElement('span');
            span.textContent = categoryName;
            span.style.flex = '1';
            span.style.overflow = 'hidden';
            span.style.textOverflow = 'ellipsis';
            span.style.whiteSpace = 'nowrap';
            
            label.appendChild(checkbox);
            label.appendChild(span);
            
            label.addEventListener('change', () => {
                label.classList.toggle('selected', checkbox.checked);
            });
            
            container.appendChild(label);
        });
    }

    // 推荐功能
    async loadNextRecommendation() {
        const loadingEl = document.getElementById('card-loading');
        const contentEl = document.getElementById('card-content');
        const emptyEl = document.getElementById('card-empty');

        loadingEl.style.display = 'flex';
        contentEl.style.display = 'none';
        emptyEl.style.display = 'none';

        try {
            const response = await api.getNextRecommendation();
            if (response.success) {
                if (response.data) {
                    this.currentPaper = response.data;
                    this.displayPaperCard(response.data);
                    loadingEl.style.display = 'none';
                    contentEl.style.display = 'flex';
                } else {
                    // 没有更多推荐
                    loadingEl.style.display = 'none';
                    emptyEl.style.display = 'flex';
                }
            }
        } catch (error) {
            console.error('加载推荐失败:', error);
            utils.showNotification('加载推荐失败: ' + error.message, 'error');
            loadingEl.style.display = 'none';
            emptyEl.style.display = 'flex';
        }
    }

    displayPaperCard(paper) {
        document.getElementById('paper-title').textContent = paper.title;
        document.getElementById('paper-abstract').textContent = paper.abstract;
        document.getElementById('paper-arxiv-link').href = paper.arxiv_url;
        document.getElementById('paper-pdf-link').href = paper.pdf_url;

        // 显示发表日期
        const publishedEl = document.getElementById('paper-published-date');
        if (publishedEl) {
            if (paper.published_date) {
                publishedEl.textContent = `📅 ${utils.formatDate(paper.published_date)}`;
                publishedEl.style.display = 'inline-block';
            } else {
                publishedEl.textContent = '';
                publishedEl.style.display = 'none';
            }
        }

        // 显示推荐理由
        const reasonEl = document.getElementById('paper-recommendation-reason');
        if (paper.recommendation_reason) {
            reasonEl.textContent = paper.recommendation_reason;
            reasonEl.parentElement.style.display = 'block';
        } else {
            reasonEl.parentElement.style.display = 'none';
        }

        // 显示中文翻译
        const chineseTitleEl = document.getElementById('paper-chinese-title');
        const chineseAbstractEl = document.getElementById('paper-chinese-abstract');
        
        if (paper.chinese_title) {
            chineseTitleEl.textContent = paper.chinese_title;
            chineseTitleEl.style.display = 'block';
        } else {
            chineseTitleEl.style.display = 'none';
        }
        
        if (paper.chinese_abstract) {
            chineseAbstractEl.textContent = paper.chinese_abstract;
            chineseAbstractEl.style.display = 'block';
        } else {
            chineseAbstractEl.style.display = 'none';
        }

        // 显示作者
        let authors = [];
        if (paper.authors) {
            try {
                authors = typeof paper.authors === 'string' ? JSON.parse(paper.authors) : paper.authors;
            } catch (e) {
                console.error('解析authors出错:', e);
            }
        }
        const authorsHtml = authors.length > 0 ? 
            `作者: ${authors.join(', ')}` : '作者信息不可用';
        document.getElementById('paper-authors').textContent = authorsHtml;

        // 显示分类标签
        const categoriesContainer = document.getElementById('paper-categories');
        categoriesContainer.innerHTML = '';
        let categories = [];
        if (paper.categories) {
            try {
                categories = typeof paper.categories === 'string' ? JSON.parse(paper.categories) : paper.categories;
            } catch (e) {
                console.error('解析categories出错:', e);
            }
        }
        if (categories.length > 0) {
            categories.forEach(cat => {
                const tag = document.createElement('span');
                tag.className = 'category-tag';
                tag.textContent = cat;
                categoriesContainer.appendChild(tag);
            });
        }
    }

    async handlePaperAction(action) {
        if (!this.currentPaper) return;

        // 不再弹出笔记模态框，直接发送反馈（user_note 为空）
        if (action === 'favorite' || action === 'maybe_later') {
            await this.sendPaperFeedback(this.currentPaper.id, action, '');
        } else {
            await this.sendPaperFeedback(this.currentPaper.id, action);
        }
    }

    async sendPaperFeedback(paperId, action, note = '') {
        try {
            utils.showLoading('处理反馈中...');
            await api.sendFeedback({
                paper_id: paperId,
                action: action,
                user_note: note
            });
            
            utils.hideLoading();
            utils.showNotification('反馈已处理', 'success');
            
            // 加载下一个推荐
            this.loadNextRecommendation();
            // 刷新剩余计数
            this.loadRecommendationStatus();
            
        } catch (error) {
            utils.hideLoading();
            utils.showNotification('处理反馈失败: ' + error.message, 'error');
        }
    }

    saveNote() {
        // note-modal 已移除，保存笔记功能被禁用
        return;
    }

    // 列表管理
    async loadListData() {
        if (this.currentListTab === 'favorites') {
            await this.loadFavorites();
        } else if (this.currentListTab === 'maybe-later') {
            await this.loadMaybeLater();
        } else if (this.currentListTab === 'library') {
            // 加载管理面板数据并渲染论文库（所有论文）
            await this.loadAdminPanel();
            await this.loadAdminPapers(1);
        }
    }

    async loadFavorites(page = 1) {
        try {
            console.log('加载收藏列表，页码:', page);
            const response = await api.getFavorites(page, 10);
            console.log('收藏列表API响应:', response);
            if (response.success) {
                this.renderPaperList('favorites-papers-list', response.data.papers);
                this.renderPagination('favorites-pagination', response.data.pagination);
            } else {
                console.error('API返回失败:', response.error);
            }
        } catch (error) {
            console.error('加载收藏列表失败:', error);
            utils.showNotification('加载收藏列表失败: ' + error.message, 'error');
        }
    }

    async loadMaybeLater(page = 1) {
        try {
            console.log('加载稍后再说列表，页码:', page);
            const response = await api.getMaybeLater(page, 10);
            console.log('稍后再说列表API响应:', response);
            if (response.success) {
                this.renderPaperList('maybe-later-papers-list', response.data.papers, true);
                this.renderPagination('maybe-later-pagination', response.data.pagination);
            } else {
                console.error('API返回失败:', response.error);
            }
        } catch (error) {
            console.error('加载稍后再说列表失败:', error);
            utils.showNotification('加载稍后再说列表失败: ' + error.message, 'error');
        }
    }

    renderPaperList(containerId, papers, isMaybeLater = false) {
        console.log(`渲染论文列表到 ${containerId}，论文数量:`, papers.length);
        console.log('论文数据:', papers);
        
        const container = document.getElementById(containerId);
        if (!container) {
            console.error('找不到容器元素:', containerId);
            return;
        }
        
        container.innerHTML = '';

        if (papers.length === 0) {
            container.innerHTML = '<p class="empty-list">暂无数据</p>';
            return;
        }

        papers.forEach(paper => {
            const paperElement = document.createElement('div');
            paperElement.className = 'paper-item';
            
            // 使用正确的 id 字段：
            // - 收藏列表包含 `favorite_id` 和 `paper_id`
            // - 稍后再说列表包含 `maybe_later_id` 和 `paper_id`
            const actionsHtml = isMaybeLater ? 
                `<button class="item-action-btn move-btn" data-paper-id="${paper.paper_id}">移到收藏</button>
                 <button class="item-action-btn delete-btn" data-paper-id="${paper.paper_id}">删除</button>` :
                `<button class="item-action-btn delete-btn" data-paper-id="${paper.paper_id}">删除</button>`;

            // 解析categories
            let categories = [];
            if (paper.categories) {
                try {
                    categories = typeof paper.categories === 'string' ? JSON.parse(paper.categories) : paper.categories;
                } catch (e) {
                    console.error('解析categories出错:', e);
                }
            }

            paperElement.innerHTML = `
                <div class="paper-item-header">
                    <h3 class="paper-item-title">${paper.title}</h3>
                    <div class="paper-item-actions">
                        ${actionsHtml}
                    </div>
                </div>
                <div class="paper-item-meta">
                    <span class="meta-item">📅 ${utils.formatDate(paper.published_date)}</span>
                    <span class="meta-item">🏷️ ${categories.length > 0 ? categories.join(', ') : ''}</span>
                </div>
                <div class="paper-item-abstract">${utils.truncateText(paper.abstract, 300)}</div>
            `;

            // 使论文项可点击查看详情
            const titleElement = paperElement.querySelector('.paper-item-title');
            titleElement.style.cursor = 'pointer';
            titleElement.addEventListener('click', (e) => {
                e.stopPropagation();
                this.showPaperDetail(paper);
            });

            // 绑定操作按钮事件
            paperElement.querySelectorAll('.delete-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const paperId = e.target.dataset.paperId;
                    if (paperId) {
                        if (isMaybeLater) this.deleteMaybeLater(paperId);
                        else this.deleteFavorite(paperId);
                    } else {
                        console.warn('未找到有效的删除 ID');
                    }
                });
            });

            if (isMaybeLater) {
                paperElement.querySelectorAll('.move-btn').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        const paperId = e.target.dataset.paperId;
                        this.moveToFavorite(paperId);
                    });
                });
            }

            container.appendChild(paperElement);
        });
    }

    renderPagination(containerId, pagination) {
        const container = document.getElementById(containerId);
        container.innerHTML = `
            <button class="pagination-btn" id="prev-btn" 
                    ${pagination.page <= 1 ? 'disabled' : ''}>上一页</button>
            <span class="page-info">第 ${pagination.page} 页，共 ${pagination.pages} 页</span>
            <button class="pagination-btn" id="next-btn" 
                    ${pagination.page >= pagination.pages ? 'disabled' : ''}>下一页</button>
        `;

        document.getElementById('prev-btn').addEventListener('click', () => {
            const newPage = pagination.page - 1;
            if (this.currentListTab === 'favorites') {
                this.loadFavorites(newPage);
            } else {
                this.loadMaybeLater(newPage);
            }
        });

        document.getElementById('next-btn').addEventListener('click', () => {
            const newPage = pagination.page + 1;
            if (this.currentListTab === 'favorites') {
                this.loadFavorites(newPage);
            } else {
                this.loadMaybeLater(newPage);
            }
        });
    }

    async moveToFavorite(paperId) {
        try {
            utils.showLoading('移动中...');
            await api.moveToFavorite(paperId);
            utils.hideLoading();
            utils.showNotification('已移动到收藏', 'success');
            this.loadListData();
        } catch (error) {
            utils.hideLoading();
            utils.showNotification('移动失败: ' + error.message, 'error');
        }
    }

    async deleteFavorite(favoriteId) {
        if (!confirm('确定要删除这篇收藏吗？')) return;
        
        try {
            utils.showLoading('删除中...');
            await api.deleteFavorite(favoriteId);
            utils.hideLoading();
            utils.showNotification('删除成功', 'success');
            this.loadListData();
        } catch (error) {
            utils.hideLoading();
            utils.showNotification('删除失败: ' + error.message, 'error');
        }
    }

    async deleteMaybeLater(maybeLaterId) {
        if (!confirm('确定要删除这条记录吗？')) return;
        
        try {
            utils.showLoading('删除中...');
            await api.deleteMaybeLater(maybeLaterId);
            utils.hideLoading();
            utils.showNotification('删除成功', 'success');
            this.loadListData();
        } catch (error) {
            utils.hideLoading();
            utils.showNotification('删除失败: ' + error.message, 'error');
        }
    }

    // 论文详情显示
    showPaperDetail(paper) {
        const modal = document.getElementById('paper-detail-modal');
        
        // 填充论文信息
        document.getElementById('paper-detail-title').textContent = paper.title;
        document.getElementById('paper-detail-abstract').textContent = paper.abstract;
        document.getElementById('paper-detail-arxiv-link').href = paper.arxiv_url;
        document.getElementById('paper-detail-pdf-link').href = paper.pdf_url;

        // 显示作者
        const authorsEl = document.getElementById('paper-detail-authors');
        if (paper.authors) {
            try {
                const authors = typeof paper.authors === 'string' ? JSON.parse(paper.authors) : paper.authors;
                authorsEl.textContent = '作者: ' + authors.join(', ');
            } catch (e) {
                authorsEl.textContent = '作者: ' + paper.authors;
            }
        }

        // 显示分类
        const categoriesEl = document.getElementById('paper-detail-categories');
        categoriesEl.innerHTML = '';
        if (paper.categories) {
            try {
                const categories = typeof paper.categories === 'string' ? JSON.parse(paper.categories) : paper.categories;
                categories.forEach(cat => {
                    const tag = document.createElement('span');
                    tag.className = 'category-tag';
                    tag.textContent = cat;
                    categoriesEl.appendChild(tag);
                });
            } catch (e) {
                console.error('解析分类出错:', e);
            }
        }

        // 显示推荐理由
        const reasonEl = document.getElementById('paper-detail-recommendation-reason');
        const reasonContainer = reasonEl.parentElement;
        if (paper.recommendation_reason) {
            reasonEl.textContent = paper.recommendation_reason;
            reasonContainer.style.display = 'block';
        } else {
            reasonContainer.style.display = 'none';
        }

        // 显示中文翻译（如果存在）
        const chineseTitleEl = document.getElementById('paper-detail-chinese-title');
        if (paper.chinese_title) {
            chineseTitleEl.textContent = paper.chinese_title;
            chineseTitleEl.style.display = 'block';
        } else {
            chineseTitleEl.style.display = 'none';
        }

        const chineseAbstractEl = document.getElementById('paper-detail-chinese-abstract');
        if (paper.chinese_abstract) {
            chineseAbstractEl.textContent = paper.chinese_abstract;
            chineseAbstractEl.parentElement.style.display = 'block';
        } else {
            chineseAbstractEl.parentElement.style.display = 'none';
        }

        // 显示论文发表日期
        const detailDateEl = document.getElementById('paper-detail-published-date');
        if (detailDateEl) {
            if (paper.published_date) {
                detailDateEl.textContent = `📅 ${utils.formatDate(paper.published_date)}`;
                detailDateEl.style.display = 'inline-block';
            } else {
                detailDateEl.textContent = '';
                detailDateEl.style.display = 'none';
            }
        }

        // 打开模态框
        modal.classList.add('active');
    }

    closePaperDetail() {
        const modal = document.getElementById('paper-detail-modal');
        modal.classList.remove('active');
    }

    // 设置保存功能
    async saveLLMConfig() {
        const baseUrl = document.getElementById('llm-base-url').value.trim();
        const apiKey = document.getElementById('llm-api-key').value.trim();
        const model = document.getElementById('llm-model').value.trim();

        if (!baseUrl || !apiKey || !model) {
            utils.showNotification('请填写所有必填字段', 'warning');
            return;
        }

        try {
            utils.showLoading('保存配置中...');
            await api.updateLLMConfig({ base_url: baseUrl, api_key: apiKey, model });
            utils.hideLoading();
            utils.showNotification('LLM配置已保存', 'success');
            this.loadConfigStatus();
        } catch (error) {
            utils.hideLoading();
            utils.showNotification('保存失败: ' + error.message, 'error');
        }
    }

    async testLLM() {
        try {
            utils.showLoading('测试连接中...');
            const response = await api.testLLMConnection();
            utils.hideLoading();
            
            if (response.success) {
                utils.showNotification(response.message, response.success ? 'success' : 'error');
            }
        } catch (error) {
            utils.hideLoading();
            utils.showNotification('测试失败: ' + error.message, 'error');
        }
    }

    async saveUserInterests() {
        const interests = document.getElementById('user-interests').value.trim();
        
        if (!interests) {
            utils.showNotification('请输入研究兴趣', 'warning');
            return;
        }

        try {
            utils.showLoading('处理中...');
            const response = await api.updateUserInterests(interests);
            utils.hideLoading();
            
            if (response.success) {
                document.getElementById('refined-interests').innerHTML = 
                    `<p>${response.data.refined_interests}</p>`;
                utils.showNotification('兴趣点已保存并精炼', 'success');
                this.loadConfigStatus();
            }
        } catch (error) {
            utils.hideLoading();
            utils.showNotification('保存失败: ' + error.message, 'error');
        }
    }

    async saveCategories() {
        const selectedCategories = [];
        const categoryNames = {
            '人工智能': 'cs.AI',
            '硬件架构': 'cs.AR',
            '计算复杂性': 'cs.CC',
            '计算工程': 'cs.CE',
            '计算几何': 'cs.CG',
            '自然语言处理': 'cs.CL',
            '密码安全': 'cs.CR',
            '计算机视觉': 'cs.CV',
            '计算机社会': 'cs.CY',
            '数据库': 'cs.DB',
            '分布式计算': 'cs.DC',
            '数字图书馆': 'cs.DL',
            '离散数学': 'cs.DM',
            '数据结构': 'cs.DS',
            '新兴技术': 'cs.ET',
            '形式语言': 'cs.FL',
            '综合通论': 'cs.GL',
            '计算机图形': 'cs.GR',
            '博弈论': 'cs.GT',
            '人机交互': 'cs.HC',
            '信息检索': 'cs.IR',
            '信息论': 'cs.IT',
            '机器学习': 'cs.LG',
            '程序逻辑': 'cs.LO',
            '多智能体': 'cs.MA',
            '多媒体': 'cs.MM',
            '数学软件': 'cs.MS',
            '数值分析': 'cs.NA',
            '神经计算': 'cs.NE',
            '网络架构': 'cs.NI',
            '其他CS': 'cs.OH',
            '操作系统': 'cs.OS',
            '性能分析': 'cs.PF',
            '编程语言': 'cs.PL',
            '机器人学': 'cs.RO',
            '符号计算': 'cs.SC',
            '音频计算': 'cs.SD',
            '软件工程': 'cs.SE',
            '社会网络': 'cs.SI',
            '系统控制': 'cs.SY'
        };
        
        document.querySelectorAll('.category-option.selected input[type="checkbox"]:checked').forEach(checkbox => {
            const label = checkbox.closest('.category-option');
            const categoryName = label.querySelector('span').textContent.trim();
            const categoryCode = categoryNames[categoryName];
            if (categoryCode) {
                selectedCategories.push(categoryCode);
            }
        });

        if (selectedCategories.length === 0) {
            utils.showNotification('请至少选择一个分类', 'warning');
            return;
        }

        try {
            utils.showLoading('保存中...');
            await api.updateCategories(selectedCategories);
            utils.hideLoading();
            utils.showNotification('分类配置已保存', 'success');
            this.loadConfigStatus();
        } catch (error) {
            utils.hideLoading();
            utils.showNotification('保存失败: ' + error.message, 'error');
        }
    }

    async updateFavoriteSummary() {
        try {
            utils.showLoading('更新总结中...');
            const response = await api.updateFavoriteSummaryAuto();
            utils.hideLoading();
            
            if (response.success) {
                document.getElementById('favorite-summary').value = response.data.summary;
                utils.showNotification('收藏总结已更新', 'success');
            }
        } catch (error) {
            utils.hideLoading();
            utils.showNotification('更新失败: ' + error.message, 'error');
        }
    }

    async saveFavoriteSummary() {
        const summary = document.getElementById('favorite-summary').value.trim();
        
        if (!summary) {
            utils.showNotification('请输入总结内容', 'warning');
            return;
        }

        try {
            utils.showLoading('保存中...');
            await api.updateFavoriteSummary(summary);
            utils.hideLoading();
            utils.showNotification('收藏总结已保存', 'success');
        } catch (error) {
            utils.hideLoading();
            utils.showNotification('保存失败: ' + error.message, 'error');
        }
    }

    // 系统维护功能
    async crawlNow() {
        const startInput = document.getElementById('crawl-start-date');
        const endInput = document.getElementById('crawl-end-date');
        const startDate = startInput && startInput.value ? startInput.value : null;
        const endDate = endInput && endInput.value ? endInput.value : null;

        // 本地校验：如果同时填写了起始和结束日期，确保起始日期不晚于结束日期
        if (startDate && endDate) {
            const s = new Date(startDate);
            const e = new Date(endDate);
            if (s > e) {
                utils.showNotification('起始日期不能晚于结束日期，请调整后重试。', 'error');
                return;
            }
        }

        if (!confirm('确定要立即爬取新论文吗？这可能需要一些时间。')) return;

        try {
            utils.showLoading('爬取中...');
            const body = {};
            if (startDate) body.start_date = startDate;
            if (endDate) body.end_date = endDate;

            const response = await api.request('/system/crawl-now', {
                method: 'POST',
                body: body
            });
            utils.hideLoading();

            if (response.success) {
                utils.showNotification(response.message, 'success');
                this.loadConfigStatus();
            }
        } catch (error) {
            utils.hideLoading();
            utils.showNotification('爬取失败: ' + error.message, 'error');
        }
    }

    async cleanCache() {
        const select = document.getElementById('clean-cache-range');
        const val = select ? select.value : '30';
        const label = val === 'all' ? '全部' : `${val} 天前`;
        if (!confirm(`确定要清理 ${label} 的缓存吗？仅删除被标记为不喜欢的论文。`)) return;

        try {
            utils.showLoading('清理中...');
            const response = await api.cleanCache(val);
            utils.hideLoading();

            if (response.success) {
                utils.showNotification(response.message, 'success');
            }
        } catch (error) {
            utils.hideLoading();
            utils.showNotification('清理失败: ' + error.message, 'error');
        }
    }

    // 管理界面：加载 admin 面板数据（上次抓取时间）
    async loadAdminPanel() {
        try {
            const resp = await api.getLastCrawlDate();
            if (resp.success) {
                const date = resp.data.last_crawl_date || '';
                const input = document.getElementById('admin-last-crawl-date');
                if (input) input.value = date;
            }
        } catch (e) {
            console.error('加载 admin 面板失败', e);
        }
    }

    // 管理界面：加载论文列表
    async loadAdminPapers(page = 1) {
        // 恢复分页：每页请求一定数量，默认 50
        const perPage = 50;
        this.adminPage = page || 1;
        try {
            const statusEl = document.getElementById('admin-filter-status');
            const status = statusEl ? statusEl.value : 'all';
            const resp = await api.getAdminPapers(status, this.adminPage, perPage);
            if (resp.success) {
                const papers = resp.data.papers || [];
                const rawPag = resp.data.pagination || {};
                const pageNum = rawPag.page || this.adminPage;
                const per = rawPag.per_page || perPage;
                const total = rawPag.total != null ? rawPag.total : (papers.length || 0);
                const pages = Math.max(1, Math.ceil(total / per));
                const pagination = { page: pageNum, per_page: per, total: total, pages: pages };
                this.renderAdminPapers(papers, pagination);
            }
        } catch (e) {
            utils.showNotification('加载论文列表失败: ' + e.message, 'error');
        }
    }

    renderAdminPapers(papers, pagination = { page: 1, pages: 1 }) {
        const container = document.getElementById('admin-papers-table');
        if (!container) return;

        let html = '<table class="admin-table">';
        // 列宽使用 colgroup：checkbox 固定、状态/发布日期固定，标题列自适应剩余空间
        html += '<colgroup><col style="width:40px"><col><col style="width:130px"><col style="width:130px"></colgroup>';
        html += '<thead><tr><th></th><th>标题</th><th>状态</th><th>发布日期</th></tr></thead><tbody>';
        for (const p of papers) {
            const status = this._paperStatus(p);
            const title = p.title || '';
            const date = p.published_date || '';
            const escTitle = this._escapeHtml(title);
            html += `<tr data-id="${p.paper_id}"><td><input type="checkbox" class="admin-select" data-id="${p.paper_id}"></td><td><div class="admin-title" title="${escTitle}">${escTitle}</div></td><td class="col-status">${status}</td><td class="col-date">${date}</td></tr>`;
        }
        html += '</tbody></table>';

        // 分页控件
        html += `<div class="admin-pagination" id="admin-pagination">`;
        html += `<button class="pagination-btn" id="admin-prev" ${pagination.page <= 1 ? 'disabled' : ''}>上一页</button>`;
        html += `<span class="page-info">第 ${pagination.page} 页，共 ${pagination.pages} 页</span>`;
        html += `<button class="pagination-btn" id="admin-next" ${pagination.page >= pagination.pages ? 'disabled' : ''}>下一页</button>`;
        html += `</div>`;

        container.innerHTML = html;

        const selectAll = document.getElementById('admin-select-all');
        if (selectAll) {
            selectAll.checked = false;
            // 只选择当前页面上的复选框（覆盖旧的处理器以避免重复绑定）
            selectAll.onchange = (e) => {
                container.querySelectorAll('.admin-select').forEach(cb => cb.checked = e.target.checked);
            };
        }

        // 绑定分页事件
        const prev = document.getElementById('admin-prev');
        const next = document.getElementById('admin-next');
        if (prev) prev.addEventListener('click', () => { if (pagination.page > 1) this.loadAdminPapers(pagination.page - 1); });
        if (next) next.addEventListener('click', () => { if (pagination.page < pagination.pages) this.loadAdminPapers(pagination.page + 1); });
    }

    _paperStatus(p) {
        if (p.favorite == 1) return '喜欢';
        if (p.maybe_later == 1) return '稍后再说';
        if (p.disliked == 1) return '不喜欢';
        if (p.llm_evaluated == 1) return '已评估';
        return '未评估';
    }

    _escapeHtml(text) {
        if (text === null || text === undefined) return '';
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    _getSelectedAdminPaperIds() {
        const ids = [];
        document.querySelectorAll('.admin-select:checked').forEach(cb => ids.push(parseInt(cb.dataset.id)));
        return ids;
    }

    // 绑定管理面板事件（在 init 之后调用）
    _bindAdminEvents() {
        const refreshBtn = document.getElementById('admin-refresh-list');
        if (refreshBtn) refreshBtn.addEventListener('click', () => this.loadAdminPapers(this.adminPage));

        const filterSelect = document.getElementById('admin-filter-status');
        if (filterSelect) filterSelect.addEventListener('change', () => { this.adminPage = 1; this.loadAdminPapers(1); });

        const crawlBtn = document.getElementById('admin-crawl-now');
        if (crawlBtn) crawlBtn.addEventListener('click', () => this.adminCrawlNow());


        const delUnassessed = document.getElementById('admin-delete-unassessed');
        if (delUnassessed) delUnassessed.addEventListener('click', async () => {
            if (!confirm('确定删除所有未评估且未被收藏/未被标记为稍后再说的论文吗？')) return;
            try {
                const resp = await api.deleteUnassessed();
                if (resp.success) utils.showNotification('已删除', 'success');
                this.loadAdminPapers(this.adminPage);
            } catch (e) { utils.showNotification('操作失败: ' + e.message, 'error'); }
        });

        const markDisliked = document.getElementById('admin-mark-assessed-unseen-disliked');
        if (markDisliked) markDisliked.addEventListener('click', async () => {
            if (!confirm('将所有已评估但未被标记的论文标记为不喜欢？')) return;
            try {
                const resp = await api.markAssessedUnseenDisliked();
                if (resp.success) utils.showNotification('已标记', 'success');
                this.loadAdminPapers(this.adminPage);
            } catch (e) { utils.showNotification('操作失败: ' + e.message, 'error'); }
        });

        const delDislikedAll = document.getElementById('admin-delete-disliked');
        if (delDislikedAll) delDislikedAll.addEventListener('click', async () => {
            if (!confirm('确定删除所有已标记为不喜欢的论文吗？该操作不可恢复。')) return;
            try {
                const resp = await api.deleteDisliked();
                if (resp.success) utils.showNotification('已删除所有不喜欢的论文', 'success');
                this.loadAdminPapers(this.adminPage);
            } catch (e) { utils.showNotification('操作失败: ' + e.message, 'error'); }
        });

        const bulkFavorite = document.getElementById('admin-bulk-favorite');
        if (bulkFavorite) bulkFavorite.addEventListener('click', async () => {
            const ids = this._getSelectedAdminPaperIds(); if (!ids.length) return utils.showNotification('未选择任何论文', 'warning');
            try { await api.bulkUpdate(ids, 'favorite'); utils.showNotification('已标记为喜欢', 'success'); this.loadAdminPapers(this.adminPage); } catch (e) { utils.showNotification('失败: ' + e.message, 'error'); }
        });

        const bulkMaybe = document.getElementById('admin-bulk-maybe');
        if (bulkMaybe) bulkMaybe.addEventListener('click', async () => {
            const ids = this._getSelectedAdminPaperIds(); if (!ids.length) return utils.showNotification('未选择任何论文', 'warning');
            try { await api.bulkUpdate(ids, 'maybe_later'); utils.showNotification('已标记为稍后再说', 'success'); this.loadAdminPapers(this.adminPage); } catch (e) { utils.showNotification('失败: ' + e.message, 'error'); }
        });

        const bulkDislike = document.getElementById('admin-bulk-dislike');
        if (bulkDislike) bulkDislike.addEventListener('click', async () => {
            const ids = this._getSelectedAdminPaperIds(); if (!ids.length) return utils.showNotification('未选择任何论文', 'warning');
            try { await api.bulkUpdate(ids, 'dislike'); utils.showNotification('已标记为不喜欢', 'success'); this.loadAdminPapers(this.adminPage); } catch (e) { utils.showNotification('失败: ' + e.message, 'error'); }
        });

        const bulkDelete = document.getElementById('admin-bulk-delete');
        if (bulkDelete) bulkDelete.addEventListener('click', async () => {
            const ids = this._getSelectedAdminPaperIds(); if (!ids.length) return utils.showNotification('未选择任何论文', 'warning');
            if (!confirm('确定批量删除所选论文吗？')) return;
            try { await api.bulkDelete(ids); utils.showNotification('已删除', 'success'); this.loadAdminPapers(this.adminPage); } catch (e) { utils.showNotification('失败: ' + e.message, 'error'); }
        });
    }

    // 管理页面调用爬取（使用 admin API）
    async adminCrawlNow() {
        if (!confirm('确定要立即爬取新论文吗？这可能需要一些时间。')) return;

        try {
            utils.showLoading('爬取中...');
            const resp = await api.adminCrawlNow();
            utils.hideLoading();
            if (resp.success) {
                utils.showNotification(resp.message || '已开始爬取', 'success');
                this.loadAdminPanel();
            }
        } catch (e) {
            utils.hideLoading();
            utils.showNotification('爬取失败: ' + e.message, 'error');
        }
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ArxivAgentApp();
});