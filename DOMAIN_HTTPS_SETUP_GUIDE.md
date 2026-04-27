# StarDragon 域名和HTTPS配置指南

## ✅ 已完成的配置

### 1. Nginx配置
- ✅ HTTP自动跳转到HTTPS
- ✅ 支持 `stardragon.top` 和 `www.stardragon.top`
- ✅ SSL证书配置（临时自签名证书）
- ✅ HTTP/2 支持
- ✅ SSL优化配置

### 2. 防火墙
- ✅ 开放443端口（HTTPS）
- ✅ 开放80端口（HTTP）

### 3. 服务状态
- ✅ Gunicorn运行正常
- ✅ Nginx运行正常
- ✅ MySQL运行正常

---

## 📋 下一步操作清单

### ⚠️ 重要：必须完成以下步骤才能访问

### 步骤1: 阿里云DNS解析配置（必须）

登录阿里云控制台，配置DNS解析：

1. 进入 **阿里云DNS控制台**
2. 找到 `stardragon.top` 域名
3. 添加以下两条解析记录：

#### 记录1: @ (根域名)
```
记录类型: A
主机记录: @
记录值: 106.12.23.83
TTL: 10分钟（默认）
```

#### 记录2: www
```
记录类型: A
主机记录: www
记录值: 106.12.23.83
TTL: 10分钟（默认）
```

**等待DNS生效**：通常需要5-10分钟，最长可能需要24小时

---

### 步骤2: 阿里云安全组配置（必须）

在阿里云ECS控制台配置安全组规则：

1. 进入 **ECS实例控制台**
2. 找到你的实例 → **安全组** → **配置规则**
3. 添加入方向规则：

#### 规则1: HTTPS
```
优先级: 1
策略: 允许
协议类型: TCP
端口范围: 443/443
授权对象: 0.0.0.0/0
描述: HTTPS访问
```

#### 规则2: HTTP
```
优先级: 2
策略: 允许
协议类型: TCP
端口范围: 80/80
授权对象: 0.0.0.0/0
描述: HTTP访问（用于跳转到HTTPS）
```

---

### 步骤3: 测试访问

DNS和安全组配置完成后，等待5-10分钟，然后访问：

- **HTTP**: http://www.stardragon.top （会自动跳转到HTTPS）
- **HTTPS**: https://www.stardragon.top

⚠️ **注意**：由于使用的是临时自签名证书，浏览器会显示"您的连接不是私密连接"警告。

**解决方法**：
- Chrome: 点击"高级" → "继续前往www.stardragon.top（不安全）"
- Firefox: 点击"高级" → "接受风险并继续"
- Edge: 点击"详细信息" → "继续转到网页"

---

### 步骤4: 申请正式SSL证书（推荐）

要消除浏览器警告，需要申请Let's Encrypt免费证书。

#### 方法1: 使用Certbot自动申请（推荐）

在服务器上执行：

```bash
ssh root@106.12.23.83

# 安装Certbot
apt update
apt install -y certbot python3-certbot-nginx

# 停止Nginx
systemctl stop nginx

# 申请证书
certbot certonly --standalone \
    -d stardragon.top \
    -d www.stardragon.top \
    --email admin@stardragon.top \
    --agree-tos \
    --no-eff-email

# 启动Nginx
systemctl start nginx

# 更新Nginx配置使用正式证书
# 编辑 /etc/nginx/conf.d/stardragon.conf
# 将以下两行：
#   ssl_certificate /etc/nginx/ssl/stardragon.top.crt;
#   ssl_certificate_key /etc/nginx/ssl/stardragon.top.key;
# 修改为：
#   ssl_certificate /etc/letsencrypt/live/www.stardragon.top/fullchain.pem;
#   ssl_certificate_key /etc/letsencrypt/live/www.stardragon.top/privkey.pem;

# 重启Nginx
systemctl restart nginx
```

#### 方法2: 使用阿里云免费SSL证书

1. 进入 **阿里云SSL证书控制台**
2. 申请免费证书（DV单域名）
3. 验证域名所有权
4. 下载证书（选择Nginx格式）
5. 上传到服务器 `/etc/nginx/ssl/` 目录
6. 更新Nginx配置指向新证书
7. 重启Nginx

---

### 步骤5: 配置证书自动续期（如果使用Let's Encrypt）

Let's Encrypt证书有效期90天，需要自动续期：

```bash
# 编辑crontab
crontab -e

# 添加以下行（每周一凌晨3点自动续期）
0 3 * * 1 /usr/bin/certbot renew --quiet && systemctl reload nginx
```

---

## 🔧 常用管理命令

### 查看服务状态
```bash
systemctl status nginx
systemctl status stardragon
docker ps | grep mysql
```

### 查看日志
```bash
# Nginx访问日志
tail -f /var/log/nginx/stardragon_access.log

# Nginx错误日志
tail -f /var/log/nginx/stardragon_error.log

# Gunicorn日志
journalctl -u stardragon -f
```

### 重启服务
```bash
systemctl restart nginx
systemctl restart stardragon
```

### 测试Nginx配置
```bash
nginx -t
```

---

## ❓ 常见问题

### Q1: 访问显示"无法访问此网站"
**原因**: DNS未生效或安全组未配置
**解决**: 
1. 检查DNS解析: `ping www.stardragon.top`
2. 检查安全组规则是否开放80和443端口

### Q2: 浏览器显示安全警告
**原因**: 使用临时自签名证书
**解决**: 按照步骤4申请正式SSL证书

### Q3: HTTP不跳转到HTTPS
**原因**: Nginx配置问题
**解决**: 
```bash
nginx -t  # 检查配置
systemctl restart nginx  # 重启Nginx
```

### Q4: 如何强制所有访问都使用www
**解决**: 当前配置已实现，http://stardragon.top 会自动跳转到 https://www.stardragon.top

---

## 📞 技术支持

如遇到问题，请检查：
1. DNS解析是否正确: `nslookup www.stardragon.top`
2. 端口是否开放: `telnet 106.12.23.83 443`
3. 服务是否运行: `systemctl status nginx stardragon`
4. 日志是否有错误: `tail -100 /var/log/nginx/stardragon_error.log`

---

## ✨ 配置完成后的访问地址

- **主站**: https://www.stardragon.top
- **HTTP自动跳转**: http://www.stardragon.top → https://www.stardragon.top
- **根域名跳转**: http://stardragon.top → https://www.stardragon.top
