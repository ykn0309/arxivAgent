import sqlite3
import json
from datetime import datetime
import os
from config import Config

class DatabaseManager:
    """数据库管理工具类"""
    
    def __init__(self, db_path=None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        # 确保数据目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建论文表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                arxiv_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                abstract TEXT,
                authors TEXT,
                categories TEXT,
                published_date TEXT,
                updated_date TEXT,
                pdf_url TEXT,
                arxiv_url TEXT,
                is_recommended BOOLEAN DEFAULT FALSE,
                llm_evaluated BOOLEAN DEFAULT FALSE,
                recommendation_reason TEXT,
                chinese_title TEXT,
                chinese_abstract TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 旧的 `favorites` / `maybe_later` 表已迁移到 papers.user_status。
        # 不再在新版本中创建这些独立表，保留迁移代码以处理历史数据。
        
        # 创建配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 迁移：为已有的 papers 表添加列（如果不存在）
        cursor.execute("PRAGMA table_info(papers)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'recommendation_reason' not in columns:
            cursor.execute('ALTER TABLE papers ADD COLUMN recommendation_reason TEXT')
        if 'chinese_title' not in columns:
            cursor.execute('ALTER TABLE papers ADD COLUMN chinese_title TEXT')
        if 'chinese_abstract' not in columns:
            cursor.execute('ALTER TABLE papers ADD COLUMN chinese_abstract TEXT')
        if 'user_status' not in columns:
            # user_status: 'none' | 'favorite' | 'maybe_later' | 'dislike'
            cursor.execute("ALTER TABLE papers ADD COLUMN user_status TEXT DEFAULT 'none'")
        if 'favorite_summarized' not in columns:
            cursor.execute("ALTER TABLE papers ADD COLUMN favorite_summarized BOOLEAN DEFAULT FALSE")

        # 如果历史上存在 favorites / maybe_later 表，则迁移它们的数据到 papers.user_status
        # 并删除冗余表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='favorites'")
        if cursor.fetchone():
            try:
                # 将 favorites 表中的 paper_id 标记为 favorite
                cursor.execute('SELECT paper_id FROM favorites')
                fav_rows = cursor.fetchall()
                for row in fav_rows:
                    cursor.execute("UPDATE papers SET user_status = 'favorite' WHERE id = ?", (row[0],))
                # 将 maybe_later 表中的 paper_id 标记为 maybe_later
                cursor.execute('SELECT paper_id FROM maybe_later')
                ml_rows = cursor.fetchall()
                for row in ml_rows:
                    cursor.execute("UPDATE papers SET user_status = 'maybe_later' WHERE id = ?", (row[0],))
                # 删除旧表
                cursor.execute('DROP TABLE IF EXISTS favorites')
                cursor.execute('DROP TABLE IF EXISTS maybe_later')
            except Exception:
                # 如果迁移失败，不要阻塞启动
                pass
        
        conn.commit()
        conn.close()
    
    def execute_query(self, query, params=None):
        """执行查询"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if query.strip().upper().startswith('SELECT'):
                result = cursor.fetchall()
            else:
                conn.commit()
                result = cursor.lastrowid if 'INSERT' in query.upper() else cursor.rowcount
            
            return result
        finally:
            conn.close()
    
    def insert_paper(self, paper_data):
        """插入论文数据"""
        query = '''
            INSERT OR IGNORE INTO papers 
            (arxiv_id, title, abstract, authors, categories, published_date, updated_date, pdf_url, arxiv_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        params = (
            paper_data['arxiv_id'],
            paper_data['title'],
            paper_data['abstract'],
            json.dumps(paper_data.get('authors', [])),
            json.dumps(paper_data.get('categories', [])),
            paper_data.get('published_date'),
            paper_data.get('updated_date'),
            paper_data.get('pdf_url'),
            paper_data.get('arxiv_url')
        )
        return self.execute_query(query, params)
    
    def get_papers_for_recommendation(self, limit=10):
        """获取待推荐的论文"""
        # 优先返回已被LLM评估且被推荐但尚未被用户标记的论文（user_status = 'none'）
        # 其次返回尚未被LLM评估的论文
        query = '''
            SELECT * FROM papers
            WHERE (
                (llm_evaluated = TRUE AND is_recommended = TRUE AND user_status = 'none')
                OR (llm_evaluated = FALSE)
            )
            ORDER BY CASE WHEN is_recommended = TRUE THEN 0 ELSE 1 END, published_date DESC
            LIMIT ?
        '''
        return self.execute_query(query, (limit,))
    
    def update_paper_evaluation(self, paper_id, is_recommended, llm_evaluated=True, recommendation_reason=None):
        """更新论文评估状态"""
        query = '''
            UPDATE papers 
            SET is_recommended = ?, llm_evaluated = ?, recommendation_reason = ?
            WHERE id = ?
        '''
        return self.execute_query(query, (is_recommended, llm_evaluated, recommendation_reason, paper_id))
    
    def update_paper_translation(self, paper_id, chinese_title=None, chinese_abstract=None):
        """更新论文的中文翻译"""
        query = '''
            UPDATE papers 
            SET chinese_title = ?, chinese_abstract = ?
            WHERE id = ?
        '''
        return self.execute_query(query, (chinese_title, chinese_abstract, paper_id))

    def set_user_status(self, paper_id, status='none'):
        """设置论文的用户状态（favorite/maybe_later/dislike/none）"""
        query = '''
            UPDATE papers SET user_status = ? WHERE id = ?
        '''
        return self.execute_query(query, (status, paper_id))

    def get_papers_by_user_status(self, status, limit=10, offset=0):
        query = '''
            SELECT * FROM papers
            WHERE user_status = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        '''
        return self.execute_query(query, (status, limit, offset))
    
    # Legacy helper methods for old tables were removed. Use `set_user_status(paper_id, status)` instead.
    
    def get_config(self, key, default=None):
        """获取配置值"""
        query = 'SELECT value FROM config WHERE key = ?'
        result = self.execute_query(query, (key,))
        if result:
            return result[0]['value']
        return default
    
    def set_config(self, key, value):
        """设置配置值"""
        query = '''
            INSERT OR REPLACE INTO config (key, value, updated_at)
            VALUES (?, ?, datetime('now'))
        '''
        return self.execute_query(query, (key, str(value)))
    
    def get_unsummarized_favorites(self):
        """获取未总结的收藏论文（迁移后基于 papers.user_status）"""
        query = '''
            SELECT p.*
            FROM papers p
            WHERE p.user_status = 'favorite' AND (p.favorite_summarized IS NULL OR p.favorite_summarized = FALSE)
        '''
        return self.execute_query(query)
    
    def mark_favorite_summarized(self, favorite_id):
        """标记收藏已总结（传入 paper_id）"""
        query = 'UPDATE papers SET favorite_summarized = TRUE WHERE id = ?'
        return self.execute_query(query, (favorite_id,))
    
    def reset_database(self):
        """重置数据库到初始状态（清空所有数据）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 清空所有数据表（旧表已合并至 `papers`）
            tables = ['papers', 'config']
            for table in tables:
                cursor.execute(f'DELETE FROM {table}')
            
            # 重置自增ID
            for table in tables:
                cursor.execute(f'DELETE FROM sqlite_sequence WHERE name = "{table}"')
            
            conn.commit()
            print("数据库已重置到初始状态")
            return True
        except Exception as e:
            print(f"重置数据库时出错: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()