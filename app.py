from flask import Flask, render_template, jsonify, request
from services.arxiv_service import ArxivService
from services.llm_service import LLMService
from services.recommendation_service import RecommendationService
from utils.database import DatabaseManager
import json
import threading
from datetime import datetime

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


# === 管理接口：论文管理（在列表页） ===
@app.route('/api/admin/last-crawl')
def admin_last_crawl():
    try:
        last = db.get_config('LAST_CRAWL_DATE', '')
        return jsonify({'success': True, 'data': {'last_crawl_date': last}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500




@app.route('/api/admin/crawl-now', methods=['POST'])
def admin_crawl_now():
    try:
        data = request.get_json() or {}
        categories = data.get('categories')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        count = arxiv_service.crawl_recent_papers(force_categories=categories, start_date=start_date, end_date=end_date)
        return jsonify({'success': True, 'message': f'成功爬取 {count} 篇论文', 'data': {'count': count}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/papers')
def admin_get_papers():
    try:
        status = request.args.get('status', 'all')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        offset = (page - 1) * per_page

        base_query = 'SELECT *, id as paper_id FROM papers'
        where_clauses = []
        params = []

        if status == 'unassessed':
            where_clauses.append('llm_evaluated = 0')
        elif status == 'assessed':
            where_clauses.append('llm_evaluated = 1')
        elif status == 'unread':
            # 已被LLM评估且被LLM推荐，但用户尚未对其进行任何标记（未收藏/未稍后/未标记为不喜欢）
            where_clauses.append('(llm_evaluated = 1 AND is_recommended = 1 AND (favorite IS NULL OR favorite = 0) AND (maybe_later IS NULL OR maybe_later = 0) AND (disliked IS NULL OR disliked = 0))')
        elif status == 'favorite':
            where_clauses.append('favorite = 1')
        elif status == 'disliked':
            where_clauses.append('disliked = 1')
        elif status == 'maybe_later':
            where_clauses.append('maybe_later = 1')

        where_sql = (' WHERE ' + ' AND '.join(where_clauses)) if where_clauses else ''

        query = f"{base_query} {where_sql} ORDER BY published_date DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])
        rows = db.execute_query(query, params)

        # total
        count_query = f"SELECT COUNT(*) as total FROM papers {where_sql}"
        total_res = db.execute_query(count_query)
        total = total_res[0]['total'] if total_res else 0

        return jsonify({'success': True, 'data': {'papers': [dict(r) for r in rows], 'pagination': {'page': page, 'per_page': per_page, 'total': total}}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/delete-unprocessed', methods=['POST'])
def admin_delete_unprocessed():
    try:
        # 删除未处理的论文（未被评估且未被用户标记）
        query = "DELETE FROM papers WHERE llm_evaluated = 0 AND (favorite IS NULL OR favorite = 0) AND (maybe_later IS NULL OR maybe_later = 0) AND (disliked IS NULL OR disliked = 0)"
        res = db.execute_query(query)
        return jsonify({'success': True, 'data': {'deleted': res}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/delete-others', methods=['POST'])
def admin_delete_others():
    try:
        # 删除除了收藏和稍后再说之外的所有论文
        query = "DELETE FROM papers WHERE (favorite IS NULL OR favorite = 0) AND (maybe_later IS NULL OR maybe_later = 0)"
        res = db.execute_query(query)
        return jsonify({'success': True, 'data': {'deleted': res}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/mark-unread-read', methods=['POST'])
def admin_mark_unread_read():
    try:
        # 将所有未读论文标记为已读（用户没有做任何标记的论文）
        # 已读的意思是：做了喜欢、不喜欢或稍后再说的任意一个标记
        # 所以，将未读论文标记为已读，就是将它们标记为不喜欢
        # 只处理处理过的论文（llm_evaluated = 1），未处理的论文不用管
        query = "UPDATE papers SET disliked = 1 WHERE llm_evaluated = 1 AND (favorite IS NULL OR favorite = 0) AND (maybe_later IS NULL OR maybe_later = 0) AND (disliked IS NULL OR disliked = 0)"
        res = db.execute_query(query)
        return jsonify({'success': True, 'data': {'updated': res}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/bulk-update', methods=['POST'])
def admin_bulk_update():
    try:
        data = request.get_json() or {}
        ids = data.get('paper_ids', [])
        action = data.get('action')
        if not ids or not action:
            return jsonify({'success': False, 'error': '缺少参数'}), 400

        for pid in ids:
            if action == 'favorite':
                db.mark_favorite(pid)
            elif action == 'unfavorite':
                db.unmark_favorite(pid)
            elif action == 'maybe_later':
                db.mark_maybe_later(pid)
            elif action == 'unmaybe':
                db.unmark_maybe_later(pid)
            elif action == 'dislike':
                db.mark_disliked(pid)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/bulk-delete', methods=['POST'])
def admin_bulk_delete():
    try:
        data = request.get_json() or {}
        ids = data.get('paper_ids', [])
        if not ids:
            return jsonify({'success': False, 'error': '缺少参数'}), 400
        placeholders = ','.join(['?'] * len(ids))
        query = f'DELETE FROM papers WHERE id IN ({placeholders})'
        res = db.execute_query(query, ids)
        return jsonify({'success': True, 'data': {'deleted': res}})
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
        data = request.get_json() or {}
        categories = data.get('categories')
        start_date = data.get('start_date')  # expected YYYY-MM-DD or None
        end_date = data.get('end_date')

        # 后端校验：确保传入日期格式正确且 start_date <= end_date
        if start_date and end_date:
            try:
                sd = datetime.strptime(start_date, '%Y-%m-%d')
                ed = datetime.strptime(end_date, '%Y-%m-%d')
            except Exception:
                return jsonify({'success': False, 'error': '日期格式错误，期望 YYYY-MM-DD'}), 400

            if sd > ed:
                return jsonify({'success': False, 'error': '起始日期不能晚于结束日期'}), 400

        count = arxiv_service.crawl_recent_papers(force_categories=categories, start_date=start_date, end_date=end_date)
        
        return jsonify({
            'success': True,
            'message': f'成功爬取 {count} 篇论文',
            'data': {'count': count}
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)