# StarDragon 项目部署指南

## 服务器信息
- **公网地址**: 106.12.23.83
- **数据库**: Docker MySQL
- **数据库用户**: root
- **数据库密码**: 583471755a

---

## 一、服务器环境准备

### 1. 连接到服务器
```bash
ssh root@106.12.23.83
```

### 2. 安装基础依赖
```bash
# 更新系统
yum update -y  # CentOS/RHEL
# 或
apt update && apt upgrade -y  # Ubuntu/Debian

# 安装必要工具
yum install -y git python3 python3-pip python3-devel mysql-devel gcc nginx  # CentOS
# 或
apt install -y git python3 python3-pip python3-dev default-libmysqlclient-dev build-essential nginx  # Ubuntu
```

### 3. 安装 Python 虚拟环境工具
```bash
pip3 install virtualenv
```

---

## 二、MySQL 数据库配置

### 1. 检查 Docker MySQL 是否运行
```bash
docker ps | grep mysql
```

### 2. 如果未安装，安装 MySQL Docker 容器
```bash
docker run -d \
  --name mysql \
  -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=583471755a \
  -e MYSQL_DATABASE=test_brain_db \
  -v /data/mysql:/var/lib/mysql \
  --restart=always \
  mysql:8.0
```

### 3. 创建数据库（如果不存在）
```bash
docker exec -it mysql mysql -uroot -p583471755a -e "CREATE DATABASE IF NOT EXISTS test_brain_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

---

## 三、项目部署

### 1. 上传项目代码到服务器
```bash
# 方法1: 使用 git（推荐）
cd /opt
git clone <your-repository-url> stardragon
cd stardragon

# 方法2: 使用 scp 从本地上传
# 在本地执行：
scp -r F:\test\TestBranin root@106.12.23.83:/opt/stardragon
```

### 2. 创建 Python 虚拟环境
```bash
cd /opt/stardragon
python3 -m virtualenv venv
source venv/bin/activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 配置 Django 设置

编辑 `config/settings.py`，修改以下配置：

```python
# 修改 ALLOWED_HOSTS
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    '106.12.23.83',  # 添加服务器公网IP
]

# 修改数据库配置
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'test_brain_db',
        'USER': 'root',
        'PASSWORD': '583471755a',  # Docker MySQL 密码
        'HOST': '127.0.0.1',  # Docker MySQL 在本机
        'PORT': '3306',
    }
}

# 生产环境关闭 DEBUG
DEBUG = False

# 修改 SECRET_KEY（生成一个安全的密钥）
SECRET_KEY = 'your-production-secret-key-here'
```

### 5. 初始化数据库
```bash
cd /opt/stardragon
source venv/bin/activate

# 执行数据库迁移
python manage.py makemigrations
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser
```

### 6. 收集静态文件
```bash
python manage.py collectstatic --noinput
```

---

## 四、配置 Nginx

### 1. 创建 Nginx 配置文件
```bash
sudo vi /etc/nginx/conf.d/stardragon.conf
```

添加以下内容：

```nginx
server {
    listen 80;
    server_name 106.12.23.83;

    # 静态文件
    location /static/ {
        alias /opt/stardragon/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 媒体文件
    location /uploads/ {
        alias /opt/stardragon/uploads/;
        expires 30d;
    }

    # Django 应用
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # WebSocket 支持（如果需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 日志
    access_log /var/log/nginx/stardragon_access.log;
    error_log /var/log/nginx/stardragon_error.log;
}
```

### 2. 测试并重启 Nginx
```bash
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
```

---

## 五、配置 Gunicorn（生产环境 WSGI 服务器）

### 1. 安装 Gunicorn
```bash
source /opt/stardragon/venv/bin/activate
pip install gunicorn
```

### 2. 创建 Gunicorn 配置文件
```bash
vi /opt/stardragon/gunicorn_config.py
```

添加以下内容：

```python
import multiprocessing

# 绑定地址
bind = "127.0.0.1:8000"

# Worker 数量
workers = multiprocessing.cpu_count() * 2 + 1

# Worker 类型
worker_class = "sync"

# 超时时间
timeout = 120

# 最大请求数
max_requests = 1000
max_requests_jitter = 50

# 日志
accesslog = "/var/log/gunicorn/stardragon_access.log"
errorlog = "/var/log/gunicorn/stardragon_error.log"
loglevel = "info"

# 进程命名
proc_name = "stardragon"

# 工作目录
chdir = "/opt/stardragon"
```

### 3. 创建日志目录
```bash
sudo mkdir -p /var/log/gunicorn
sudo chown $(whoami):$(whoami) /var/log/gunicorn
```

