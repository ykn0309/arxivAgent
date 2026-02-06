import json
from typing import List, Dict, Optional
from services.arxiv_service import ArxivService
from services.llm_service import LLMService
from utils.database import DatabaseManager

class RecommendationService:
    """推荐引擎服务"""
    
    def __init__(self):
        self.arxiv_service = ArxivService()
        self.llm_service = LLMService()
        self.db = DatabaseManager()
    
    def get_next_recommendation(self) -> Optional[Dict]:
        """获取下一条推荐论文"""
        # 获取待评估的论文
        papers = self.db.get_papers_for_recommendation(limit=1)
        
        if not papers:
            # 如果没有待评估论文，触发爬取
            self.arxiv_service.crawl_recent_papers()
            papers = self.db.get_papers_for_recommendation(limit=1)
            if not papers:
                return None
        
        paper = papers[0]
        
        # 获取用户配置
        user_interests = self.db.get_config('USER_INTERESTS', '')
        favorite_summary = self.db.get_config('FAVORITE_SUMMARY', '')
        
        if not user_interests:
            raise ValueError("用户兴趣点未配置")
        
        # 使用LLM评估论文
        paper_dict = dict(paper)
        eval_result = self.llm_service.evaluate_paper(
            paper_dict, user_interests, favorite_summary
        )
        is_recommended = eval_result.get('is_recommended', False)
        reason = eval_result.get('reason', '')
        
        # 更新论文状态和推荐理由
        self.db.update_paper_evaluation(paper['id'], is_recommended, recommendation_reason=reason)
        
        if is_recommended:
            # 为推荐论文添加翻译
            try:
                translation = self.llm_service.translate_paper_info(
                    paper_dict['title'], 
                    paper_dict['abstract']
                )
                chinese_title = translation['chinese_title']
                chinese_abstract = translation['chinese_abstract']
                paper_dict['chinese_title'] = chinese_title
                paper_dict['chinese_abstract'] = chinese_abstract
                # 保存翻译到数据库
                self.db.update_paper_translation(paper['id'], chinese_title, chinese_abstract)
            except Exception as e:
                print(f"翻译论文时出错: {e}")
                paper_dict['chinese_title'] = ''
                paper_dict['chinese_abstract'] = ''
            
            # 添加推荐理由到返回数据
            paper_dict['recommendation_reason'] = reason
            
            # 返回推荐论文的完整信息
            return paper_dict
        else:
            # 如果不推荐，递归获取下一个
            return self.get_next_recommendation()
    
    def process_user_feedback(self, paper_id: int, action: str, user_note: str = None):
        """处理用户反馈"""
        if action == 'favorite':
            # 添加到收藏
            self.db.add_favorite(paper_id, user_note)
        elif action == 'maybe_later':
            # 添加到稍后再说
            self.db.add_maybe_later(paper_id)
        # 如果是不喜欢，则不做额外处理，论文已被标记为已评估
    
    def _trigger_incremental_summary(self):
        """触发增量总结"""
        # 获取未总结的收藏论文
        unsummarized = self.db.get_unsummarized_favorites()
        
        if not unsummarized:
            return
        
        # 准备论文数据
        papers_data = []
        favorite_ids = []
        
        for row in unsummarized:
            paper_data = {
                'title': row['title'],
                'abstract': row['abstract']
            }
            papers_data.append(paper_data)
            favorite_ids.append(row['id'])
        
        # 获取当前总结
        current_summary = self.db.get_config('FAVORITE_SUMMARY', '')
        
        # 调用LLM进行增量总结
        new_summary = self.llm_service.summarize_favorites(papers_data, current_summary)
        
        # 更新配置
        self.db.set_config('FAVORITE_SUMMARY', new_summary)
        
        # 标记这些收藏已总结
        for favorite_id in favorite_ids:
            self.db.mark_favorite_summarized(favorite_id)
    
    def get_favorites_list(self, page: int = 1, per_page: int = 10) -> Dict:
        """获取收藏列表（分页）"""
        offset = (page - 1) * per_page
        
        query = '''
            SELECT 
                f.id as favorite_id,
                f.paper_id,
                f.user_note,
                f.is_summarized,
                f.created_at as favorite_created_at,
                p.id,
                p.arxiv_id,
                p.title,
                p.abstract,
                p.authors,
                p.categories,
                p.published_date,
                p.updated_date,
                p.pdf_url,
                p.arxiv_url,
                p.is_recommended,
                p.llm_evaluated,
                p.recommendation_reason,
                p.chinese_title,
                p.chinese_abstract,
                p.created_at
            FROM favorites f
            JOIN papers p ON f.paper_id = p.id
            ORDER BY f.created_at DESC
            LIMIT ? OFFSET ?
        '''
        
        papers = self.db.execute_query(query, (per_page, offset))
        
        # 获取总数
        count_query = '''
            SELECT COUNT(*) as total 
            FROM favorites f
            JOIN papers p ON f.paper_id = p.id
        '''
        total_result = self.db.execute_query(count_query)
        total = total_result[0]['total'] if total_result else 0
        
        return {
            'papers': [dict(row) for row in papers],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }

    def get_pending_count(self) -> int:
        """返回待评估（未由LLM评估且未标记为推荐）的论文数量"""
        query = """
            SELECT COUNT(*) as total
            FROM papers
            WHERE llm_evaluated = FALSE AND is_recommended = FALSE
        """
        result = self.db.execute_query(query)
        return result[0]['total'] if result else 0
    
    def get_maybe_later_list(self, page: int = 1, per_page: int = 10) -> Dict:
        """获取稍后再说列表（分页）"""
        offset = (page - 1) * per_page
        
        query = '''
            SELECT 
                ml.id as maybe_later_id,
                ml.paper_id,
                ml.created_at as maybe_later_created_at,
                p.id,
                p.arxiv_id,
                p.title,
                p.abstract,
                p.authors,
                p.categories,
                p.published_date,
                p.updated_date,
                p.pdf_url,
                p.arxiv_url,
                p.is_recommended,
                p.llm_evaluated,
                p.recommendation_reason,
                p.chinese_title,
                p.chinese_abstract,
                p.created_at
            FROM maybe_later ml
            JOIN papers p ON ml.paper_id = p.id
            ORDER BY ml.created_at DESC
            LIMIT ? OFFSET ?
        '''
        
        papers = self.db.execute_query(query, (per_page, offset))
        
        # 获取总数
        count_query = '''
            SELECT COUNT(*) as total 
            FROM maybe_later ml
            JOIN papers p ON ml.paper_id = p.id
        '''
        total_result = self.db.execute_query(count_query)
        total = total_result[0]['total'] if total_result else 0
        
        return {
            'papers': [dict(row) for row in papers],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }
    
    def move_from_maybe_to_favorite(self, paper_id: int, user_note: str = None):
        """将论文从稍后再说移动到收藏"""
        # 删除稍后再说记录
        delete_query = 'DELETE FROM maybe_later WHERE paper_id = ?'
        self.db.execute_query(delete_query, (paper_id,))
        
        # 添加到收藏
        self.db.add_favorite(paper_id, user_note)
        
        # 触发增量总结
        self._trigger_incremental_summary()
    
    def delete_favorite(self, favorite_id: int):
        """删除收藏"""
        query = 'DELETE FROM favorites WHERE id = ?'
        return self.db.execute_query(query, (favorite_id,))
    
    def delete_maybe_later(self, maybe_later_id: int):
        """删除稍后再说"""
        query = 'DELETE FROM maybe_later WHERE id = ?'
        return self.db.execute_query(query, (maybe_later_id,))
    
    def clean_old_papers(self, days_old: int = 30):
        """清理旧论文（保留收藏和稍后再说）"""
        from datetime import datetime, timedelta
        
        cutoff_date = (datetime.now() - timedelta(days=days_old)).strftime('%Y-%m-%d')
        
        # 获取要保留的论文ID
        protected_papers_query = '''
            SELECT DISTINCT paper_id FROM favorites
            UNION
            SELECT DISTINCT paper_id FROM maybe_later
        '''
        protected_result = self.db.execute_query(protected_papers_query)
        protected_ids = [str(row['paper_id']) for row in protected_result]
        
        if protected_ids:
            # 删除不在保护列表中的旧论文
            delete_query = f'''
                DELETE FROM papers 
                WHERE published_date < ? 
                AND id NOT IN ({','.join(['?'] * len(protected_ids))})
            '''
            params = [cutoff_date] + protected_ids
        else:
            # 没有保护的论文，直接删除旧论文
            delete_query = 'DELETE FROM papers WHERE published_date < ?'
            params = [cutoff_date]
        
        return self.db.execute_query(delete_query, params)