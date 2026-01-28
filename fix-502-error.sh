#!/bin/bash

# สคริปต์แก้ไขปัญหา 502 Bad Gateway
# Usage: ./fix-502-error.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "🔧 แก้ไขปัญหา 502 Bad Gateway"
echo "=========================================="
echo ""

# ตรวจสอบ Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker ไม่พบ!"
    exit 1
fi

# ตรวจสอบ Docker Compose
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo "❌ Docker Compose ไม่พบ!"
    exit 1
fi

# ตรวจสอบว่า containers ทำงานอยู่หรือไม่
echo "🐳 ตรวจสอบ Docker containers..."
echo ""

# ตรวจสอบ Backend
BACKEND_RUNNING=false
if docker ps | grep -q "mnp-backend-prod"; then
    BACKEND_CONTAINER="mnp-backend-prod"
    BACKEND_RUNNING=true
    echo "✅ Backend container (prod) ทำงานอยู่"
elif docker ps | grep -q "mnp-backend"; then
    BACKEND_CONTAINER="mnp-backend"
    BACKEND_RUNNING=true
    echo "✅ Backend container (dev) ทำงานอยู่"
else
    echo "❌ Backend container ไม่ทำงาน!"
    echo "   กำลัง start backend..."
    $DOCKER_COMPOSE -f docker-compose.prod.yml up -d backend 2>/dev/null || \
    $DOCKER_COMPOSE up -d backend 2>/dev/null || {
        echo "   ⚠️  ไม่สามารถ start backend ได้"
    }
fi

# ตรวจสอบ Frontend
FRONTEND_RUNNING=false
if docker ps | grep -q "mnp-frontend-prod"; then
    FRONTEND_CONTAINER="mnp-frontend-prod"
    FRONTEND_RUNNING=true
    echo "✅ Frontend container (prod) ทำงานอยู่"
elif docker ps | grep -q "mnp-frontend"; then
    FRONTEND_CONTAINER="mnp-frontend"
    FRONTEND_RUNNING=true
    echo "✅ Frontend container (dev) ทำงานอยู่"
else
    echo "❌ Frontend container ไม่ทำงาน!"
    echo "   กำลัง start frontend..."
    $DOCKER_COMPOSE -f docker-compose.prod.yml up -d frontend 2>/dev/null || \
    $DOCKER_COMPOSE up -d frontend 2>/dev/null || {
        echo "   ⚠️  ไม่สามารถ start frontend ได้"
    }
fi

# ตรวจสอบ ports
echo ""
echo "🔌 ตรวจสอบ ports..."
BACKEND_PORT=""
FRONTEND_PORT=""

# ตรวจสอบ backend port
if docker ps --format "{{.Ports}}" | grep -q ":8000"; then
    BACKEND_PORT="8000"
    echo "✅ Backend port 8000 เปิดอยู่"
else
    echo "⚠️  Backend port 8000 ไม่พบ"
fi

# ตรวจสอบ frontend port
if docker ps --format "{{.Ports}}" | grep -q ":8080"; then
    FRONTEND_PORT="8080"
    echo "✅ Frontend port 8080 เปิดอยู่"
elif docker ps --format "{{.Ports}}" | grep -q ":5173"; then
    FRONTEND_PORT="5173"
    echo "✅ Frontend port 5173 เปิดอยู่ (dev mode)"
else
    echo "⚠️  Frontend port ไม่พบ"
fi

# ตรวจสอบ Nginx
echo ""
echo "🌐 ตรวจสอบ Nginx..."

if ! command -v nginx &> /dev/null; then
    echo "⚠️  Nginx ไม่พบบน host"
    echo "   ถ้าคุณใช้ Nginx บน host ให้ติดตั้ง: sudo apt install nginx"
else
    # ตรวจสอบว่า Nginx ทำงานอยู่หรือไม่
    if systemctl is-active --quiet nginx 2>/dev/null || pgrep nginx > /dev/null; then
        echo "✅ Nginx ทำงานอยู่"
        
        # ตรวจสอบ configuration
        if sudo nginx -t 2>/dev/null; then
            echo "✅ Nginx configuration ถูกต้อง"
        else
            echo "⚠️  Nginx configuration มีปัญหา"
            echo "   ตรวจสอบ: sudo nginx -t"
        fi
        
        # ตรวจสอบ config file
        NGINX_CONFIG="/etc/nginx/sites-available/mnp"
        if [ -f "$NGINX_CONFIG" ]; then
            echo "✅ พบ Nginx config: $NGINX_CONFIG"
            
            # ตรวจสอบว่า config ชี้ไปที่ port ที่ถูกต้องหรือไม่
            if grep -q "proxy_pass http://127.0.0.1:8000" "$NGINX_CONFIG"; then
                echo "✅ Backend proxy config ถูกต้อง"
            else
                echo "⚠️  Backend proxy config อาจไม่ถูกต้อง"
            fi
            
            if grep -q "proxy_pass http://127.0.0.1:8080" "$NGINX_CONFIG"; then
                echo "✅ Frontend proxy config ถูกต้อง"
            else
                echo "⚠️  Frontend proxy config อาจไม่ถูกต้อง"
            fi
        else
            echo "⚠️  ไม่พบ Nginx config file"
            echo "   สร้าง config: $NGINX_CONFIG"
        fi
    else
        echo "⚠️  Nginx ไม่ทำงาน"
        echo "   Start Nginx: sudo systemctl start nginx"
    fi
