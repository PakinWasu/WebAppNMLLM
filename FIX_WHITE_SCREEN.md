# แก้ไขปัญหาจอขาว (White Screen)

## ปัญหา

เมื่อเข้าถึงผ่าน `http://10.4.15.167` จะเห็นจอขาว เพราะ nginx บน host ไม่ได้ proxy ไฟล์ assets (JavaScript, CSS) ไปยัง frontend container

## สาเหตุ

- Frontend container ทำงานที่ port 8080
- Nginx บน host ทำงานที่ port 80 แต่ยังไม่ได้ตั้งค่าให้ proxy ไปยัง port 8080

## วิธีแก้ไข

### วิธีที่ 1: ใช้สคริปต์ (ต้องใช้ sudo)

```bash
sudo bash scripts/ubuntu/fix-white-screen.sh
```

### วิธีที่ 2: ตั้งค่าด้วยตนเอง

#### 1. สร้างไฟล์ nginx config

```bash
sudo nano /etc/nginx/sites-available/mnp
```

เพิ่มเนื้อหานี้:

```nginx
server {
    listen 80;
    server_name _;
    
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
    location ~ ^/(auth|users|projects|ai|docs|openapi\.json|folders|summary|project-options) {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
        proxy_buffering off;
    }
    
    # Frontend static files (proxy to Docker container on port 8080)
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

#### 2. Enable site

```bash
sudo ln -sf /etc/nginx/sites-available/mnp /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # ถ้ามี
sudo nginx -t
sudo systemctl reload nginx
```

#### 3. ทดสอบ

```bash
# ทดสอบ HTML
curl http://localhost

# ทดสอบ assets
curl http://localhost/assets/index-C8v5KQXI.js
```

### วิธีที่ 3: เข้าถึงโดยตรงที่ port 8080 (ชั่วคราว)

ถ้ายังแก้ไขไม่ได้ทันที สามารถเข้าถึงโดยตรง:

- **http://10.4.15.167:8080**

## ตรวจสอบว่าแก้ไขแล้ว

1. เปิด browser ไปที่ `http://10.4.15.167`
2. กด F12 เพื่อเปิด Developer Tools
3. ไปที่ tab "Network"
4. Refresh หน้า (Ctrl+R)
5. ตรวจสอบว่าไฟล์ assets (JS, CSS) โหลดสำเร็จ (Status 200)

## ถ้ายังมีปัญหา

1. **Clear browser cache**: Ctrl+Shift+R หรือ Ctrl+F5
2. **ตรวจสอบ logs**:
   ```bash
   sudo tail -f /var/log/nginx/error.log
   docker compose -f docker-compose.prod.yml logs frontend
   ```
3. **ตรวจสอบว่า frontend container ทำงาน**:
   ```bash
   docker compose -f docker-compose.prod.yml ps frontend
   ```

## สรุป

ปัญหาจอขาวเกิดจาก nginx บน host ไม่ได้ proxy ไฟล์ assets ไปยัง frontend container ต้องตั้งค่า nginx ให้ proxy ทั้งหมดไปยัง port 8080
