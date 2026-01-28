# 🔧 แก้ไขปัญหา 502 Bad Gateway

## ปัญหา

เมื่อเข้าถึงที่ `http://10.4.15.167` จะเห็น error "502 Bad Gateway" จาก Nginx

## สาเหตุที่เป็นไปได้

1. **Backend container ไม่ทำงาน** - Nginx ไม่สามารถเชื่อมต่อกับ backend ได้
2. **Frontend container ไม่ทำงาน** - Nginx ไม่สามารถเชื่อมต่อกับ frontend ได้
3. **Nginx configuration ไม่ถูกต้อง** - Config ชี้ไปที่ port ที่ผิด
4. **Ports ไม่ถูกต้อง** - Backend/Frontend ไม่ได้ bind กับ port ที่ Nginx คาดหวัง

## วิธีแก้ไข

### วิธีที่ 1: ใช้สคริปต์อัตโนมัติ (แนะนำ)

```bash
# รันสคริปต์แก้ไขอัตโนมัติ
./fix-502-error.sh

# หรือถ้าต้องการใช้ sudo
sudo ./fix-502-error.sh
```

สคริปต์นี้จะ:
- ✅ ตรวจสอบและ start containers ที่ไม่ทำงาน
- ✅ ตรวจสอบ ports
- ✅ สร้าง/แก้ไข Nginx configuration
- ✅ Reload Nginx
- ✅ ทดสอบการเชื่อมต่อ

### วิธีที่ 2: แก้ไขด้วยตนเอง

#### 1. ตรวจสอบว่า containers ทำงานอยู่

```bash
# ตรวจสอบ containers
docker ps

# ควรเห็น:
# - mnp-backend-prod หรือ mnp-backend
# - mnp-frontend-prod หรือ mnp-frontend

# ถ้าไม่เห็น ให้ start:
docker-compose -f docker-compose.prod.yml up -d
# หรือ
docker-compose up -d
```

#### 2. ตรวจสอบ ports

```bash
# ตรวจสอบว่า ports เปิดอยู่
netstat -tulpn | grep -E '8000|8080'

# หรือ
ss -tulpn | grep -E '8000|8080'

# ควรเห็น:
# - Port 8000 (Backend)
# - Port 8080 (Frontend - prod) หรือ 5173 (dev)
```

#### 3. ทดสอบการเชื่อมต่อ

```bash
# ทดสอบ Backend
curl http://localhost:8000/docs

# ทดสอบ Frontend
curl http://localhost:8080
# หรือ (dev mode)
curl http://localhost:5173
```

#### 4. ตรวจสอบ Nginx configuration

```bash
# ตรวจสอบ config
sudo nginx -t

# ดู config file
sudo cat /etc/nginx/sites-available/mnp

# ตรวจสอบว่า config ชี้ไปที่ port ที่ถูกต้อง:
# - Backend: proxy_pass http://127.0.0.1:8000;
# - Frontend: proxy_pass http://127.0.0.1:8080;
```

#### 5. สร้าง/แก้ไข Nginx config

```bash
# สร้าง config file
sudo nano /etc/nginx/sites-available/mnp
```

เนื้อหาที่ควรมี:

```nginx
server {
    listen 80;
    server_name _;
    
    client_max_body_size 10M;
    
    # API proxy
    location ~ ^/(auth|users|projects|ai|docs|openapi\.json|folders|summary|project-options|health) {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
        proxy_buffering off;
    }
    
    # Frontend
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 6. Enable และ Reload Nginx

```bash
# Enable site
sudo ln -sf /etc/nginx/sites-available/mnp /etc/nginx/sites-enabled/mnp

# ลบ default site (ถ้ามี)
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
# หรือ
sudo nginx -s reload
```

## ตรวจสอบ Logs

### Backend Logs

```bash
# ดู logs
docker logs mnp-backend-prod -f

# หรือ
docker logs mnp-backend -f
```

### Frontend Logs

```bash
# ดู logs
docker logs mnp-frontend-prod -f

# หรือ
docker logs mnp-frontend -f
```

### Nginx Logs

```bash
# Error logs
sudo tail -f /var/log/nginx/error.log

# Access logs
sudo tail -f /var/log/nginx/access.log
```

## การแก้ไขปัญหาเพิ่มเติม

### ปัญหา: Backend ไม่ตอบสนอง

```bash
# ตรวจสอบว่า backend container ทำงาน
docker ps | grep backend

# Restart backend
docker-compose restart backend

# หรือ
docker restart mnp-backend-prod
```

### ปัญหา: Frontend ไม่ตอบสนอง

```bash
# ตรวจสอบว่า frontend container ทำงาน
docker ps | grep frontend

# Restart frontend
docker-compose restart frontend

# หรือ
docker restart mnp-frontend-prod
```

### ปัญหา: Port ถูกใช้งานแล้ว

```bash
# ตรวจสอบ process ที่ใช้ port
sudo lsof -i :8000
sudo lsof -i :8080

# หยุด process
sudo kill -9 <PID>
```

### ปัญหา: Nginx ไม่สามารถเชื่อมต่อได้

```bash
# ตรวจสอบว่า backend/frontend bind กับ 127.0.0.1 หรือ 0.0.0.0
docker ps --format "{{.Ports}}"

# ควรเห็น: 0.0.0.0:8000->8000/tcp หรือ 127.0.0.1:8000->8000/tcp
```

## ทดสอบหลังจากแก้ไข

```bash
# ทดสอบผ่าน Nginx
curl http://10.4.15.167

# ทดสอบ Backend API
curl http://10.4.15.167/docs

# ทดสอบ Frontend
curl http://10.4.15.167
```

## URLs สำหรับเข้าใช้งาน

- **Frontend**: http://10.4.15.167
- **Backend API**: http://10.4.15.167/docs
- **Backend Direct**: http://10.4.15.167:8000/docs
- **Frontend Direct**: http://10.4.15.167:8080

## คำสั่งที่มีประโยชน์

```bash
# ตรวจสอบสถานะทั้งหมด
./check-and-fix.sh

# แก้ไข 502 error
./fix-502-error.sh

# Restart services
docker-compose restart

# ดู logs ทั้งหมด
docker-compose logs -f
```
