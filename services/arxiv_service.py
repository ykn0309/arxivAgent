import requests
import feedparser
from datetime import datetime, timedelta
import time
from typing import List, Dict, Optional
from config import Config
from utils.database import DatabaseManager

class ArxivService:
    """arXiv论文爬虫服务"""
    
    def __init__(self):
        self.config = Config()
        self.db = DatabaseManager()
        self.base_url = self.config.ARXIV_API_BASE
        
    def build_search_query(self, categories: List[str], start_date: str, end_date: str) -> str:
        """构建arXiv搜索查询"""
        # 构建分类搜索条件
        category_conditions = " OR ".join([f"cat:{cat}" for cat in categories])
        
        # 构建日期搜索条件
        date_condition = f"lastUpdatedDate:[{start_date} TO {end_date}]"
        
        # 组合查询
        search_query = f"search_query=({category_conditions}) AND {date_condition}"
        return search_query
    
    def parse_arxiv_entry(self, entry) -> Dict:
        """解析arXiv条目"""
        # 提取arXiv ID
        arxiv_id = entry.id.split('/abs/')[-1]
        
        # 提取分类
        categories = []
        if hasattr(entry, 'tags'):
            for tag in entry.tags:
                if hasattr(tag, 'term'):
                    categories.append(tag.term)
        
        # 提取作者
        authors = []
        if hasattr(entry, 'authors'):
            for author in entry.authors:
                authors.append(author.name)
        
        # 解析日期
        published_date = None
        updated_date = None
        if hasattr(entry, 'published'):
            published_date = datetime.strptime(entry.published, '%Y-%m-%dT%H:%M:%SZ')
        if hasattr(entry, 'updated'):
            updated_date = datetime.strptime(entry.updated, '%Y-%m-%dT%H:%M:%SZ')
        
        return {
            'arxiv_id': arxiv_id,
            'title': entry.title,
            'abstract': entry.summary,
            'authors': authors,
            'categories': categories,
            'published_date': published_date.strftime('%Y-%m-%d') if published_date else None,
            'updated_date': updated_date.strftime('%Y-%m-%d') if updated_date else None,
            'pdf_url': f'http://arxiv.org/pdf/{arxiv_id}',
            'arxiv_url': f'http://arxiv.org/abs/{arxiv_id}'
        }
    
    def fetch_papers(self, categories: List[str], start_date: str, end_date: str, max_results: int = 1000) -> List[Dict]:
        """获取指定时间段内的论文"""
        papers = []
        
        # 构建查询参数
        search_params = self.build_search_query(categories, start_date, end_date)
        url = f"{self.base_url}?{search_params}&sortBy=lastUpdatedDate&sortOrder=descending&max_results={max_results}"
        
        try:
            # 发送请求
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # 解析RSS feed
            feed = feedparser.parse(response.content)
            
            # 解析每个条目
            for entry in feed.entries:
                paper_data = self.parse_arxiv_entry(entry)
                papers.append(paper_data)
                
        except Exception as e:
            print(f"获取论文时出错: {e}")
            return []
        
        return papers
    
    def crawl_recent_papers(self, force_categories: Optional[List[str]] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> int:
        """爬取论文，支持可选的日期范围（YYYY-MM-DD）。

        如果提供 `start_date`/`end_date`，将使用该范围，否则使用基于 `LAST_CRAWL_DATE` 的默认逻辑。
        """
        # 获取配置的分类
        categories_str = self.db.get_config('CATEGORIES', '')
        if force_categories:
            categories = force_categories
        elif categories_str:
            categories = categories_str.split(',')
        else:
            categories = self.config.DEFAULT_CATEGORIES
        
        # 如果显式提供了 start_date/end_date（格式 YYYY-MM-DD），使用它们
        if start_date or end_date:
            try:
                if start_date:
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                else:
                    start_dt = datetime.now() - timedelta(days=30)

                if end_date:
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                else:
                    end_dt = datetime.now()
            except Exception as e:
                print(f"解析传入日期失败: {e}")
                return 0

        else:
            # 确定爬取时间范围（基于上次爬取日期或默认最近7天）
            last_crawl_date_str = self.db.get_config('LAST_CRAWL_DATE')

            if last_crawl_date_str:
                # 如果存在上次抓取日期：从该日期（包含）开始，直到今天（包含）
                last_crawl_date = datetime.strptime(last_crawl_date_str, '%Y-%m-%d')
                start_dt = last_crawl_date
                end_dt = datetime.now()
            else:
                # 初次使用：抓取最近7天（包含今天）
                end_dt = datetime.now()
                start_dt = datetime.now() - timedelta(days=6)

        # 如果计算得到的起始日期晚于结束日期，调整为相同日期（避免反向区间）
        if start_dt > end_dt:
            start_dt = end_dt

        # arXiv API 期望 YYYYMMDD 格式
        start_date = start_dt.strftime('%Y%m%d')
        end_date = end_dt.strftime('%Y%m%d')
        
        print(f"爬取时间范围: {start_date} 到 {end_date}")
        print(f"关注分类: {categories}")
        
        # 获取论文
        papers = self.fetch_papers(categories, start_date, end_date)
        
        # 保存到数据库
        saved_count = 0
        for paper in papers:
            result = self.db.insert_paper(paper)
            try:
                saved_count += int(result)
            except Exception:
                if result:
                    saved_count += 1
        
        # 更新最后爬取日期
        today_str = datetime.now().strftime('%Y-%m-%d')
        self.db.set_config('LAST_CRAWL_DATE', today_str)
        
        print(f"成功爬取并保存 {saved_count} 篇论文")
        return saved_count
    
    def get_cs_categories(self) -> Dict[str, str]:
        """获取CS分区下的所有子分区及其简介"""
        return {
            'cs.AI': '人工智能：涵盖人工智能的所有领域，但不包括计算机视觉、机器人、机器学习、多智能体系统以及计算与语言（自然语言处理）',
            'cs.AR': '硬件体系结构：涵盖计算机系统组织与硬件体系结构，包括处理器结构、存储系统、并行体系结构及相关硬件设计问题',
            'cs.CC': '计算复杂性理论：研究计算模型、复杂性类别、结构复杂性、复杂性权衡以及上下界证明等问题',
            'cs.CE': '计算工程、金融与科学：涵盖计算机科学在科学、工程和金融领域中的应用，强调复杂系统的数学建模与大规模计算',
            'cs.CG': '计算几何：研究几何对象及其算法问题，包括点、线、多边形、多维几何结构及其计算复杂性',
            'cs.CL': '计算与语言（自然语言处理）：涵盖自然语言处理与计算语言学，包括文本、语音、语言理解与生成等问题',
            'cs.CR': '密码学与安全：涵盖密码学与信息安全的各个方面，包括加密算法、认证机制、公钥系统、安全协议等',
            'cs.CV': '计算机视觉与模式识别：涵盖图像处理、计算机视觉、模式识别和场景理解等内容',
            'cs.CY': '计算机与社会：研究计算技术对社会的影响，包括计算机伦理、信息技术政策、法律问题、教育等',
            'cs.DB': '数据库：涵盖数据库管理系统、数据挖掘、数据处理与查询优化等内容',
            'cs.DC': '分布式、并行与集群计算：涵盖分布式系统、并行计算、集群计算及相关算法',
            'cs.DL': '数字图书馆：涵盖数字图书馆的设计、构建与管理，以及文档与文本的创建、存储和访问',
            'cs.DM': '离散数学：涵盖组合数学、图论以及概率论在计算机科学中的应用',
            'cs.DS': '数据结构与算法：研究数据结构设计与算法分析，包括时间复杂度、空间复杂度及算法效率',
            'cs.ET': '新兴技术：涵盖超越传统硅基CMOS技术的信息处理方法，如纳米电子、光子、量子、自旋、超导、生物计算等',
            'cs.FL': '形式语言与自动机理论：研究自动机、形式语言、语法理论及字符串组合性质',
            'cs.GL': '综合与通论：包括综述文章、教材性内容、未来趋势预测、人物传记及其他杂项计算机科学文献',
            'cs.GR': '计算机图形学：涵盖计算机图形学的各个方面，如建模、渲染、动画与图形系统',
            'cs.GT': '计算机科学与博弈论：研究计算机科学与博弈论的交叉领域，包括机制设计、计算博弈、博弈学习等',
            'cs.HC': '人机交互：涵盖人机界面、用户体验、协同计算与人因工程等内容',
            'cs.IR': '信息检索：研究信息索引、搜索、检索模型、内容分析与评估方法',
            'cs.IT': '信息论：涵盖信息论与编码理论的理论与实验研究，包括信源编码、信道编码及相关数学基础',
            'cs.LG': '机器学习：涵盖机器学习的所有方面，包括监督学习、无监督学习、强化学习、鲁棒性、公平性、可解释性等',
            'cs.LO': '计算机科学中的逻辑：研究逻辑在计算机科学中的应用，包括程序逻辑、模型论、模态逻辑、形式化验证等',
            'cs.MA': '多智能体系统：涵盖多智能体系统、分布式人工智能、智能体建模、协作与交互机制及其应用',
            'cs.MM': '多媒体：涵盖多媒体信息的表示、处理与交互，如音视频系统与多媒体应用',
            'cs.MS': '数学软件：涵盖用于数学计算的算法、系统与软件工具',
            'cs.NA': '数值分析：等同于math.NA，研究数值计算方法及其误差分析',
            'cs.NE': '神经与进化计算：涵盖神经网络、进化算法、遗传算法、人工生命与自适应行为等',
            'cs.NI': '网络与互联网体系结构：涵盖计算机网络与互联网架构，包括协议设计、网络性能、互联标准等',
            'cs.OH': '其他计算机科学：用于不适合归入其他任何计算机科学子分区的研究工作',
            'cs.OS': '操作系统：涵盖操作系统的设计与实现，包括进程管理、内存管理、文件系统与系统安全',
            'cs.PF': '性能分析：研究系统性能评测、排队理论与仿真分析',
            'cs.PL': '程序设计语言：涵盖编程语言的语义、语言特性、编程范式以及与语言相关的编译技术',
            'cs.RO': '机器人学：涵盖机器人感知、规划、控制与系统集成等问题',
            'cs.SC': '符号计算：研究符号代数、计算代数系统及相关理论与实现',
            'cs.SD': '声音与音频计算：涵盖声音建模、分析、合成、音频接口、计算机音乐与声学信号处理',
            'cs.SE': '软件工程：涵盖软件设计方法、开发工具、测试、调试、软件质量与工程实践',
            'cs.SI': '社会与信息网络：研究社会网络与信息网络的建模、分析与应用，包括在线社交系统与信息传播',
            'cs.SY': '系统与控制：等同于eess.SY，涵盖控制系统的分析与设计，包括非线性、随机、鲁棒与分布式控制'
        }