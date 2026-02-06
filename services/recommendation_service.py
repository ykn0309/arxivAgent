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
            # 标记为收藏
            self.db.set_user_status(paper_id, 'favorite')
            # 记录用户笔记（历史上使用独立的 `favorites` 表；当前实现将用户标记合并到
            # `papers.user_status`，用户笔记可扩展存放在 `papers` 表的相应字段）
        elif action == 'maybe_later':
            # 标记为稍后再说
            self.db.set_user_status(paper_id, 'maybe_later')
        elif action == 'dislike':
            # 标记为不喜欢
            self.db.set_user_status(paper_id, 'dislike')
        # 其它情况（例如 'none'）可不做处理
    
    def _trigger_incremental_summary(self):
        """触发增量总结"""
        # 获取未总结的收藏论文（基于 `papers.user_status = 'favorite'`）
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
        rows = self.db.get_papers_by_user_status('favorite', limit=per_page, offset=offset)
        # count total
        count_query = "SELECT COUNT(*) as total FROM papers WHERE user_status = 'favorite'"
        total_result = self.db.execute_query(count_query)
        total = total_result[0]['total'] if total_result else 0

        return {
            'papers': [dict(row) for row in rows],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }

    def get_pending_count(self) -> int:
        """返回待评估（未由LLM评估且未标记为推荐）的论文数量"""
        # 统计尚未由 LLM 评估的论文数量
        query = "SELECT COUNT(*) as total FROM papers WHERE llm_evaluated = FALSE"
        result = self.db.execute_query(query)
        return result[0]['total'] if result else 0
    
    def get_maybe_later_list(self, page: int = 1, per_page: int = 10) -> Dict:
        """获取稍后再说列表（分页）"""
        offset = (page - 1) * per_page
        rows = self.db.get_papers_by_user_status('maybe_later', limit=per_page, offset=offset)
        count_query = "SELECT COUNT(*) as total FROM papers WHERE user_status = 'maybe_later'"
        total_result = self.db.execute_query(count_query)
        total = total_result[0]['total'] if total_result else 0

        return {
            'papers': [dict(row) for row in rows],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }
    
    def move_from_maybe_to_favorite(self, paper_id: int, user_note: str = None):
        """将论文从稍后再说移动到收藏"""
        # 直接将用户状态改为 favorite
        self.db.set_user_status(paper_id, 'favorite')
        
        # 触发增量总结
        self._trigger_incremental_summary()
    
    def delete_favorite(self, favorite_id: int):
        """删除收藏（兼容旧接口）"""
        # 旧模型的 `favorite_id` 指向 `favorites.id`；新接口以 `paper_id` 表示论文。
        # 这里假设传入的是 `paper_id` 并将其状态重置为 'none'。
        query = "UPDATE papers SET user_status = 'none' WHERE id = ?"
        return self.db.execute_query(query, (favorite_id,))
    
    def delete_maybe_later(self, maybe_later_id: int):
        """删除稍后再说"""
        # assume maybe_later_id is paper_id
        query = "UPDATE papers SET user_status = 'none' WHERE id = ?"
        return self.db.execute_query(query, (maybe_later_id,))
    
    def clean_old_papers(self, days_old: int = 30):
        """清理旧论文（保留收藏和稍后再说）"""
        from datetime import datetime, timedelta
        
        cutoff_date = (datetime.now() - timedelta(days=days_old)).strftime('%Y-%m-%d')
        
        # 获取要保留的论文ID：user_status in ('favorite','maybe_later')
        protected_query = "SELECT id FROM papers WHERE user_status IN ('favorite','maybe_later')"
        protected_result = self.db.execute_query(protected_query)
        protected_ids = [str(row['id']) for row in protected_result]
        
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