### 4. 创建 Systemd 服务文件
```bash
sudo vi /etc/systemd/system/stardragon.service
```

添加以下内容：

```ini
[Unit]
Description=StarDragon Django Application
After=network.target mysql.service

[Service]
User=root
Group=root
WorkingDirectory=/opt/stardragon
Environment="PATH=/opt/stardragon/venv/bin"
ExecStart=/opt/stardragon/venv/bin/gunicorn --config gunicorn_config.py config.wsgi:application

Restart=on-failure
RestartSec=5s

# 日志
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 5. 启动服务
```bash
sudo systemctl daemon-reload
sudo systemctl start stardragon
sudo systemctl enable stardragon

# 检查状态
sudo systemctl status stardragon
```

---

## 六、防火墙配置

### 1. 开放端口
```bash
# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload

# Ubuntu (ufw)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw reload
```

---

## 七、验证部署

### 1. 检查服务状态
```bash
# 检查 Gunicorn
sudo systemctl status stardragon

# 检查 Nginx
sudo systemctl status nginx

# 检查 MySQL
docker ps | grep mysql
```

### 2. 访问应用
在浏览器中访问：`http://106.12.23.83`

### 3. 查看日志
```bash
# Gunicorn 日志
tail -f /var/log/gunicorn/stardragon_error.log
tail -f /var/log/gunicorn/stardragon_access.log

# Nginx 日志
tail -f /var/log/nginx/stardragon_error.log
tail -f /var/log/nginx/stardragon_access.log

# Django 日志
tail -f /opt/stardragon/logs/all.log
```

---

## 八、可选：配置 HTTPS（推荐）

### 1. 安装 Certbot
```bash
# CentOS
sudo yum install -y certbot python3-certbot-nginx

# Ubuntu
sudo apt install -y certbot python3-certbot-nginx
```

### 2. 获取 SSL 证书
```bash
sudo certbot --nginx -d 106.12.23.83
```

### 3. 自动续期
```bash
sudo crontab -e
# 添加以下行
0 0 1 * * certbot renew --quiet
```

---

## 九、常见问题排查

### 1. 数据库连接失败
```bash
# 检查 MySQL 是否运行
docker ps | grep mysql

# 测试数据库连接
docker exec -it mysql mysql -uroot -p583471755a -e "SHOW DATABASES;"

# 检查防火墙
telnet 127.0.0.1 3306
```

### 2. 静态文件 404
```bash
# 重新收集静态文件
source /opt/stardragon/venv/bin/activate
python manage.py collectstatic --noinput

# 检查 Nginx 配置
sudo nginx -t
sudo systemctl restart nginx
```

### 3. 权限问题
```bash
# 确保目录权限正确
sudo chown -R root:root /opt/stardragon
sudo chmod -R 755 /opt/stardragon
sudo chmod -R 777 /opt/stardragon/logs
sudo chmod -R 777 /opt/stardragon/uploads
```

### 4. 内存不足
```bash
# 检查内存使用
free -h

# 调整 Gunicorn worker 数量
vi /opt/stardragon/gunicorn_config.py
# 减少 workers 数量
```

---

## 十、维护和监控

### 1. 常用管理命令
```bash
# 重启应用
sudo systemctl restart stardragon

# 停止应用
sudo systemctl stop stardragon

# 查看日志
sudo journalctl -u stardragon -f

# 更新代码
cd /opt/stardragon
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart stardragon
```

### 2. 备份数据库
```bash
# 备份
docker exec mysql mysqldump -uroot -p583471755a test_brain_db > /backup/test_brain_db_$(date +%Y%m%d).sql

# 恢复
docker exec -i mysql mysql -uroot -p583471755a test_brain_db < /backup/test_brain_db_20260424.sql
```

---

## 快速部署脚本

创建一个自动化部署脚本 `deploy.sh`：

```bash
#!/bin/bash

echo "=== StarDragon 部署脚本 ==="

# 1. 进入项目目录
cd /opt/stardragon

# 2. 激活虚拟环境
source venv/bin/activate

# 3. 拉取最新代码
git pull

# 4. 安装依赖
pip install -r requirements.txt

# 5. 数据库迁移
python manage.py migrate

# 6. 收集静态文件
python manage.py collectstatic --noinput

# 7. 重启服务
sudo systemctl restart stardragon

echo "=== 部署完成 ==="
```

使用方法：
```bash
chmod +x deploy.sh
./deploy.sh
```

---

## 联系与支持

如有问题，请检查：
1. 日志文件：`/var/log/gunicorn/` 和 `/var/log/nginx/`
2. Django 日志：`/opt/stardragon/logs/`
3. 系统日志：`sudo journalctl -u stardragon`
