import requests
import json
from typing import Optional, Dict, Any
from config import Config
from utils.database import DatabaseManager

class LLMService:
    """LLM服务类"""
    
    def __init__(self):
        self.config = Config()
        self.db = DatabaseManager()
        self._load_config()
    
    def _load_config(self):
        """加载LLM配置"""
        self.base_url = self.db.get_config('LLM_BASE_URL', self.config.DEFAULT_LLM_BASE_URL)
        self.api_key = self.db.get_config('LLM_API_KEY', '')
        self.model = self.db.get_config('LLM_MODEL', self.config.DEFAULT_LLM_MODEL)
    
    def update_config(self, base_url: str, api_key: str, model: str):
        """更新LLM配置"""
        self.db.set_config('LLM_BASE_URL', base_url)
        self.db.set_config('LLM_API_KEY', api_key)
        self.db.set_config('LLM_MODEL', model)
        self._load_config()
    
    def test_connection(self) -> bool:
        """测试LLM连接"""
        if not self.api_key:
            return False
            
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': self.model,
                'messages': [{'role': 'user', 'content': 'Hello, this is a test.'}],
                'max_tokens': 10
            }
            
            response = requests.post(
                f'{self.base_url}/chat/completions',
                headers=headers,
                json=data,
                timeout=10
            )
            
            return response.status_code == 200
        except Exception:
            return False
    
    def refine_user_interests(self, user_input: str) -> str:
        """精炼用户兴趣点"""
        prompt = f"""
        请将以下用户的研究兴趣描述精炼成一段简洁明了的技术兴趣点描述。
        要求：
        1. 保持专业性和准确性
        2. 突出关键技术领域和研究方向
        3. 便于后续论文推荐使用
        4. 字数控制在100-200字之间
        
        用户原始描述：
        {user_input}
        
        请直接返回精炼后的兴趣点描述：
        """
        
        return self._call_llm(prompt)
    
    def summarize_favorites(self, papers_data: list, current_summary: str = "") -> str:
        """增量总结收藏论文"""
        if not papers_data:
            return current_summary
            
        papers_text = "\n".join([
            f"论文{i+1}: {paper.get('title', '')}\n摘要: {paper.get('abstract', '')[:200]}..."
            for i, paper in enumerate(papers_data)
        ])
        
        if current_summary:
            prompt = f"""
            基于以下已有的用户兴趣总结和新增的收藏论文，请更新用户的兴趣总结：
            
            当前兴趣总结：
            {current_summary}
            
            新增收藏论文：
            {papers_text}
            
            请结合已有总结和新增论文，给出更新后的用户兴趣总结。
            要求：
            1. 保持总结的专业性和准确性
            2. 突出用户的核心研究兴趣
            3. 如果新增论文展现了新的研究方向，请适当扩展总结
            4. 字数控制在150-250字之间
            
            请直接返回更新后的兴趣总结：
            """
        else:
            prompt = f"""
            基于以下用户收藏的论文，请总结用户的研究兴趣：
            
            收藏论文：
            {papers_text}
            
            请总结用户的研究兴趣，要求：
            1. 保持专业性和准确性
            2. 突出用户的核心研究领域
            3. 识别主要的技术方向和应用场景
            4. 字数控制在150-250字之间
            
            请直接返回兴趣总结：
            """
        
        return self._call_llm(prompt)
    
    def evaluate_paper(self, paper_data: Dict, user_interests: str, favorite_summary: str) -> Dict[str, Any]:
        """评估论文推荐价值，返回推荐结果和理由"""
        paper_info = f"""
        标题: {paper_data.get('title', '')}
        摘要: {paper_data.get('abstract', '')}
        分类: {', '.join(json.loads(paper_data.get('categories', '[]')))}
        """
        
        prompt = f"""
        你是一个专业的学术论文推荐助手。请根据以下信息判断这篇论文是否值得推荐给用户，并给出简短的推荐理由。
        
        用户初始兴趣点：
        {user_interests}
        
        用户收藏论文总结出的兴趣：
        {favorite_summary}
        
        待评估论文信息：
        {paper_info}
        
        请严格按照以下JSON格式回复（不要包含其他文字）：
        {{
            "is_recommended": true/false,
            "reason": "简短的推荐或不推荐理由（不超过50字）"
        }}
        """
        
        response = self._call_llm(prompt)
        
        try:
            # 清理可能的Markdown代码块标记
            response = response.replace('```json', '').replace('```', '').strip()
            result = json.loads(response)
            return {
                'is_recommended': result.get('is_recommended', False),
                'reason': result.get('reason', '无')
            }
        except Exception as e:
            print(f"解析评估结果时出错: {e}，原始响应: {response}")
            return {
                'is_recommended': False,
                'reason': '评估失败'
            }
    
    def translate_paper_info(self, title: str, abstract: str) -> Dict[str, str]:
        """翻译论文标题和摘要"""
        prompt = f"""
        请将以下英文学术论文的标题和摘要翻译成中文：
        
        英文标题: {title}
        英文摘要: {abstract}
        
        请严格按照以下JSON格式返回翻译结果：
        {{
            "chinese_title": "中文标题",
            "chinese_abstract": "中文摘要"
        }}
        
        要求：
        1. 保持学术性和准确性
        2. 中文标题要简洁明了
        3. 中文摘要要完整传达原意
        4. 直接返回JSON，不要添加其他文字
        """
        
        response = self._call_llm(prompt, max_tokens=1000)
        
        try:
            # 清理可能的Markdown代码块标记
            response = response.replace('```json', '').replace('```', '').strip()
            translation_result = json.loads(response)
            return {
                'chinese_title': translation_result.get('chinese_title', ''),
                'chinese_abstract': translation_result.get('chinese_abstract', '')
            }
        except Exception as e:
            print(f"解析翻译结果时出错: {e}")
            return {
                'chinese_title': '',
                'chinese_abstract': ''
            }
    
    def _call_llm(self, prompt: str, max_tokens: int = 500) -> str:
        """调用LLM API"""
        if not self.api_key:
            raise ValueError("LLM API key未配置")
        
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': self.model,
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': max_tokens,
                'temperature': 0.7
            }
            
            response = requests.post(
                f'{self.base_url}/chat/completions',
                headers=headers,
                json=data,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0]['message']['content'].strip()
            else:
                raise ValueError("LLM返回格式异常")
                
        except Exception as e:
            print(f"调用LLM时出错: {e}")
            raise