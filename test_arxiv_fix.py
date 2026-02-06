#!/usr/bin/env python3
"""
arxivAgent 功能测试脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.arxiv_service import ArxivService
from services.llm_service import LLMService
from services.recommendation_service import RecommendationService
from utils.database import DatabaseManager

def test_database():
    """测试数据库连接和基本操作"""
    print("🧪 测试数据库功能...")
    try:
        db = DatabaseManager()
        # 测试基本查询
        result = db.execute_query("SELECT 1")
        print("✅ 数据库连接正常")
        return True
    except Exception as e:
        print(f"❌ 数据库测试失败: {e}")
        return False

def test_arxiv_service():
    """测试arXiv爬虫服务"""
    print("\n🧪 测试arXiv服务...")
    try:
        service = ArxivService()
        # 测试获取分类信息
        categories = service.get_cs_categories()
        print(f"✅ 成功获取 {len(categories)} 个CS分类")
        
        # 测试爬取功能（小范围测试）
        print("🔍 正在进行小范围爬取测试...")
        count = service.crawl_recent_papers(['cs.AI'])
        print(f"✅ 成功爬取 {count} 篇论文")
        return True
    except Exception as e:
        print(f"❌ arXiv服务测试失败: {e}")
        return False

def test_llm_service():
    """测试LLM服务（需要配置）"""
    print("\n🧪 测试LLM服务...")
    try:
        service = LLMService()
        # 检查是否有配置
        if not service.api_key:
            print("⚠️  LLM未配置，跳过测试")
            return True
            
        # 测试连接
        success = service.test_connection()
        if success:
            print("✅ LLM连接测试通过")
            return True
        else:
            print("❌ LLM连接测试失败")
            return False
    except Exception as e:
        print(f"❌ LLM服务测试失败: {e}")
        return False

def test_recommendation_service():
    """测试推荐服务"""
    print("\n🧪 测试推荐服务...")
    try:
        service = RecommendationService()
        print("✅ 推荐服务初始化成功")
        return True
    except Exception as e:
        print(f"❌ 推荐服务测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 50)
    print("arxivAgent 功能测试")
    print("=" * 50)
    
    tests = [
        ("数据库测试", test_database),
        ("arXiv服务测试", test_arxiv_service),
        ("LLM服务测试", test_llm_service),
        ("推荐服务测试", test_recommendation_service)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！")
        return True
    else:
        print("⚠️  部分测试失败，请检查配置")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)