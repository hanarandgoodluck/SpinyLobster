#!/bin/bash

#############################################
# StarDragon 域名和HTTPS配置脚本
# 域名: www.stardragon.top
#############################################

set -e

echo "========================================="
echo "StarDragon 域名和HTTPS配置"
echo "========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

DOMAIN="www.stardragon.top"
DOMAIN_NO_WWW="stardragon.top"
EMAIL="admin@stardragon.top"  # 请修改为你的邮箱

# 步骤 1: DNS解析提示
print_info "步骤 1: DNS解析配置"
echo ""
print_warning "请在阿里云DNS控制台添加以下解析记录："
echo "  记录类型: A"
echo "  主机记录: @"
echo "  记录值: 106.12.23.83"
echo ""
echo "  记录类型: A"
echo "  主机记录: www"
echo "  记录值: 106.12.23.83"
echo ""
read -p "按回车键继续（确保已配置DNS解析）..."

# 步骤 2: 安装 Certbot
print_info "步骤 2: 安装 Certbot（Let's Encrypt 客户端）..."
if command -v yum &> /dev/null; then
    # CentOS/RHEL
    yum install -y epel-release
    yum install -y certbot python3-certbot-nginx
elif command -v apt &> /dev/null; then
    # Ubuntu/Debian
    apt update
    apt install -y certbot python3-certbot-nginx
else
    print_error "不支持的操作系统"
    exit 1
fi

# 步骤 3: 创建临时SSL目录和自签名证书
print_info "步骤 3: 创建临时SSL证书..."
mkdir -p /etc/nginx/ssl
mkdir -p /var/www/certbot

# 生成自签名证书（仅用于测试，正式环境会使用 Let's Encrypt）
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/stardragon.top.key \
    -out /etc/nginx/ssl/stardragon.top.crt \
    -subj "/C=CN/ST=Beijing/L=Beijing/O=StarDragon/CN=$DOMAIN"

print_info "临时证书已创建（浏览器会显示警告，这是正常的）"

# 步骤 4: 更新 Nginx 配置
print_info "步骤 4: 配置 Nginx..."
cp nginx_stardragon.conf /etc/nginx/conf.d/stardragon.conf

# 测试 Nginx 配置
nginx -t
if [ $? -eq 0 ]; then
    print_info "✓ Nginx 配置测试通过"
else
    print_error "✗ Nginx 配置测试失败"
    exit 1
fi

# 重启 Nginx
systemctl restart nginx
print_info "✓ Nginx 已重启"

# 步骤 5: 配置防火墙
print_info "步骤 5: 配置防火墙..."
if command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-service=https
    firewall-cmd --reload
    print_info "✓ 防火墙已配置 HTTPS (443)"
elif command -v ufw &> /dev/null; then
    ufw allow 443/tcp
    ufw reload
    print_info "✓ 防火墙已配置 HTTPS (443)"
fi

# 步骤 6: 申请 Let's Encrypt 正式证书
print_info "步骤 6: 申请 Let's Encrypt SSL 证书..."
echo ""
print_warning "注意：确保证书已正确解析到 106.12.23.83"
read -p "是否现在申请正式证书？(y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 停止 Nginx（certbot standalone 模式需要）
    systemctl stop nginx
    
    # 申请证书
    certbot certonly --standalone \
        -d $DOMAIN \
        -d $DOMAIN_NO_WWW \
        --email $EMAIL \
        --agree-tos \
        --no-eff-email \
        --force-renewal
    
    if [ $? -eq 0 ]; then
        print_info "✓ SSL 证书申请成功"
        
        # 更新 Nginx 配置使用正式证书
        sed -i "s|ssl_certificate /etc/nginx/ssl/stardragon.top.crt;|ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;|" /etc/nginx/conf.d/stardragon.conf
        sed -i "s|ssl_certificate_key /etc/nginx/ssl/stardragon.top.key;|ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;|" /etc/nginx/conf.d/stardragon.conf
        
        # 重启 Nginx
        systemctl start nginx
        print_info "✓ Nginx 已使用正式证书重启"
        
        # 配置自动续期
        print_info "配置证书自动续期..."
        (crontab -l 2>/dev/null; echo "0 3 * * 1 /usr/bin/certbot renew --quiet && systemctl reload nginx") | crontab -
        print_info "✓ 证书将在每周一凌晨3点自动续期"
    else
        print_error "✗ SSL 证书申请失败"
        print_warning "继续使用临时自签名证书"
        
        # 重新启动 Nginx
        systemctl start nginx
    fi
else
    print_warning "跳过正式证书申请，使用临时自签名证书"
    print_info "稍后可以运行: certbot --nginx -d $DOMAIN -d $DOMAIN_NO_WWW"
fi

# 完成
echo ""
echo "========================================="
print_info "配置完成！"
echo "========================================="
echo ""
echo "访问地址:"
echo "  HTTP:  http://$DOMAIN (自动跳转到 HTTPS)"
echo "  HTTPS: https://$DOMAIN"
echo ""
echo "注意事项:"
echo "  1. 如果使用临时证书，浏览器会显示安全警告（点击高级-继续访问即可）"
echo "  2. 申请正式证书后，警告将消失"
echo "  3. 确保证书已在阿里云DNS控制台正确解析"
echo "  4. 查看日志: tail -f /var/log/nginx/stardragon_error.log"
echo ""
