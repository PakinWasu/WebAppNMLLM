# การตั้งค่า Domain Name สำหรับ Frontend

เอกสารนี้อธิบายวิธีการตั้งค่า domain name แทนการใช้ IP address

## 📋 สารบัญ

- [วิธีที่ 1: แก้ไข nginx.conf ใน Container (แนะนำ)](#วิธีที่-1-แก้ไข-nginxconf-ใน-container-แนะนำ)
- [วิธีที่ 2: ใช้ Nginx บน Host เป็น Reverse Proxy](#วิธีที่-2-ใช้-nginx-บน-host-เป็น-reverse-proxy)
- [การตั้งค่า DNS](#การตั้งค่า-dns)
- [การแก้ไขปัญหา](#การแก้ไขปัญหา)

## วิธีที่ 1: แก้ไข nginx.conf ใน Container (แนะนำ)

### 1. แก้ไข nginx.conf

แก้ไขไฟล์ `frontend/nginx.conf`:

```nginx
server {
    listen 80;
    # เปลี่ยน _ เป็น domain name ของคุณ
    server_name mnp.example.com www.mnp.example.com;
    # หรือถ้าต้องการรองรับทั้ง domain และ IP:
    # server_name mnp.example.com www.mnp.example.com _;
    
    root /usr/share/nginx/html;
    index index.html;
    # ... rest of config
}
```

### 2. Rebuild และ Restart

```bash
docker compose -f docker-compose.prod.yml build frontend
docker compose -f docker-compose.prod.yml up -d frontend
```

## วิธีที่ 2: ใช้ Nginx บน Host เป็น Reverse Proxy

### 1. ติดตั้ง Nginx บน Host

```bash
sudo apt update
sudo apt install nginx -y
```

### 2. สร้าง Nginx Configuration

สร้างไฟล์ `/etc/nginx/sites-available/mnp`:

```nginx
server {
    listen 80;
    server_name mnp.example.com www.mnp.example.com;  # เปลี่ยนเป็น domain ของคุณ
    
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
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
    }
    
    # API proxy - proxy all API endpoints to backend
    location ~ ^/(auth|users|projects|ai|docs|openapi\.json) {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        
        # Increase timeouts for long-running requests
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
        
        # Disable buffering for streaming responses
        proxy_buffering off;
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

ถ้าใช้ Nginx บน host, เปลี่ยน port mapping:

```yaml
frontend:
  ports:
    - "8080:80"  # เปลี่ยนจาก 80:80 เป็น 8080:80

backend:
  ports:
    - "8001:8000"  # เปลี่ยนจาก 8000:8000 เป็น 8001:8000
```

และอัปเดต Nginx config ให้ชี้ไปที่ port ใหม่

## การตั้งค่า DNS

### สำหรับ LAN (Local Network)

#### วิธีที่ 1: แก้ไข /etc/hosts (แต่ละเครื่อง)

บนเครื่อง client (Windows/Linux/Mac):

**Windows:**
```
C:\Windows\System32\drivers\etc\hosts
```

**Linux/Mac:**
```
/etc/hosts
```

เพิ่มบรรทัด:
```
10.4.15.53    mnp.example.com
```

#### วิธีที่ 2: ตั้งค่า DNS Server (สำหรับทั้ง LAN)

ถ้ามี DNS server ใน LAN:

1. เพิ่ม A record:
   ```
   mnp.example.com    A    10.4.15.53
   ```

2. ตั้งค่า DNS server ใน router หรือ DHCP server

### สำหรับ Internet (Public Domain)

1. ซื้อ domain name จาก registrar (เช่น Namecheap, GoDaddy)
2. เพิ่ม A record ใน DNS settings:
   ```
   mnp    A    <your-server-public-ip>
   www    A    <your-server-public-ip>
   ```
3. รอ DNS propagation (อาจใช้เวลา 5-30 นาที)

## การแก้ไขปัญหา

### ไม่สามารถเข้าถึงผ่าน Domain ได้

**ตรวจสอบ:**

1. **DNS Resolution:**
   ```bash
   # บน client
   nslookup mnp.example.com
   # หรือ
   ping mnp.example.com
   ```

2. **Nginx Configuration:**
   ```bash
   # บน server
   sudo nginx -t
   sudo systemctl status nginx
   ```

3. **Firewall:**
   ```bash
   sudo ufw status
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp  # สำหรับ HTTPS
   ```

4. **Container Status:**
   ```bash
   docker compose -f docker-compose.prod.yml ps
   docker compose -f docker-compose.prod.yml logs frontend
   ```

### Domain ไม่ resolve

**แก้ไข:**

1. ตรวจสอบ /etc/hosts (สำหรับ LAN)
2. ตรวจสอบ DNS settings (สำหรับ public domain)
3. รอ DNS propagation (สำหรับ public domain)

### SSL/HTTPS (แนะนำสำหรับ Production)

#### ใช้ Let's Encrypt

```bash
# ติดตั้ง certbot
sudo apt install certbot python3-certbot-nginx -y

# สร้าง SSL certificate
sudo certbot --nginx -d mnp.example.com -d www.mnp.example.com

# Auto-renewal (จะตั้งค่าให้อัตโนมัติ)
sudo certbot renew --dry-run
```

Nginx จะถูกอัปเดตให้ใช้ HTTPS อัตโนมัติ

## ตัวอย่าง Configuration

### nginx.conf สำหรับ Domain Specific

```nginx
server {
    listen 80;
    server_name mnp.example.com www.mnp.example.com;
    
    # Redirect HTTP to HTTPS (ถ้ามี SSL)
    # return 301 https://$server_name$request_uri;
    
    root /usr/share/nginx/html;
    index index.html;
    
    # ... rest of config
}
```

### nginx.conf สำหรับรองรับทั้ง Domain และ IP

```nginx
server {
    listen 80;
    # รองรับทั้ง domain และ IP
    server_name mnp.example.com www.mnp.example.com _;
    
    root /usr/share/nginx/html;
    index index.html;
    
    # ... rest of config
}
```

## ✅ Checklist

- [ ] แก้ไข nginx.conf ให้มี server_name
- [ ] Rebuild frontend container
- [ ] ตั้งค่า DNS (hosts file หรือ DNS server)
- [ ] ตรวจสอบ firewall
- [ ] ทดสอบเข้าถึงผ่าน domain
- [ ] (Optional) ตั้งค่า SSL/HTTPS

## 📝 หมายเหตุ

- สำหรับ LAN: ใช้ /etc/hosts หรือ DNS server ใน LAN
- สำหรับ Internet: ต้องมี public IP และ domain name
- แนะนำให้ใช้ HTTPS ใน production (Let's Encrypt)
- ถ้าใช้ Nginx บน host, ต้องแก้ไข port mapping ใน docker-compose.prod.yml

