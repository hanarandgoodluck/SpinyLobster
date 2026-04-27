# StarDragon 快速部署检查清单

## 📋 部署前准备

### 本地准备
- [ ] 确认项目代码已提交到 Git 或准备好上传
- [ ] 备份本地数据库（如果需要迁移数据）
- [ ] 记录所有需要配置的 API Key（DeepSeek、通义千问等）

### 服务器信息
- **IP地址**: 106.12.23.83
- **SSH用户**: root
- **MySQL密码**: 583471755a
- **数据库名**: test_brain_db

---

## 🚀 快速部署步骤（推荐自动化脚本）

### 方法一：使用自动化部署脚本（推荐）

```bash
# 1. SSH 连接到服务器
ssh root@106.12.23.83

# 2. 上传项目文件（在本地 PowerShell 执行）
scp -r F:\test\TestBranin\* root@106.12.23.83:/opt/stardragon/

# 3. 在服务器上运行部署脚本
cd /opt/stardragon
chmod +x deploy.sh
./deploy.sh

# 4. 创建超级用户
source venv/bin/activate
python manage.py createsuperuser

# 5. 配置 AI API Key（通过管理后台或环境变量）
```

### 方法二：手动部署

按照 `DEPLOYMENT.md` 中的详细步骤执行。

---

## ✅ 部署后验证清单

### 服务状态检查
```bash
# 检查 Gunicorn
systemctl status stardragon

# 检查 Nginx
systemctl status nginx

# 检查 MySQL
docker ps | grep mysql

# 查看日志
tail -f /var/log/gunicorn/stardragon_error.log
tail -f /var/log/nginx/stardragon_error.log
```

### 功能测试
- [ ] 访问 http://106.12.23.83 能看到首页
- [ ] 能够登录管理后台
- [ ] 静态文件正常加载（CSS、JS）
- [ ] 能够上传文件
- [ ] 数据库读写正常
- [ ] AI 功能正常工作（需要配置 API Key）

---

## 🔧 必要配置项

### 1. 创建超级用户
```bash
cd /opt/stardragon
source venv/bin/activate
python manage.py createsuperuser
```

### 2. 配置 AI API Key
**方式一：通过管理后台（推荐）**
1. 访问 http://106.12.23.83/admin
2. 进入 "AI 配置管理"
3. 配置 DeepSeek 或其他模型的 API Key

**方式二：通过环境变量**
```bash
# 编辑 systemd 服务文件
vi /etc/systemd/system/stardragon.service

# 添加环境变量
Environment="DEEPSEEK_API_KEY=your-api-key-here"

# 重启服务
systemctl daemon-reload
systemctl restart stardragon
```

### 3. 生成安全的 SECRET_KEY
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

将生成的密钥更新到 `config/settings_production.py` 或通过环境变量设置：
```bash
Environment="DJANGO_SECRET_KEY=generated-key-here"
```

---

## 📝 常用管理命令

### 服务管理
```bash
# 重启应用
systemctl restart stardragon

# 停止应用
systemctl stop stardragon

# 查看状态
systemctl status stardragon

# 查看日志
journalctl -u stardragon -f
```

### Nginx 管理
```bash
# 重启 Nginx
systemctl restart nginx

# 测试配置
nginx -t

# 查看日志
tail -f /var/log/nginx/stardragon_access.log
tail -f /var/log/nginx/stardragon_error.log
```

### 数据库管理
```bash
# 进入 MySQL
docker exec -it mysql mysql -uroot -p583471755a

# 备份数据库
docker exec mysql mysqldump -uroot -p583471755a test_brain_db > backup_$(date +%Y%m%d).sql

# 恢复数据库
docker exec -i mysql mysql -uroot -p583471755a test_brain_db < backup_20260424.sql
```

### Django 管理
```bash
cd /opt/stardragon
source venv/bin/activate

# 数据库迁移
python manage.py migrate

# 收集静态文件
python manage.py collectstatic --noinput

# 创建超级用户
python manage.py createsuperuser

# 查看 Django 日志
tail -f logs/all.log
```

