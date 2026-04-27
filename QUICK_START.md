# StarDragon 部署快速开始

## 🎯 5分钟快速部署

### 步骤 1: 上传代码到服务器

在本地 PowerShell 执行：
```powershell
# 压缩项目文件
Compress-Archive -Path F:\test\TestBranin\* -DestinationPath F:\test\stardragon.zip

# 上传到服务器
scp F:\test\stardragon.zip root@106.12.23.83:/opt/

# SSH 连接
ssh root@106.12.23.83
```

### 步骤 2: 在服务器上解压和部署

```bash
# 解压
cd /opt
unzip stardragon.zip -d stardragon
cd stardragon

# 运行自动化部署脚本
chmod +x deploy.sh
./deploy.sh
```

### 步骤 3: 创建管理员账户

```bash
source venv/bin/activate
python manage.py createsuperuser
# 按提示输入用户名、邮箱、密码
```

### 步骤 4: 配置 AI API Key

访问 http://106.12.23.83/admin，在 "AI 配置管理" 中配置 DeepSeek API Key。

### 步骤 5: 验证部署

浏览器访问：http://106.12.23.83

---

## 📁 已创建的部署文件说明

| 文件 | 用途 |
|------|------|
| `DEPLOYMENT.md` | 详细部署文档（完整步骤） |
| `DEPLOYMENT_CHECKLIST.md` | 部署检查清单和故障排查 |
| `deploy.sh` | 自动化部署脚本 |
| `gunicorn_config.py` | Gunicorn WSGI 服务器配置 |
| `stardragon.service` | Systemd 服务配置文件 |
| `nginx_stardragon.conf` | Nginx 反向代理配置 |
| `config/settings_production.py` | 生产环境 Django 配置 |
| `.env.example` | 环境变量配置示例 |

---

## 🔑 关键信息

- **服务器地址**: 106.12.23.83
- **数据库**: Docker MySQL (root / 583471755a)
- **数据库名**: test_brain_db
- **访问地址**: http://106.12.23.83
- **管理后台**: http://106.12.23.83/admin

---

## ⚡ 常用命令速查

```bash
# 查看服务状态
systemctl status stardragon
systemctl status nginx
docker ps | grep mysql

# 重启服务
systemctl restart stardragon
systemctl restart nginx

# 查看日志
journalctl -u stardragon -f
tail -f /var/log/nginx/stardragon_error.log
tail -f /opt/stardragon/logs/all.log

# 进入 Python 环境
cd /opt/stardragon
source venv/bin/activate

# 数据库操作
docker exec -it mysql mysql -uroot -p583471755a
```

---

## ❓ 遇到问题？

1. 查看详细文档：`DEPLOYMENT.md`
2. 查看检查清单：`DEPLOYMENT_CHECKLIST.md`
3. 查看日志定位问题
4. 确保防火墙开放了 80 端口

---

**祝部署顺利！** 🚀
