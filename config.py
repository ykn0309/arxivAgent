import os
from datetime import datetime

class Config:
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'arxiv-agent-secret-key'
    
    # 数据库配置
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DATABASE_PATH = os.path.join(BASE_DIR, 'data', 'arxiv_agent.db')
    
    # arXiv API配置
    ARXIV_API_BASE = 'http://export.arxiv.org/api/query'
    ARXIV_SEARCH_BASE = 'http://arxiv.org/search'
    
    # 默认配置值
    DEFAULT_CATEGORIES = ['cs.AI', 'cs.LG', 'cs.CL']  # 默认关注的CS子分区
    DEFAULT_TIME_WINDOW_DAYS = 7  # 默认时间窗口天数
    
    # LLM默认配置
    DEFAULT_LLM_BASE_URL = 'https://api.openai.com/v1'
    DEFAULT_LLM_MODEL = 'gpt-3.5-turbo'
    
    # 系统配置键名
    CONFIG_KEYS = {
        'llm_base_url': 'LLM_BASE_URL',
        'llm_api_key': 'LLM_API_KEY',
        'llm_model': 'LLM_MODEL',
        'user_interests': 'USER_INTERESTS',
        'categories': 'CATEGORIES',
        'favorite_summary': 'FAVORITE_SUMMARY'
    }
    
    @staticmethod
    def get_database_uri():
        """获取数据库URI"""
        return f'sqlite:///{Config.DATABASE_PATH}'
    
    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        pass