---

## 🔒 安全加固建议

### 1. 配置防火墙
```bash
# 只开放必要端口
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --permanent --remove-service=ssh  # 谨慎操作，确保有其他访问方式
firewall-cmd --reload
```

### 2. 配置 HTTPS（强烈推荐）
```bash
# 安装 Certbot
yum install -y certbot python3-certbot-nginx  # CentOS
# 或
apt install -y certbot python3-certbot-nginx  # Ubuntu

# 获取证书（如果有域名）
certbot --nginx -d your-domain.com

# 自动续期
crontab -e
# 添加: 0 0 1 * * certbot renew --quiet
```

### 3. 修改默认密码
- [ ] 修改 MySQL root 密码
- [ ] 使用强密码创建 Django 超级用户
- [ ] 更改 SECRET_KEY

### 4. 定期备份
```bash
# 创建备份脚本
cat > /opt/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 备份数据库
docker exec mysql mysqldump -uroot -p583471755a test_brain_db > $BACKUP_DIR/db_$DATE.sql

# 备份 uploads 目录
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz /opt/stardragon/uploads/

# 删除7天前的备份
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x /opt/backup.sh

# 添加到 crontab（每天凌晨2点备份）
crontab -e
# 添加: 0 2 * * * /opt/backup.sh >> /var/log/backup.log 2>&1
```

---

## 🐛 故障排查

### 问题1: 无法访问网站
```bash
# 检查服务状态
systemctl status stardragon
systemctl status nginx

# 检查端口监听
netstat -tlnp | grep 80
netstat -tlnp | grep 8000

# 检查防火墙
firewall-cmd --list-all
```

### 问题2: 数据库连接失败
```bash
# 检查 MySQL 容器
docker ps | grep mysql

# 测试连接
docker exec -it mysql mysql -uroot -p583471755a -e "SHOW DATABASES;"

# 检查 Django 数据库配置
grep -A 10 "DATABASES" /opt/stardragon/config/settings.py
```

### 问题3: 静态文件 404
```bash
# 重新收集静态文件
cd /opt/stardragon
source venv/bin/activate
python manage.py collectstatic --noinput

# 检查 Nginx 配置
grep -A 5 "location /static" /etc/nginx/conf.d/stardragon.conf

# 检查目录权限
ls -la /opt/stardragon/staticfiles/
```

### 问题4: 内存不足
```bash
# 检查内存使用
free -h
top

# 减少 Gunicorn worker 数量
vi /opt/stardragon/gunicorn_config.py
# 修改: workers = 2

# 重启服务
systemctl restart stardragon
```

### 问题5: AI 功能不工作
```bash
# 检查 API Key 配置
# 方式1: 通过管理后台检查
# 方式2: 检查环境变量
systemctl show stardragon | grep Environment

# 检查日志
tail -f /opt/stardragon/logs/llm.log
tail -f /opt/stardragon/logs/all.log
```

---

## 📊 性能优化建议

### 1. 启用 Gzip 压缩
在 Nginx 配置中添加：
```nginx
gzip on;
gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
```

### 2. 配置 Redis 缓存（可选）
```bash
# 安装 Redis
docker run -d --name redis -p 6379:6379 --restart=always redis:7

# 在 Django settings 中配置 CACHES
```

### 3. 优化数据库
```bash
# 定期优化表
docker exec -it mysql mysqlcheck -uroot -p583471755a --optimize --all-databases
```

---

## 🔄 更新部署

当代码有更新时：

```bash
# 方法一：使用更新脚本
cd /opt/stardragon
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
systemctl restart stardragon

# 方法二：重新运行部署脚本
./deploy.sh
```

---

## 📞 获取帮助

- 查看详细部署文档：`DEPLOYMENT.md`
- 查看应用日志：`journalctl -u stardragon -f`
- 查看 Nginx 日志：`tail -f /var/log/nginx/stardragon_error.log`
- 查看 Django 日志：`tail -f /opt/stardragon/logs/all.log`

---

**最后更新**: 2026-04-24
