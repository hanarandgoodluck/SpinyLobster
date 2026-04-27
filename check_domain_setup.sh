#!/bin/bash

echo "========================================="
echo "StarDragon 域名配置检查"
echo "========================================="
echo ""

DOMAIN="www.stardragon.top"
IP="106.12.23.83"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_ok() {
    echo -e "${GREEN}✓${NC} $1"
}

print_fail() {
    echo -e "${RED}✗${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

echo "1. 检查DNS解析..."
DNS_IP=$(ping -c 1 -W 2 $DOMAIN 2>/dev/null | grep -oP '\d+\.\d+\.\d+\.\d+' | head -1)
if [ "$DNS_IP" == "$IP" ]; then
    print_ok "DNS解析正确: $DOMAIN -> $DNS_IP"
else
    print_fail "DNS解析未配置或不正确"
    print_warn "请在阿里云DNS控制台添加A记录: $DOMAIN -> $IP"
fi
echo ""

echo "2. 检查Nginx配置..."
if nginx -t 2>&1 | grep -q "syntax is ok"; then
    print_ok "Nginx配置语法正确"
else
    print_fail "Nginx配置有错误"
fi
echo ""

echo "3. 检查服务状态..."
if systemctl is-active --quiet nginx; then
    print_ok "Nginx服务运行正常"
else
    print_fail "Nginx服务未运行"
fi

if systemctl is-active --quiet stardragon; then
    print_ok "Gunicorn服务运行正常"
else
    print_fail "Gunicorn服务未运行"
fi
echo ""

echo "4. 检查端口监听..."
if ss -tuln | grep -q ':80 '; then
    print_ok "80端口 (HTTP) 正在监听"
else
    print_fail "80端口未监听"
fi

if ss -tuln | grep -q ':443 '; then
    print_ok "443端口 (HTTPS) 正在监听"
else
    print_fail "443端口未监听"
fi
echo ""

echo "5. 检查SSL证书..."
if [ -f /etc/nginx/ssl/stardragon.top.crt ]; then
    print_ok "SSL证书文件存在（临时自签名证书）"
    openssl x509 -in /etc/nginx/ssl/stardragon.top.crt -noout -dates 2>/dev/null | sed 's/^/  /'
else
    print_fail "SSL证书文件不存在"
fi
echo ""

echo "6. 检查防火墙..."
if ufw status 2>/dev/null | grep -q "443/tcp.*ALLOW"; then
    print_ok "防火墙已开放443端口"
else
    print_warn "请确认云服务商安全组已开放443端口"
fi
echo ""

echo "========================================="
echo "配置摘要"
echo "========================================="
echo "域名: $DOMAIN"
echo "服务器IP: $IP"
echo "HTTP: http://$DOMAIN (自动跳转HTTPS)"
echo "HTTPS: https://$DOMAIN"
echo ""
echo "下一步:"
echo "  1. 在阿里云DNS控制台添加A记录"
echo "  2. 在阿里云安全组开放80和443端口"
echo "  3. 等待DNS生效后访问测试"
echo "  4. 申请正式SSL证书消除浏览器警告"
echo ""
