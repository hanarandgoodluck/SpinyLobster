"""
Django production settings for StarDragon
部署到 106.12.23.83 时使用此配置
"""

import os
from pathlib import Path

# 导入基础配置
from config.settings import *

# ============================================
# 生产环境配置
# ============================================

# 关闭调试模式
DEBUG = False

# 允许的主机
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    '106.12.23.83',  # 服务器公网IP
]

# 安全的 SECRET_KEY（请替换为随机生成的密钥）
# 生成方法: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'change-this-to-random-secret-key-in-production')

# 数据库配置 - Docker MySQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'test_brain_db',
        'USER': 'root',
        'PASSWORD': '583471755a',  # Docker MySQL 密码
        'HOST': '127.0.0.1',  # Docker MySQL 在本机
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# 静态文件配置
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# 媒体文件配置
MEDIA_ROOT = os.path.join(BASE_DIR, 'uploads')
MEDIA_URL = '/uploads/'

# 安全设置
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Session 安全设置
SESSION_COOKIE_SECURE = False  # 如果使用 HTTPS，改为 True
CSRF_COOKIE_SECURE = False  # 如果使用 HTTPS，改为 True

# CSRF 信任的来源
CSRF_TRUSTED_ORIGINS = [
    'http://106.12.23.83',
    'http://localhost',
]

# 日志配置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'production.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'WARNING',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['file', 'console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# AI 模型配置 - 建议通过环境变量或数据库配置
# LLM_PROVIDERS 保持不变，但 API Key 应该通过环境变量设置
LLM_PROVIDERS['deepseek']['api_key'] = os.environ.get('DEEPSEEK_API_KEY', '')

# Java 分析服务地址（如果部署在同一服务器）
JAVA_ANALYZER_SERVICE_URL = os.environ.get('JAVA_ANALYZER_SERVICE_URL', 'http://localhost:8089')

# Milvus 配置（如果启用）
if ENABLE_MILVUS:
    VECTOR_DB_CONFIG = {
        'host': os.environ.get('MILVUS_HOST', 'localhost'),
        'port': os.environ.get('MILVUS_PORT', '19530'),
        'collection_name': 'vv_knowledge_collection',
    }
