#!/usr/bin/env python
"""
测试项目管理功能
"""
import os
import sys
import django
import json

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.core.models import Project, TestCase

def test_project_management():
    """测试项目管理功能"""
    print("=" * 60)
    print("开始测试项目管理功能...")
    print("=" * 60)
    
    # 1. 创建测试项目
    print("\n1. 创建测试项目...")
    project1 = Project.objects.create(
        name="智慧校园平台",
        version="v1.0.0",
        description="智慧校园管理平台第一个版本"
    )
    print(f"   ✅ 创建项目：{project1}")
    
    project2 = Project.objects.create(
        name="AI 测试助手",
        version="v2.1.0",
        description="基于 AI 的测试用例生成助手"
    )
    print(f"   ✅ 创建项目：{project2}")
    
    # 2. 查询所有项目
    print("\n2. 查询所有项目...")
    projects = Project.objects.all()
    for project in projects:
        print(f"   - {project.name} (版本：{project.version})")
    
    # 3. 创建关联项目的测试用例
    print("\n3. 创建关联项目的测试用例...")
    test_case = TestCase.objects.create(
        title="用户登录测试",
        project=project1,
        description="测试用户登录功能",
        test_steps="1. 打开登录页面\n2. 输入用户名和密码\n3. 点击登录按钮",
        expected_results="1. 登录成功\n2. 跳转到首页"
    )
    print(f"   ✅ 创建测试用例：{test_case.title} (所属项目：{project1.name})")
    
    # 4. 查询项目及其关联的测试用例
    print("\n4. 查询项目及其关联的测试用例...")
    project1_with_cases = Project.objects.get(id=project1.id)
    print(f"   项目：{project1_with_cases.name}")
    print(f"   测试用例数量：{project1_with_cases.test_cases.count()}")
    for case in project1_with_cases.test_cases.all():
        print(f"     - {case.title}")
    
    # 5. 更新项目信息
    print("\n5. 更新项目信息...")
    project1.version = "v1.1.0"
    project1.description = "智慧校园管理平台 - 更新版本"
    project1.save()
    print(f"   ✅ 更新项目版本为：{project1.version}")
    
    # 6. 删除项目
    print("\n6. 删除项目测试...")
    project2.delete()
    print(f"   ✅ 删除项目：AI 测试助手")
    
    # 7. 最终项目列表
    print("\n7. 最终项目列表...")
    final_projects = Project.objects.all()
    for project in final_projects:
        print(f"   - {project.name} (版本：{project.version}, 用例数：{project.test_cases.count()})")
    
    print("\n" + "=" * 60)
    print("🎉 项目管理功能测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    test_project_management()