fi

# สร้าง/แก้ไข Nginx config
echo ""
echo "📝 สร้าง/แก้ไข Nginx configuration..."

NGINX_CONFIG="/etc/nginx/sites-available/mnp"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-8080}"

if [ -w "$NGINX_CONFIG" ] || [ "$EUID" -eq 0 ]; then
    sudo tee "$NGINX_CONFIG" > /dev/null <<EOF
server {
    listen 80;
    server_name _;
    
    # Increase client body size for file uploads
    client_max_body_size 10M;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json application/javascript;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # API proxy - proxy all API endpoints to backend
    location ~ ^/(auth|users|projects|ai|docs|openapi\.json|folders|summary|project-options|health) {
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # Increase timeouts for long-running requests
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
        
        # Disable buffering for streaming responses
        proxy_buffering off;
    }
    
    # Frontend static files (proxy to Docker container)
    location / {
        proxy_pass http://127.0.0.1:${FRONTEND_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Increase timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF
    
    echo "✅ สร้าง/อัปเดต Nginx config: $NGINX_CONFIG"
    
    # Enable site
    if [ ! -L "/etc/nginx/sites-enabled/mnp" ]; then
        sudo ln -sf "$NGINX_CONFIG" /etc/nginx/sites-enabled/mnp
        echo "✅ Enable Nginx site"
    fi
    
    # Remove default site if exists
    if [ -f /etc/nginx/sites-enabled/default ]; then
        sudo rm /etc/nginx/sites-enabled/default
        echo "✅ ลบ default site"
    fi
    
    # Test configuration
    if sudo nginx -t; then
        echo "✅ Nginx configuration ถูกต้อง"
        
        # Reload Nginx
        if sudo systemctl reload nginx 2>/dev/null || sudo nginx -s reload 2>/dev/null; then
            echo "✅ Reload Nginx สำเร็จ"
        else
            echo "⚠️  ไม่สามารถ reload Nginx ได้"
            echo "   ลอง: sudo systemctl restart nginx"
        fi
    else
        echo "❌ Nginx configuration มีปัญหา"
        echo "   ตรวจสอบ: sudo nginx -t"
    fi
else
    echo "⚠️  ไม่สามารถเขียน Nginx config ได้ (ต้องใช้ sudo)"
    echo "   รันด้วย sudo: sudo ./fix-502-error.sh"
fi

# ทดสอบการเชื่อมต่อ
echo ""
echo "🧪 ทดสอบการเชื่อมต่อ..."

# ทดสอบ Backend
if [ -n "$BACKEND_PORT" ]; then
    if curl -s http://localhost:${BACKEND_PORT}/docs &>/dev/null; then
        echo "✅ Backend API ตอบสนองที่ port ${BACKEND_PORT}"
    else
        echo "⚠️  Backend API ไม่ตอบสนองที่ port ${BACKEND_PORT}"
        echo "   ตรวจสอบ logs: docker logs ${BACKEND_CONTAINER:-mnp-backend-prod}"
    fi
fi

# ทดสอบ Frontend
if [ -n "$FRONTEND_PORT" ]; then
    if curl -s http://localhost:${FRONTEND_PORT} &>/dev/null; then
        echo "✅ Frontend ตอบสนองที่ port ${FRONTEND_PORT}"
    else
        echo "⚠️  Frontend ไม่ตอบสนองที่ port ${FRONTEND_PORT}"
        echo "   ตรวจสอบ logs: docker logs ${FRONTEND_CONTAINER:-mnp-frontend-prod}"
    fi
fi

# สรุป
echo ""
echo "=========================================="
echo "✅ การแก้ไขเสร็จสิ้น"
echo "=========================================="
echo ""
echo "📋 สรุป:"
echo "  - Backend: http://localhost:${BACKEND_PORT:-8000}"
echo "  - Frontend: http://localhost:${FRONTEND_PORT:-8080}"
echo "  - ผ่าน Nginx: http://10.4.15.167"
echo ""
echo "🔍 ตรวจสอบ:"
echo "  - Backend logs: docker logs ${BACKEND_CONTAINER:-mnp-backend-prod}"
echo "  - Frontend logs: docker logs ${FRONTEND_CONTAINER:-mnp-frontend-prod}"
echo "  - Nginx logs: sudo tail -f /var/log/nginx/error.log"
echo ""
echo "📝 ถ้ายังมีปัญหา:"
echo "  1. ตรวจสอบว่า containers ทำงาน: docker ps"
echo "  2. ตรวจสอบ ports: netstat -tulpn | grep -E '8000|8080'"
echo "  3. ตรวจสอบ Nginx: sudo nginx -t"
echo "  4. Restart services: docker-compose restart"
echo ""
