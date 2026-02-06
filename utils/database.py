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
        # 为了简化测试环境，直接在 papers 表内保存收藏/稍后/不喜欢等状态，移除单独表
        # 如果存在旧的 favorites / maybe_later 表，先删除（测试环境允许直接删除）
        try:
            cursor.execute('DROP TABLE IF EXISTS favorites')
            cursor.execute('DROP TABLE IF EXISTS maybe_later')
        except Exception:
            pass

        # 创建论文表（包含收藏/稍后/不喜欢等字段）
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
                favorite BOOLEAN DEFAULT FALSE,
                favorite_marked_at TEXT,
                maybe_later BOOLEAN DEFAULT FALSE,
                maybe_later_marked_at TEXT,
                disliked BOOLEAN DEFAULT FALSE,
                is_summarized BOOLEAN DEFAULT FALSE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 对于可能存在的旧表结构，尝试按需添加缺失列（更稳健）
        cursor.execute("PRAGMA table_info(papers)")
        columns = [column[1] for column in cursor.fetchall()]
        needed_cols = {
            'recommendation_reason': 'TEXT',
            'chinese_title': 'TEXT',
            'chinese_abstract': 'TEXT',
            'favorite': 'BOOLEAN',
            'favorite_marked_at': 'TEXT',
            'maybe_later': 'BOOLEAN',
            'maybe_later_marked_at': 'TEXT',
            'disliked': 'BOOLEAN',
            'is_summarized': 'BOOLEAN'
        }
        for col, coltype in needed_cols.items():
            if col not in columns:
                try:
                    cursor.execute(f'ALTER TABLE papers ADD COLUMN {col} {coltype}')
                except Exception:
                    pass

        # 如果旧表包含 `favorite_note` 列，则进行迁移：创建新表并复制数据（不包含该列）
        if 'favorite_note' in columns:
            # 构建新表结构（与上面 CREATE TABLE 一致）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS papers_new (
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
                    favorite BOOLEAN DEFAULT FALSE,
                    favorite_marked_at TEXT,
                    maybe_later BOOLEAN DEFAULT FALSE,
                    maybe_later_marked_at TEXT,
                    disliked BOOLEAN DEFAULT FALSE,
                    is_summarized BOOLEAN DEFAULT FALSE,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 将旧表的数据复制到新表（排除 favorite_note 列）
            copy_cols = [c for c in columns if c != 'favorite_note']
            cols_csv = ', '.join(copy_cols)
            cursor.execute(f'INSERT OR REPLACE INTO papers_new ({cols_csv}) SELECT {cols_csv} FROM papers')
            cursor.execute('DROP TABLE papers')
            cursor.execute('ALTER TABLE papers_new RENAME TO papers')
            # 刷新 columns 变量
            cursor.execute("PRAGMA table_info(papers)")
            columns = [column[1] for column in cursor.fetchall()]
        
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

    # 新的状态操作方法（将 favorite / maybe_later / disliked 状态保存在 papers 表）
    def mark_favorite(self, paper_id, user_note=None):
        query = '''
            UPDATE papers SET favorite = 1, favorite_marked_at = datetime('now')
            WHERE id = ?
        '''
        return self.execute_query(query, (paper_id,))

    def unmark_favorite(self, paper_id):
        query = '''
            UPDATE papers SET favorite = 0, favorite_marked_at = NULL
            WHERE id = ?
        '''
        return self.execute_query(query, (paper_id,))

    def mark_maybe_later(self, paper_id):
        query = '''
            UPDATE papers SET maybe_later = 1, maybe_later_marked_at = datetime('now')
            WHERE id = ?
        '''
        return self.execute_query(query, (paper_id,))

    def unmark_maybe_later(self, paper_id):
        query = '''
            UPDATE papers SET maybe_later = 0, maybe_later_marked_at = NULL
            WHERE id = ?
        '''
        return self.execute_query(query, (paper_id,))

    def mark_disliked(self, paper_id):
        query = '''
            UPDATE papers SET disliked = 1 WHERE id = ?
        '''
        return self.execute_query(query, (paper_id,))

    def get_favorites(self, limit=10, offset=0):
        query = '''
            SELECT *, id as paper_id FROM papers
            WHERE favorite = 1
            ORDER BY favorite_marked_at DESC
            LIMIT ? OFFSET ?
        '''
        return self.execute_query(query, (limit, offset))

    def count_favorites(self):
        query = 'SELECT COUNT(*) as total FROM papers WHERE favorite = 1'
        res = self.execute_query(query)
        return res[0]['total'] if res else 0

    def get_maybe_later(self, limit=10, offset=0):
        query = '''
            SELECT *, id as paper_id FROM papers
            WHERE maybe_later = 1
            ORDER BY maybe_later_marked_at DESC
            LIMIT ? OFFSET ?
        '''
        return self.execute_query(query, (limit, offset))

    def count_maybe_later(self):
        query = 'SELECT COUNT(*) as total FROM papers WHERE maybe_later = 1'
        res = self.execute_query(query)
        return res[0]['total'] if res else 0
    
    def get_papers_for_recommendation(self, limit=10):
        """获取待推荐的论文"""
        query = '''
            SELECT * FROM papers 
            WHERE llm_evaluated = FALSE AND is_recommended = FALSE
            ORDER BY published_date DESC
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
        """获取未总结的收藏论文"""
        query = '''
            SELECT * FROM papers
            WHERE favorite = 1 AND is_summarized = FALSE
        '''
        return self.execute_query(query)
    
    def mark_favorite_summarized(self, favorite_id):
        """标记收藏已总结"""
        query = 'UPDATE papers SET is_summarized = TRUE WHERE id = ?'
        return self.execute_query(query, (favorite_id,))
    
    def reset_database(self):
        """重置数据库到初始状态（清空所有数据）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 清空所有数据表
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