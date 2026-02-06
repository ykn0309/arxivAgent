from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Paper(Base):
    """论文模型"""
    __tablename__ = 'papers'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    arxiv_id = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(Text, nullable=False)
    abstract = Column(Text)
    authors = Column(Text)  # 存储作者列表的JSON字符串
    categories = Column(Text)  # 存储分类列表的JSON字符串
    published_date = Column(DateTime)
    updated_date = Column(DateTime)
    pdf_url = Column(String(200))
    arxiv_url = Column(String(200))
    is_recommended = Column(Boolean, default=False)
    llm_evaluated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    # 新增字段：推荐理由、中文翻译与用户状态
    recommendation_reason = Column(Text)
    chinese_title = Column(Text)
    chinese_abstract = Column(Text)
    user_status = Column(String(20), default='none', index=True)  # 'none'|'favorite'|'maybe_later'|'dislike'
    favorite_summarized = Column(Boolean, default=False)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'arxiv_id': self.arxiv_id,
            'title': self.title,
            'abstract': self.abstract,
            'authors': self.authors,
            'categories': self.categories,
            'published_date': self.published_date.isoformat() if self.published_date else None,
            'updated_date': self.updated_date.isoformat() if self.updated_date else None,
            'pdf_url': self.pdf_url,
            'arxiv_url': self.arxiv_url,
            'is_recommended': self.is_recommended,
            'llm_evaluated': self.llm_evaluated,
            'created_at': self.created_at.isoformat() if self.created_at else None
            ,
            'recommendation_reason': self.recommendation_reason,
            'chinese_title': self.chinese_title,
            'chinese_abstract': self.chinese_abstract,
            'user_status': self.user_status,
            'favorite_summarized': self.favorite_summarized
        }

# ORM 模型 `Favorite` 与 `MaybeLater` 已移除；用户状态统一存储在 `papers.user_status` 中。

class SystemConfig(Base):
    """系统配置模型"""
    __tablename__ = 'config'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }