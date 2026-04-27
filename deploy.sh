#!/bin/bash

#############################################
# StarDragon 自动化部署脚本
# 服务器: 106.12.23.83
#############################################

set -e  # 遇到错误立即退出

echo "========================================="
echo "StarDragon 自动化部署脚本"
echo "========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置变量
PROJECT_DIR="/opt/stardragon"
VENV_DIR="${PROJECT_DIR}/venv"
MYSQL_PASSWORD="583471755a"
DB_NAME="test_brain_db"

# 打印信息函数
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否以 root 运行
if [ "$EUID" -ne 0 ]; then 
    print_error "请使用 root 用户或 sudo 运行此脚本"
    exit 1
fi

# 步骤 1: 安装系统依赖
print_info "步骤 1: 安装系统依赖..."
if command -v yum &> /dev/null; then
    # CentOS/RHEL
    yum update -y
    yum install -y git python3 python3-pip python3-devel mysql-devel gcc nginx wget curl
elif command -v apt &> /dev/null; then
    # Ubuntu/Debian
    apt update && apt upgrade -y
    apt install -y git python3 python3-pip python3-dev default-libmysqlclient-dev build-essential nginx wget curl
else
    print_error "不支持的操作系统"
    exit 1
fi

# 步骤 2: 检查并启动 MySQL Docker 容器
print_info "步骤 2: 检查 MySQL Docker 容器..."
if ! command -v docker &> /dev/null; then
    print_warning "Docker 未安装，正在安装..."
    curl -fsSL https://get.docker.com | sh
    systemctl start docker
    systemctl enable docker
fi

# 查找 MySQL 容器（支持各种命名方式）
MYSQL_CONTAINER=$(docker ps --format '{{.Names}}' | grep -i mysql | head -n 1)

if [ -z "$MYSQL_CONTAINER" ]; then
    print_info "启动 MySQL Docker 容器..."
    docker run -d \
        --name mysql \
        -p 3306:3306 \
        -e MYSQL_ROOT_PASSWORD=${MYSQL_PASSWORD} \
        -e MYSQL_DATABASE=${DB_NAME} \
        -v /data/mysql:/var/lib/mysql \
        --restart=always \
        mysql:8.0
    
    MYSQL_CONTAINER="mysql"
    # 等待 MySQL 启动
    print_info "等待 MySQL 启动..."
    sleep 15
else
    print_info "MySQL 容器已在运行: $MYSQL_CONTAINER"
fi

# 确保数据库存在
docker exec -it $MYSQL_CONTAINER mysql -uroot -p${MYSQL_PASSWORD} -e "CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null || true

# 步骤 3: 创建项目目录并上传代码
print_info "步骤 3: 准备项目目录..."
mkdir -p ${PROJECT_DIR}

# 如果项目目录为空，提示用户上传代码
if [ -z "$(ls -A ${PROJECT_DIR})" ]; then
    print_warning "项目目录为空，请上传代码到 ${PROJECT_DIR}"
    print_info "可以使用以下命令从本地上传："
    echo "scp -r F:\\test\\TestBranin root@106.12.23.83:${PROJECT_DIR}"
    read -p "按回车键继续..."
fi

cd ${PROJECT_DIR}

# 步骤 4: 创建 Python 虚拟环境
print_info "步骤 4: 创建 Python 虚拟环境..."
if [ ! -d "${VENV_DIR}" ]; then
    python3 -m venv ${VENV_DIR}
fi

source ${VENV_DIR}/bin/activate

# 步骤 5: 安装 Python 依赖
print_info "步骤 5: 安装 Python 依赖..."
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# 步骤 6: 配置 Django
print_info "步骤 6: 配置 Django..."

# 只在第一次部署时备份（如果 settings.py.bak 不存在）
if [ ! -f "config/settings.py.bak" ]; then
    cp config/settings.py config/settings.py.bak
    print_info "已备份原始 settings.py"
else
    print_info "检测到已有备份，使用当前 settings.py（不会被覆盖）"
fi

# 修改 settings.py（使用安全的字符串替换而非正则）
python3 << 'PYEOF'
import os

