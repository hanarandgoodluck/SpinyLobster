# StarDragon 项目部署方案总结

## 📦 已生成的部署文件

我已经为你的 StarDragon 项目创建了完整的部署方案，包含以下文件：

### 1. 核心部署文档
- **QUICK_START.md** - 5分钟快速开始指南（推荐先看这个）
- **DEPLOYMENT.md** - 详细部署文档（完整步骤和说明）
- **DEPLOYMENT_CHECKLIST.md** - 部署检查清单和故障排查指南

### 2. 自动化脚本和配置
- **deploy.sh** - 一键自动化部署脚本
- **gunicorn_config.py** - Gunicorn WSGI 服务器配置
- **stardragon.service** - Systemd 服务配置文件
- **nginx_stardragon.conf** - Nginx 反向代理配置

### 3. Django 配置
- **config/settings_production.py** - 生产环境专用配置
- **.env.example** - 环境变量配置示例

### 4. 其他
- **.gitignore** - Git 忽略文件配置

---

## 🎯 部署架构

```
用户浏览器
    ↓
Nginx (80端口) ← nginx_stardragon.conf
    ↓ 反向代理
Gunicorn (8000端口) ← gunicorn_config.py + stardragon.service
    ↓ WSGI
Django 应用 ← config/settings_production.py
    ↓
MySQL Docker容器 (3306端口)
```

---

## 🚀 快速部署步骤

### 方式一：自动化部署（推荐）

```bash
# 1. 在本地 PowerShell 上传代码
scp -r F:\test\TestBranin\* root@106.12.23.83:/opt/stardragon/

# 2. SSH 连接服务器
ssh root@106.12.23.83

# 3. 运行自动化部署脚本
cd /opt/stardragon
chmod +x deploy.sh
./deploy.sh

# 4. 创建超级用户
source venv/bin/activate
python manage.py createsuperuser

# 5. 访问 http://106.12.23.83
```

### 方式二：手动部署

参考 `DEPLOYMENT.md` 文档中的详细步骤。

---

## 🔑 关键配置信息

| 项目 | 值 |
|------|-----|
| 服务器IP | 106.12.23.83 |
| MySQL用户 | root |
| MySQL密码 | 583471755a |
| 数据库名 | test_brain_db |
| MySQL端口 | 3306 (Docker) |
| Gunicorn端口 | 8000 (本地) |
| Nginx端口 | 80 (公网) |
| 项目目录 | /opt/stardragon |
| Python虚拟环境 | /opt/stardragon/venv |

---

## 📋 部署前准备清单

- [ ] 确认服务器可以SSH访问（ssh root@106.12.23.83）
- [ ] 确认 Docker 已安装或允许脚本自动安装
- [ ] 准备好 DeepSeek API Key（用于AI功能）
- [ ] 备份本地数据（如果需要迁移）

---

## ✅ 部署后验证清单

- [ ] 访问 http://106.12.23.83 能看到首页
- [ ] systemctl status stardragon 显示 active
- [ ] systemctl status nginx 显示 active
- [ ] docker ps 显示 mysql 容器运行中
- [ ] 能够登录管理后台
- [ ] 静态文件正常加载
- [ ] AI 功能正常工作（配置API Key后）

---

## 🔧 常用管理命令

```bash
# 服务管理
systemctl restart stardragon    # 重启应用
systemctl restart nginx         # 重启Nginx
systemctl status stardragon     # 查看状态

# 日志查看
journalctl -u stardragon -f     # Gunicorn日志
tail -f /var/log/nginx/stardragon_error.log  # Nginx错误日志
tail -f /opt/stardragon/logs/all.log         # Django日志

# 数据库操作
docker exec -it mysql mysql -uroot -p583471755a  # 进入MySQL
docker exec mysql mysqldump -uroot -p583471755a test_brain_db > backup.sql  # 备份

# Django管理
cd /opt/stardragon && source venv/bin/activate
python manage.py createsuperuser   # 创建管理员
python manage.py migrate           # 数据库迁移
python manage.py collectstatic     # 收集静态文件
```

---

## 🔒 安全建议

1. **修改默认密码**
   - 生成新的 SECRET_KEY
   - 使用强密码创建超级用户

2. **配置 HTTPS**（强烈推荐）
   ```bash
   yum install -y certbot python3-certbot-nginx
   certbot --nginx -d your-domain.com
   ```

3. **配置防火墙**
   ```bash
   firewall-cmd --permanent --add-service=http
   firewall-cmd --permanent --add-service=https
   firewall-cmd --reload
   ```

4. **定期备份**
   - 设置定时任务备份数据库
   - 备份 uploads 目录

5. **保护 API Keys**
   - 不要硬编码在代码中
   - 使用环境变量或数据库配置

---

## 🐛 常见问题

### 1. 无法访问网站
- 检查防火墙是否开放80端口
- 检查 Nginx 和 Gunicorn 是否运行
- 查看错误日志定位问题

### 2. 数据库连接失败
- 确认 MySQL Docker 容器运行
- 检查数据库配置是否正确
- 测试数据库连接

### 3. 静态文件404
- 运行 `python manage.py collectstatic`
- 检查 Nginx 配置中的路径
- 确认目录权限正确

### 4. AI功能不工作
- 检查 API Key 是否正确配置
- 查看 logs/llm.log 和 logs/all.log
- 确认网络连接正常

详细故障排查请参考 `DEPLOYMENT_CHECKLIST.md`

---

## 📊 性能优化建议

1. **调整 Gunicorn Workers**
   - 根据服务器CPU核心数调整
   - 公式：workers = CPU核心数 * 2 + 1

2. **启用 Nginx Gzip压缩**
   - 减少传输数据量
   - 提高页面加载速度

3. **配置 Redis 缓存**（可选）
   - 缓存频繁访问的数据
   - 提高响应速度

4. **数据库优化**
   - 定期优化表
   - 添加合适的索引

---

## 🔄 更新部署流程

当代码有更新时：

```bash
cd /opt/stardragon
git pull                              # 拉取最新代码
source venv/bin/activate              # 激活虚拟环境
pip install -r requirements.txt       # 更新依赖
python manage.py migrate              # 数据库迁移
python manage.py collectstatic        # 收集静态文件
systemctl restart stardragon          # 重启服务
```

或者直接重新运行：
```bash
./deploy.sh
```

---

## 📞 获取帮助

- 📖 快速开始：阅读 `QUICK_START.md`
- 📖 详细文档：阅读 `DEPLOYMENT.md`
- 📖 问题排查：阅读 `DEPLOYMENT_CHECKLIST.md`
- 📝 查看日志：使用上述日志命令
- 🔍 检查状态：使用 systemctl 命令

---

## 🎉 部署完成后的下一步

1. 配置 AI 模型 API Key
2. 创建测试项目
3. 测试各项功能
4. 配置定期备份
5. 设置监控告警（可选）
6. 配置 HTTPS（如果有域名）

---

**祝部署顺利！如有问题，请查看详细文档或检查日志。** 🚀

---

*文档生成时间: 2026-04-24*
*项目名称: StarDragon (原 SpinyLobster)*
*目标服务器: 106.12.23.83*
