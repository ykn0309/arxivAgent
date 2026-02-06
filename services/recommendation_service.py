import json
from typing import List, Dict, Optional
from services.arxiv_service import ArxivService
from services.llm_service import LLMService
from utils.database import DatabaseManager
import threading
import time

class RecommendationService:
    """推荐引擎服务"""
    
    def __init__(self):
        self.arxiv_service = ArxivService()
        self.llm_service = LLMService()
        self.db = DatabaseManager()
    
    def get_next_recommendation(self) -> Optional[Dict]:
        """获取下一条推荐论文"""
        # 优先返回已经被LLM标记为推荐并且用户尚未处理的论文（快速响应）
        rows = self.db.get_recommended_unseen(limit=1)
        if rows:
            paper = dict(rows[0])
            return paper

        # 否则，按照旧逻辑评估下一篇未评估论文（同步行为，可能较慢）
        papers = self.db.get_papers_for_recommendation(limit=1)
        if not papers:
            # 如果没有待评估论文，触发爬取并重试
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

        # 使用LLM评估论文（同步）
        paper_dict = dict(paper)
        eval_result = self.llm_service.evaluate_paper(
            paper_dict, user_interests, favorite_summary
        )
        is_recommended = eval_result.get('is_recommended', False)
        reason = eval_result.get('reason', '')

        # 更新论文状态和推荐理由（把 llm_evaluated 也设置为 True）
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

    def evaluate_pending_papers(self, batch_size: int = 10, delay: float = 0.0):
        """在后台对未评估的论文运行 LLM 评估并保存结果到数据库。

        该方法会批量获取未评估论文并依次调用 LLM 来评估、翻译（若被推荐），并把
        `llm_evaluated` 标记为 True，`is_recommended` 根据评估结果设置为 True/False。
        """
        try:
            # 如果LLM未配置，跳过
            if not self.llm_service.api_key:
                print("LLM 未配置，跳过后台评估")
                return
        except Exception:
            # 如果获取 api_key 时出现问题，也跳过
            print("无法读取 LLM 配置，跳过后台评估")
            return

        while True:
            papers = self.db.get_papers_for_recommendation(limit=batch_size)
            if not papers:
                break

            for row in papers:
                pid = row['id']
                paper_dict = dict(row)

                try:
                    user_interests = self.db.get_config('USER_INTERESTS', '')
                    favorite_summary = self.db.get_config('FAVORITE_SUMMARY', '')
                    eval_result = self.llm_service.evaluate_paper(paper_dict, user_interests, favorite_summary)
                    is_recommended = eval_result.get('is_recommended', False)
                    reason = eval_result.get('reason', '')

                    # 更新评估结果并标记为已评估
                    self.db.update_paper_evaluation(pid, is_recommended, recommendation_reason=reason)

                    if is_recommended:
                        try:
                            translation = self.llm_service.translate_paper_info(paper_dict['title'], paper_dict['abstract'])
                            self.db.update_paper_translation(pid, translation.get('chinese_title', ''), translation.get('chinese_abstract', ''))
                        except Exception as e:
                            print(f"翻译失败（ID={pid}）: {e}")

                except Exception as e:
                    print(f"评估论文 ID={pid} 时出错: {e}")

                if delay and delay > 0:
                    time.sleep(delay)

    def start_background_evaluation(self, batch_size: int = 10, delay: float = 0.0):
        """启动后台线程执行一次性评估任务（守护线程）。"""
        t = threading.Thread(target=self.evaluate_pending_papers, args=(batch_size, delay), daemon=True)
        t.start()
    
    def process_user_feedback(self, paper_id: int, action: str, user_note: str = None):
        """处理用户反馈"""
        if action == 'favorite':
            # 标记为收藏
            self.db.mark_favorite(paper_id, user_note)
            # 触发增量总结（延后或异步更好，这里直接触发）
            self._trigger_incremental_summary()
        elif action == 'maybe_later':
            # 标记为稍后再说
            self.db.mark_maybe_later(paper_id)
        elif action == 'dislike' or action == 'not_interested':
            # 标记为不喜欢
            self.db.mark_disliked(paper_id)
    
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
        rows = self.db.get_favorites(limit=per_page, offset=offset)
        total = self.db.count_favorites()

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
        rows = self.db.get_maybe_later(limit=per_page, offset=offset)
        total = self.db.count_maybe_later()

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
        # 取消 maybe_later 标记并添加收藏标记
        self.db.unmark_maybe_later(paper_id)
        self.db.mark_favorite(paper_id, user_note)
        # 触发增量总结
        self._trigger_incremental_summary()
    
    def delete_favorite(self, paper_id: int):
        """取消收藏（通过 paper_id）"""
        return self.db.unmark_favorite(paper_id)
    
    def delete_maybe_later(self, paper_id: int):
        """取消稍后再说（通过 paper_id）"""
        return self.db.unmark_maybe_later(paper_id)
    
    def clean_old_papers(self, days_old: int = 30):
        """清理旧论文（保留收藏和稍后再说）"""
        from datetime import datetime, timedelta
        
        cutoff_date = (datetime.now() - timedelta(days=days_old)).strftime('%Y-%m-%d')
        
        # 获取要保留的论文ID（收藏 或 稍后再说）
        protected_result = self.db.execute_query('SELECT id as paper_id FROM papers WHERE favorite = 1 OR maybe_later = 1')
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