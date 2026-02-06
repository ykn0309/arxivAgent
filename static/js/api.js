// API调用封装
class APIClient {
    constructor() {
        this.baseUrl = '/api';
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        if (config.body && typeof config.body === 'object') {
            config.body = JSON.stringify(config.body);
        }

        try {
            const response = await fetch(url, config);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}`);
            }
            
            return data;
        } catch (error) {
            console.error('API请求失败:', error);
            throw error;
        }
    }

    // 配置状态
    async getConfigStatus() {
        return this.request('/config/status');
    }

    // LLM配置
    async getLLMConfig() {
        return this.request('/config/llm');
    }

    async updateLLMConfig(config) {
        return this.request('/config/llm', {
            method: 'POST',
            body: config
        });
    }

    async testLLMConnection() {
        return this.request('/config/llm/test', {
            method: 'POST'
        });
    }

    // 用户兴趣
    async getUserInterests() {
        return this.request('/config/interests');
    }

    async updateUserInterests(interests) {
        return this.request('/config/interests', {
            method: 'POST',
            body: { interests }
        });
    }

    // 分类配置
    async getCategories() {
        return this.request('/config/categories');
    }

    async updateCategories(categories) {
        return this.request('/config/categories', {
            method: 'POST',
            body: { categories }
        });
    }

    // 收藏总结
    async getFavoriteSummary() {
        return this.request('/config/favorite-summary');
    }

    async updateFavoriteSummary(summary) {
        return this.request('/config/favorite-summary', {
            method: 'POST',
            body: { summary }
        });
    }

    async updateFavoriteSummaryAuto() {
        return this.request('/config/update-favorite-summary', {
            method: 'POST'
        });
    }

    // 推荐
    async getNextRecommendation() {
        return this.request('/recommendation/next');
    }

    async getRecommendationStatus() {
        return this.request('/recommendation/status');
    }

    async sendFeedback(feedback) {
        return this.request('/recommendation/feedback', {
            method: 'POST',
            body: feedback
        });
    }

    // 列表管理
    async getFavorites(page = 1, perPage = 10) {
        return this.request(`/list/favorites?page=${page}&per_page=${perPage}`);
    }

    async getMaybeLater(page = 1, perPage = 10) {
        return this.request(`/list/maybe-later?page=${page}&per_page=${perPage}`);
    }

    async moveToFavorite(paperId, note = '') {
        return this.request('/list/move-to-favorite', {
            method: 'POST',
            body: { paper_id: paperId, user_note: note }
        });
    }

    async deleteFavorite(favoriteId) {
        return this.request('/list/delete-favorite', {
            method: 'POST',
            body: { favorite_id: favoriteId }
        });
    }

    async deleteMaybeLater(maybeLaterId) {
        return this.request('/list/delete-maybe-later', {
            method: 'POST',
            body: { maybe_later_id: maybeLaterId }
        });
    }

    // 系统维护
    async cleanCache(days = 30) {
        return this.request(`/system/clean-cache?days=${days}`, {
            method: 'POST'
        });
    }

    async crawlNow(categories = null) {
        return this.request('/system/crawl-now', {
            method: 'POST',
            body: categories ? { categories } : {}
        });
    }
}

// 全局API客户端实例
const api = new APIClient();

// 工具函数
const utils = {
    formatDate(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    },

    truncateText(text, maxLength = 200) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    },

    showNotification(message, type = 'info') {
        // 简单的通知实现
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 5px;
            color: white;
            font-weight: 500;
            z-index: 3000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            ${type === 'success' ? 'background: #27ae60;' :
              type === 'error' ? 'background: #e74c3c;' :
              type === 'warning' ? 'background: #f39c12;' :
              'background: #3498db;'}
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    },

    showLoading(message = '处理中...') {
        const overlay = document.getElementById('loading-overlay');
        const messageEl = document.getElementById('loading-message');
        messageEl.textContent = message;
        overlay.style.display = 'flex';
    },

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        overlay.style.display = 'none';
    },
    
    // modal functions removed — modals are deprecated in the UI
    
};