from flask import Flask, render_template, jsonify, request
from services.arxiv_service import ArxivService
from services.llm_service import LLMService
from services.recommendation_service import RecommendationService
from utils.database import DatabaseManager
import json
import threading

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config.from_object('config.Config')

# 初始化服务
arxiv_service = ArxivService()
llm_service = LLMService()
recommendation_service = RecommendationService()
db = DatabaseManager()

# 启动时在后台评估未评估的论文，减少用户请求等待时间
try:
    recommendation_service.start_background_evaluation(batch_size=10, delay=0.5)
except Exception:
    # 忽略启动时的任何错误（例如 LLM 未配置）
    pass

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

# === 配置管理API ===

@app.route('/api/config/status')
def get_config_status():
    """获取配置状态"""
    try:
        llm_configured = bool(db.get_config('LLM_API_KEY'))
        interests_configured = bool(db.get_config('USER_INTERESTS'))
        categories_configured = bool(db.get_config('CATEGORIES'))
        
        return jsonify({
            'success': True,
            'data': {
                'llm_configured': llm_configured,
                'interests_configured': interests_configured,
                'categories_configured': categories_configured,
                'fully_configured': llm_configured and interests_configured and categories_configured
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config/llm', methods=['GET', 'POST'])
def llm_config():
    """LLM配置API"""
    if request.method == 'GET':
        # 获取当前配置
        try:
            return jsonify({
                'success': True,
                'data': {
                    'base_url': db.get_config('LLM_BASE_URL', ''),
                    'model': db.get_config('LLM_MODEL', '')
                }
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'POST':
        # 更新配置
        try:
            data = request.get_json()
            base_url = data.get('base_url', '').strip()
            api_key = data.get('api_key', '').strip()
            model = data.get('model', '').strip()
            
            if not all([base_url, api_key, model]):
                return jsonify({'success': False, 'error': '所有字段都是必填的'}), 400
            
            llm_service.update_config(base_url, api_key, model)
            return jsonify({'success': True, 'message': 'LLM配置已更新'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config/llm/test', methods=['POST'])
def test_llm():
    """测试LLM连接"""
    try:
        success = llm_service.test_connection()
        return jsonify({
            'success': success,
            'message': '连接成功' if success else '连接失败'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config/interests', methods=['GET', 'POST'])
def user_interests():
    """用户兴趣配置API"""
    if request.method == 'GET':
        try:
            interests = db.get_config('USER_INTERESTS', '')
            return jsonify({
                'success': True,
                'data': {'interests': interests}
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            interests_raw = data.get('interests', '').strip()
            
            if not interests_raw:
                return jsonify({'success': False, 'error': '请输入研究兴趣'}), 400
            
            # 使用LLM精炼兴趣点
            refined_interests = llm_service.refine_user_interests(interests_raw)
            db.set_config('USER_INTERESTS', refined_interests)
            
            return jsonify({
                'success': True,
                'message': '兴趣点已配置并精炼',
                'data': {'refined_interests': refined_interests}
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config/categories', methods=['GET', 'POST'])
def categories_config():
    """分类配置API"""
    if request.method == 'GET':
        try:
            # 获取所有CS分类
            all_categories = arxiv_service.get_cs_categories()
            # 获取当前配置的分类
            current_categories = db.get_config('CATEGORIES', '')
            current_list = current_categories.split(',') if current_categories else []
            
            return jsonify({
                'success': True,
                'data': {
                    'all_categories': all_categories,
                    'current_categories': current_list
                }
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            categories = data.get('categories', [])
            
            # 过滤掉空值和None
            categories = [cat for cat in categories if cat and isinstance(cat, str)]
            
            if not categories:
                return jsonify({'success': False, 'error': '请至少选择一个分类'}), 400
            
            categories_str = ','.join(categories)
            db.set_config('CATEGORIES', categories_str)
            
            return jsonify({
                'success': True,
                'message': '分类配置已更新',
                'data': {'categories': categories}
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config/favorite-summary', methods=['GET', 'POST'])
def favorite_summary():
    """收藏总结配置API"""
    if request.method == 'GET':
        try:
            summary = db.get_config('FAVORITE_SUMMARY', '')
            return jsonify({
                'success': True,
                'data': {'summary': summary}
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            summary = data.get('summary', '').strip()
            
            if not summary:
                return jsonify({'success': False, 'error': '总结不能为空'}), 400
            
            db.set_config('FAVORITE_SUMMARY', summary)
            return jsonify({
                'success': True,
                'message': '收藏总结已更新'
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config/update-favorite-summary', methods=['POST'])
def update_favorite_summary():
    """更新收藏总结"""
    try:
        # 触发增量总结
        recommendation_service._trigger_incremental_summary()
        
        # 获取新的总结
        new_summary = db.get_config('FAVORITE_SUMMARY', '')
        
        return jsonify({
            'success': True,
            'message': '收藏总结已更新',
            'data': {'summary': new_summary}
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# === 推荐API ===

@app.route('/api/recommendation/next')
def get_next_recommendation():
    """获取下一条推荐"""
    try:
        paper = recommendation_service.get_next_recommendation()
        if paper:
            # 保持JSON字段为字符串，由前端解析
            return jsonify({
                'success': True,
                'data': paper
            })
        else:
            return jsonify({
                'success': True,
                'data': None,
                'message': '暂无更多推荐论文'
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/recommendation/feedback', methods=['POST'])
def process_feedback():
    """处理用户反馈"""
    try:
        data = request.get_json()
        paper_id = data.get('paper_id')
        action = data.get('action')  # 'favorite', 'maybe_later', 'dislike'
        user_note = data.get('user_note', '')
        
        if not all([paper_id, action]):
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400
        
        recommendation_service.process_user_feedback(paper_id, action, user_note)
        
        return jsonify({
            'success': True,
            'message': '反馈已处理'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# === 列表管理API ===

@app.route('/api/list/favorites')
def get_favorites():
    """获取收藏列表"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        result = recommendation_service.get_favorites_list(page, per_page)
        # 保持JSON字段为字符串，由前端解析
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/recommendation/status')
def recommendation_status():
    """获取推荐进度状态：待评估论文数量"""
    try:
        status = recommendation_service.get_evaluation_status()
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/list/maybe-later')
def get_maybe_later():
    """获取稍后再说列表"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        result = recommendation_service.get_maybe_later_list(page, per_page)
        # 保持JSON字段为字符串，由前端解析
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/list/move-to-favorite', methods=['POST'])
def move_to_favorite():
    """将稍后再说移动到收藏"""
    try:
        data = request.get_json()
        paper_id = data.get('paper_id')
        user_note = data.get('user_note', '')
        
        if not paper_id:
            return jsonify({'success': False, 'error': '缺少论文ID'}), 400
        
        recommendation_service.move_from_maybe_to_favorite(paper_id, user_note)
        
        return jsonify({
            'success': True,
            'message': '已移动到收藏'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/list/delete-favorite', methods=['POST'])
def delete_favorite():
    """删除收藏"""
    try:
        data = request.get_json()
        paper_id = data.get('paper_id')
        
        if not paper_id:
            return jsonify({'success': False, 'error': '缺少论文ID'}), 400
        
        recommendation_service.delete_favorite(paper_id)
        
        return jsonify({
            'success': True,
            'message': '收藏已删除'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/list/delete-maybe-later', methods=['POST'])
def delete_maybe_later():
    """删除稍后再说"""
    try:
        data = request.get_json()
        paper_id = data.get('paper_id')
        
        if not paper_id:
            return jsonify({'success': False, 'error': '缺少论文ID'}), 400
        
        recommendation_service.delete_maybe_later(paper_id)
        
        return jsonify({
            'success': True,
            'message': '记录已删除'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# === 系统维护API ===

@app.route('/api/system/clean-cache', methods=['POST'])
def clean_cache():
    """清理缓存"""
    try:
        days_param = request.args.get('days', '30')
        only_disliked = request.args.get('only_disliked', 'true').lower() in ('1', 'true', 'yes')

        if days_param == 'all':
            # 删除所有被标记为不喜欢的论文（保护收藏/稍后）
            deleted_count = recommendation_service.clean_old_papers(days_old=None, delete_all=True)
        else:
            days_old = int(days_param)
            deleted_count = recommendation_service.clean_old_papers(days_old=days_old, delete_all=False)
        return jsonify({
            'success': True,
            'message': f'已清理 {deleted_count} 篇旧论文',
            'data': {'deleted_count': deleted_count}
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/system/crawl-now', methods=['POST'])
def crawl_now():
    """立即爬取"""
    try:
        data = request.get_json()
        categories = data.get('categories')
        
        count = arxiv_service.crawl_recent_papers(categories)
        
        return jsonify({
            'success': True,
            'message': f'成功爬取 {count} 篇论文',
            'data': {'count': count}
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)