with open('config/settings.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip_until_closing = False
database_block_depth = 0
in_databases_block = False

for line in lines:
    # 检测 DATABASES 块开始
    if 'DATABASES = {' in line and not in_databases_block:
        in_databases_block = True
        skip_until_closing = True
        database_block_depth = 1
        # 写入新的配置
        new_lines.append("DATABASES = {\n")
        new_lines.append("    'default': {\n")
        new_lines.append("        'ENGINE': 'django.db.backends.mysql',\n")
        new_lines.append(f"        'NAME': '{os.environ.get('DB_NAME', 'test_brain_db')}',\n")
        new_lines.append("        'USER': 'root',\n")
        new_lines.append(f"        'PASSWORD': '{os.environ.get('MYSQL_PASSWORD', '583471755a')}',\n")
        new_lines.append("        'HOST': '127.0.0.1',\n")
        new_lines.append("        'PORT': '3306',\n")
        new_lines.append("    }\n")
        new_lines.append("}\n")
        continue
    
    # 如果在 DATABASES 块中，计算括号深度
    if skip_until_closing:
        for char in line:
            if char == '{':
                database_block_depth += 1
            elif char == '}':
                database_block_depth -= 1
                if database_block_depth == 0:
                    skip_until_closing = False
                    in_databases_block = False
                    break
        continue
    
    new_lines.append(line)

# 修改 ALLOWED_HOSTS
content = ''.join(new_lines)
old_hosts = """ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    '172.16.32.88',
    '172.16.56.57',
]"""

new_hosts = """ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    '106.12.23.83',
]"""

content = content.replace(old_hosts, new_hosts)

# 关闭 DEBUG
content = content.replace("DEBUG = True", "DEBUG = False")

with open('config/settings.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Settings updated successfully")
PYEOF

# 步骤 7: 数据库迁移
print_info "步骤 7: 执行数据库迁移..."
python manage.py makemigrations
python manage.py migrate

# 步骤 8: 收集静态文件
print_info "步骤 8: 收集静态文件..."
mkdir -p staticfiles
python manage.py collectstatic --noinput

# 步骤 9: 创建必要的目录
print_info "步骤 9: 创建必要的目录..."
mkdir -p logs uploads automation_results/scripts automation_results/reports automation_results/screenshots/debug
chmod -R 777 logs uploads automation_results

# 步骤 10: 配置 Gunicorn
print_info "步骤 10: 配置 Gunicorn..."
# 只在文件不存在时复制（避免同文件复制错误）
if [ ! -f "${PROJECT_DIR}/gunicorn_config.py" ]; then
    cp gunicorn_config.py ${PROJECT_DIR}/gunicorn_config.py
    print_info "已复制 gunicorn_config.py"
else
    print_info "gunicorn_config.py 已存在"
fi

# 创建必要的目录结构（包括日志目录）
mkdir -p /opt/stardragon/logs
mkdir -p /opt/stardragon/uploads
mkdir -p /opt/stardragon/automation_results

# 步骤 11: 配置 Systemd 服务
print_info "步骤 11: 配置 Systemd 服务..."
cp stardragon.service /etc/systemd/system/stardragon.service
systemctl daemon-reload
systemctl enable stardragon

# 步骤 12: 配置 Nginx
print_info "步骤 12: 配置 Nginx..."
cp nginx_stardragon.conf /etc/nginx/conf.d/stardragon.conf

# 删除默认配置（如果存在）
rm -f /etc/nginx/conf.d/default.conf

# 测试 Nginx 配置
nginx -t

# 步骤 13: 配置防火墙
print_info "步骤 13: 配置防火墙..."
if command -v firewall-cmd &> /dev/null; then
    # CentOS/RHEL
    firewall-cmd --permanent --add-service=http
    firewall-cmd --permanent --add-service=https
    firewall-cmd --reload
elif command -v ufw &> /dev/null; then
    # Ubuntu
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw reload
fi

# 步骤 14: 启动服务
print_info "步骤 14: 启动服务..."
systemctl restart nginx
systemctl restart stardragon

# 等待服务启动
sleep 3

# 步骤 15: 验证部署
print_info "步骤 15: 验证部署..."
if systemctl is-active --quiet stardragon; then
    print_info "✓ Gunicorn 服务运行正常"
else
    print_error "✗ Gunicorn 服务启动失败"
    print_info "查看日志: journalctl -u stardragon -f"
fi

if systemctl is-active --quiet nginx; then
    print_info "✓ Nginx 服务运行正常"
else
    print_error "✗ Nginx 服务启动失败"
fi

if docker ps | grep -q mysql; then
    print_info "✓ MySQL 容器运行正常"
else
    print_error "✗ MySQL 容器未运行"
fi

# 完成
echo ""
echo "========================================="
print_info "部署完成！"
echo "========================================="
echo ""
echo "访问地址: http://106.12.23.83"
echo ""
echo "管理命令:"
echo "  查看状态: systemctl status stardragon"
echo "  重启服务: systemctl restart stardragon"
echo "  查看日志: journalctl -u stardragon -f"
echo "  Nginx日志: tail -f /var/log/nginx/stardragon_error.log"
echo ""
echo "注意事项:"
echo "  1. 首次访问前，请创建超级用户:"
echo "     cd ${PROJECT_DIR} && source venv/bin/activate"
echo "     python manage.py createsuperuser"
echo "  2. 在生产环境中，请修改 SECRET_KEY"
echo "  3. 建议配置 HTTPS（使用 Let's Encrypt）"
echo ""
