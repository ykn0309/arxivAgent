from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime

class UserInterest(Base):
    """用户兴趣模型"""
    __tablename__ = 'user_interests'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    interest_text = Column(Text, nullable=False)  # 用户兴趣描述
    refined_interest = Column(Text)  # 经过LLM精炼的兴趣点
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'interest_text': self.interest_text,
            'refined_interest': self.refined_interest,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }