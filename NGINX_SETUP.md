# การตั้งค่า Nginx สำหรับ LAN Access

เอกสารนี้อธิบายวิธีการตั้งค่า Nginx เพื่อให้ผู้ใช้ใน LAN สามารถเข้าถึงแอปพลิเคชันได้หลายคนพร้อมกัน

## 📋 สารบัญ

- [ภาพรวม](#ภาพรวม)
- [การตั้งค่าใน Docker (แนะนำ)](#การตั้งค่าใน-docker-แนะนำ)
- [การตั้งค่า Nginx บน Host (Advanced)](#การตั้งค่า-nginx-บน-host-advanced)
- [การแก้ไขปัญหา](#การแก้ไขปัญหา)

## ภาพรวม

แอปพลิเคชันนี้ใช้ Nginx ใน Docker container เพื่อ:
- Serve frontend static files
- Proxy API requests ไปยัง backend
- รองรับการเข้าถึงจากหลายคนพร้อมกัน

## การตั้งค่าใน Docker (แนะนำ)

### 1. ตรวจสอบ docker-compose.prod.yml

ไฟล์ `docker-compose.prod.yml` ได้ตั้งค่าไว้แล้ว:
- Frontend (Nginx) เปิด port 80
- Backend เปิด port 8000
- ทั้งหมดอยู่ใน network เดียวกัน (`mnp-network`)

### 2. Build และ Start Services

```bash
# Build และ start services
docker compose -f docker-compose.prod.yml up -d --build

# ตรวจสอบสถานะ
docker compose -f docker-compose.prod.yml ps
```

### 3. ตั้งค่า Domain Name (Optional)

#### วิธีที่ 1: ใช้ Script (แนะนำ)

```bash
# ตั้งค่า domain name
./setup-domain.sh mnp.example.com

# Rebuild และ restart
docker compose -f docker-compose.prod.yml build frontend
docker compose -f docker-compose.prod.yml up -d frontend
```

#### วิธีที่ 2: แก้ไข nginx.conf โดยตรง

แก้ไข `frontend/nginx.conf`:

```nginx
server {
    listen 80;
    server_name mnp.example.com www.mnp.example.com _;  # เพิ่ม domain name
    # ... rest of config
}
```

แล้ว rebuild:
```bash
docker compose -f docker-compose.prod.yml build frontend
docker compose -f docker-compose.prod.yml up -d frontend
```

#### ตั้งค่า DNS (สำหรับ LAN)

บนเครื่อง client แต่ละเครื่อง แก้ไข `/etc/hosts` (Linux/Mac) หรือ `C:\Windows\System32\drivers\etc\hosts` (Windows):

```
10.4.15.53    mnp.example.com
10.4.15.53    www.mnp.example.com
```

(เปลี่ยน `10.4.15.53` เป็น IP address ของ server)

### 3. ตรวจสอบ Firewall

บน Ubuntu Server:

```bash
# อนุญาต HTTP (port 80)
sudo ufw allow 80/tcp

# อนุญาต Backend API (port 8000) - ถ้าต้องการเข้าถึงโดยตรง
sudo ufw allow 8000/tcp

# ตรวจสอบสถานะ firewall
sudo ufw status
```

### 4. เข้าถึงจาก LAN

- **Frontend**: `http://<server-ip>` หรือ `http://<server-hostname>`
- **Backend API Docs**: `http://<server-ip>:8000/docs` (ถ้าเปิด port 8000)

### 5. ตรวจสอบว่า Nginx Proxy ทำงาน

ทดสอบ API endpoint:

```bash
# จากเครื่องอื่นใน LAN
curl http://<server-ip>/auth/login -X POST -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}'
```

## การตั้งค่า Nginx บน Host (Advanced)

ถ้าต้องการใช้ Nginx บน host แทน Docker container:

### 1. ติดตั้ง Nginx

```bash
sudo apt update
sudo apt install nginx -y
```

### 2. สร้าง Nginx Configuration

สร้างไฟล์ `/etc/nginx/sites-available/mnp`:

```nginx
server {
    listen 80;
    server_name _;  # หรือใส่ domain/IP ของ server
    
    # Increase client body size for file uploads
    client_max_body_size 10M;
    
    # Frontend static files
    location / {
        proxy_pass http://localhost:80;  # หรือ port ที่ frontend container ใช้
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # API proxy
    location ~ ^/(auth|users|projects|ai|docs|openapi\.json) {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase timeouts for long-running requests
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }
}
```

### 3. Enable Site

```bash
sudo ln -s /etc/nginx/sites-available/mnp /etc/nginx/sites-enabled/
sudo nginx -t  # ตรวจสอบ configuration
sudo systemctl reload nginx
```

### 4. ปรับ docker-compose.prod.yml

เปลี่ยน port mapping:

```yaml
frontend:
  ports:
    - "8080:80"  # เปลี่ยนจาก 80:80 เป็น 8080:80

backend:
  ports:
    - "8001:8000"  # เปลี่ยนจาก 8000:8000 เป็น 8001:8000
```

และอัปเดต Nginx config ให้ชี้ไปที่ port ใหม่

## การแก้ไขปัญหา

### Nginx ไม่สามารถ proxy ไปยัง backend ได้

**ปัญหา**: `502 Bad Gateway` หรือ `Connection refused`

**แก้ไข**:
1. ตรวจสอบว่า backend container ทำงาน:
   ```bash
   docker-compose -f docker-compose.prod.yml ps
   docker logs mnp-backend-prod
   ```

2. ตรวจสอบ network:
   ```bash
   docker network inspect manage-network-project_mnp-network
   ```

3. ทดสอบ connection จาก frontend container:
   ```bash
   docker exec mnp-frontend-prod wget -O- http://backend:8000/
   ```

### ไม่สามารถเข้าถึงจาก LAN ได้

**ปัญหา**: เข้าถึงได้เฉพาะ localhost

**แก้ไข**:
1. ตรวจสอบ firewall:
   ```bash
   sudo ufw status
   sudo ufw allow 80/tcp
   ```

2. ตรวจสอบ IP address:
   ```bash
   ip addr show
   ```

3. ตรวจสอบว่า service bind ที่ 0.0.0.0:
   ```bash
   docker-compose -f docker-compose.prod.yml ps
   # ดูว่า ports แสดงเป็น "0.0.0.0:80->80/tcp"
   ```

### API requests ไม่ทำงาน

**ปัญหา**: Frontend ไม่สามารถเรียก API ได้

**แก้ไข**:
1. ตรวจสอบ nginx.conf ใน frontend container:
   ```bash
   docker exec mnp-frontend-prod cat /etc/nginx/conf.d/default.conf
   ```

2. ตรวจสอบ logs:
   ```bash
   docker logs mnp-frontend-prod
   docker logs mnp-backend-prod
   ```

3. ทดสอบ API โดยตรง:
   ```bash
   curl http://<server-ip>:8000/auth/login -X POST -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}'
   ```

### Performance Issues (หลายคนเข้าพร้อมกัน)

**ปรับปรุง**:
1. เพิ่ม worker processes ใน nginx.conf:
   ```nginx
   worker_processes auto;
   worker_connections 1024;
   ```

2. เพิ่ม connection pool ใน docker-compose.prod.yml:
   ```yaml
   backend:
     deploy:
       resources:
         limits:
           cpus: '2'
           memory: 2G
   ```

## 📝 หมายเหตุ

- Nginx ใน Docker container จะ proxy requests ทั้งหมดไปยัง backend โดยอัตโนมัติ
- ไม่จำเป็นต้องตั้งค่า Nginx บน host ถ้าใช้ Docker Compose
- สำหรับ production, แนะนำให้ใช้ HTTPS (Let's Encrypt)

