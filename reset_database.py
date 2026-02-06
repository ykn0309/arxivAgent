#!/usr/bin/env python3
"""
数据库重置脚本
将arxivAgent数据库恢复到初始状态
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.database import DatabaseManager

def reset_database():
    """重置数据库"""
    print("=== arxivAgent 数据库重置工具 ===")
    print("警告：此操作将删除所有数据，包括：")
    print("- 所有爬取的论文记录")
    print("- 所有收藏记录")
    print("- 所有稍后再说记录")
    print("- 所有用户配置")
    print()
    
    confirm = input("请输入 'RESET' 确认重置数据库: ")
    if confirm != 'RESET':
        print("取消重置操作")
        return False
    
    try:
        db = DatabaseManager()
        success = db.reset_database()
        
        if success:
            print("\n✅ 数据库重置成功！")
            print("系统已恢复到初始状态，需要重新进行初始配置。")
            return True
        else:
            print("\n❌ 数据库重置失败！")
            return False
            
    except Exception as e:
        print(f"\n❌ 重置过程中发生错误: {e}")
        return False

if __name__ == "__main__":
    success = reset_database()
    sys.exit(0 if success else 1)