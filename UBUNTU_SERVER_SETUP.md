# คู่มือการติดตั้งบน Ubuntu Server

เอกสารนี้จะแนะนำการติดตั้งและตั้งค่าโปรเจคบน Ubuntu Server พร้อมใช้งาน Nginx

## 📋 สารบัญ

- [ภาพรวม](#ภาพรวม)
- [ความต้องการของระบบ](#ความต้องการของระบบ)
- [การติดตั้งแบบอัตโนมัติ (แนะนำ)](#การติดตั้งแบบอัตโนมัติ-แนะนำ)
- [การติดตั้งแบบแมนนวล](#การติดตั้งแบบแมนนวล)
- [การตั้งค่า Nginx](#การตั้งค่า-nginx)
- [การใช้งาน](#การใช้งาน)
- [การแก้ไขปัญหา](#การแก้ไขปัญหา)

## ภาพรวม

โปรเจคนี้สามารถทำงานบน Ubuntu Server ได้ 2 แบบ:

1. **แบบที่ 1: ใช้ Nginx ใน Docker Container** (แนะนำสำหรับเริ่มต้น)
   - Frontend container ใช้ Nginx ภายใน Docker
   - เปิด port 80 โดยตรง
   - ง่ายต่อการติดตั้งและจัดการ

2. **แบบที่ 2: ใช้ Nginx บน Host** (แนะนำสำหรับ Production)
   - ใช้ Nginx ที่ติดตั้งบน Ubuntu Server เป็น reverse proxy
   - รองรับ SSL/TLS ได้ง่ายขึ้น
   - จัดการหลายแอปพลิเคชันได้ดีกว่า

## ความต้องการของระบบ

- **Ubuntu Server 20.04 LTS หรือใหม่กว่า**
- **RAM**: อย่างน้อย 4GB (แนะนำ 8GB+)
- **Disk Space**: อย่างน้อย 20GB
- **Network**: มีการเชื่อมต่ออินเทอร์เน็ต
- **สิทธิ์**: sudo access

## การติดตั้งแบบอัตโนมัติ (แนะนำ)

### 1. Clone หรืออัปโหลดโปรเจค

```bash
# ถ้าใช้ Git
git clone <repository-url>
cd WebAppNMLLM

# หรืออัปโหลดไฟล์ผ่าน SCP/SFTP
```

### 2. รันสคริปต์ Setup

```bash
# ให้สิทธิ์ execute
chmod +x scripts/ubuntu/setup-ubuntu-server.sh

# รันสคริปต์
./scripts/ubuntu/setup-ubuntu-server.sh
```

สคริปต์จะทำการ:
- ✅ อัปเดตระบบ
- ✅ ติดตั้ง Docker และ Docker Compose
- ✅ ติดตั้ง Nginx และ dependencies
- ✅ ตั้งค่า Firewall (UFW)
- ✅ สร้างไฟล์ .env จาก .env.example
- ✅ สร้าง directories ที่จำเป็น
- ✅ ตั้งค่า Nginx (ถ้าต้องการ)

### 3. ตรวจสอบและแก้ไข Environment Variables

```bash
nano backend/.env
```

ตรวจสอบและแก้ไขค่าต่างๆ โดยเฉพาะ:
- `JWT_SECRET` - ควรเป็นค่าที่ปลอดภัย (สคริปต์จะสร้างให้อัตโนมัติ)
- `MONGODB_URI` - ควรเป็น `mongodb://mongodb:27017` (ใช้ชื่อ container)
- `AI_MODEL_ENDPOINT` - ตรวจสอบว่า Ollama ทำงาน

### 4. Build และ Start Services

#### แบบที่ 1: ใช้ Nginx ใน Docker Container

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

#### แบบที่ 2: ใช้ Nginx บน Host

```bash
# ตั้งค่า Nginx บน host ก่อน
chmod +x scripts/ubuntu/nginx-setup.sh
./scripts/ubuntu/nginx-setup.sh

# Build และ start services
docker compose -f docker-compose.prod-nginx-host.yml up -d --build
```

### 5. ตรวจสอบสถานะ

```bash
# ดูสถานะ containers
docker compose -f docker-compose.prod.yml ps
# หรือ
docker compose -f docker-compose.prod-nginx-host.yml ps

# ดู logs
docker compose -f docker-compose.prod.yml logs -f
```

### 6. เข้าใช้งาน

- **Frontend**: `http://<server-ip>` หรือ `http://<domain-name>`
- **Backend API**: `http://<server-ip>:8000/docs`
- **Default Login**:
  - Username: `admin`
  - Password: `admin123`

⚠️ **เปลี่ยนรหัสผ่านทันทีหลังจาก login ครั้งแรก!**

## การติดตั้งแบบแมนนวล

### 1. ติดตั้ง Docker

```bash
# อัปเดตระบบ
sudo apt update && sudo apt upgrade -y

# ติดตั้ง Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# เพิ่ม user เข้า docker group
sudo usermod -aG docker $USER
newgrp docker

# ตรวจสอบการติดตั้ง
docker --version
```

### 2. ติดตั้ง Docker Compose

```bash
# ติดตั้ง Docker Compose V2 (Plugin)
DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
mkdir -p ~/.docker/cli-plugins
curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o ~/.docker/cli-plugins/docker-compose
chmod +x ~/.docker/cli-plugins/docker-compose

# ตรวจสอบการติดตั้ง
docker compose version
```

### 3. ติดตั้ง Nginx (ถ้าต้องการใช้บน host)

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

### 4. ตั้งค่า Firewall

```bash
# อนุญาต SSH
sudo ufw allow 22/tcp

# อนุญาต HTTP
sudo ufw allow 80/tcp

# อนุญาต HTTPS
sudo ufw allow 443/tcp

# อนุญาต Backend API (optional)
sudo ufw allow 8000/tcp

# เปิดใช้งาน firewall
sudo ufw enable
```

### 5. สร้าง Environment File

```bash
cd backend
cp .env.example .env
nano .env
```

สร้าง JWT Secret:
```bash
openssl rand -hex 32
```

### 6. สร้าง Directories

```bash
mkdir -p storage mongo-data mongo-backup backups
chmod -R 755 storage mongo-data
```

## การตั้งค่า Nginx

### แบบที่ 1: ใช้ Nginx ใน Docker Container

ไม่ต้องตั้งค่าอะไรเพิ่มเติม Nginx ทำงานใน frontend container แล้ว

### แบบที่ 2: ใช้ Nginx บน Host

#### วิธีที่ 1: ใช้สคริปต์ (แนะนำ)

```bash
chmod +x scripts/ubuntu/nginx-setup.sh
./scripts/ubuntu/nginx-setup.sh
```

#### วิธีที่ 2: ตั้งค่าเอง

1. สร้างไฟล์ config `/etc/nginx/sites-available/mnp`:

```nginx
server {
    listen 80;
    server_name _;  # หรือใส่ domain name
    
    client_max_body_size 10M;
    
    # API proxy
    location ~ ^/(auth|users|projects|ai|docs|openapi\.json|folders|summary|project-options) {
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

2. Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/mnp /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # ถ้ามี
sudo nginx -t
sudo systemctl reload nginx
```

3. ใช้ docker-compose.prod-nginx-host.yml แทน docker-compose.prod.yml

### ตั้งค่า SSL/TLS ด้วย Let's Encrypt

```bash
# ติดตั้ง certbot (ถ้ายังไม่ได้ติดตั้ง)
sudo apt install -y certbot python3-certbot-nginx

# ตั้งค่า SSL
sudo certbot --nginx -d your-domain.com

# Auto-renewal จะตั้งค่าอัตโนมัติ
```

## การใช้งาน

### Start/Stop Services

```bash
# Start
docker compose -f docker-compose.prod.yml up -d
# หรือ
docker compose -f docker-compose.prod-nginx-host.yml up -d

# Stop
docker compose -f docker-compose.prod.yml down

# Restart
docker compose -f docker-compose.prod.yml restart

# View logs
docker compose -f docker-compose.prod.yml logs -f
```

### Update Application

```bash
# Pull latest code
git pull

# Rebuild และ restart
docker compose -f docker-compose.prod.yml up -d --build
```

### Backup

```bash
# Backup MongoDB
docker exec mnp-mongo-prod mongodump --archive=/backup/mongo-$(date +%Y%m%d).archive
docker cp mnp-mongo-prod:/backup/mongo-$(date +%Y%m%d).archive ./backups/
```

## การแก้ไขปัญหา

### ไม่สามารถเข้าถึง Frontend

1. ตรวจสอบ containers:
   ```bash
   docker ps
   ```

2. ตรวจสอบ logs:
   ```bash
   docker logs mnp-frontend-prod
   ```

3. ตรวจสอบ firewall:
   ```bash
   sudo ufw status
   ```

4. ทดสอบจาก server:
   ```bash
   curl http://localhost
   ```

### Nginx ไม่ทำงาน (แบบที่ 2)

1. ตรวจสอบสถานะ:
   ```bash
   sudo systemctl status nginx
   ```

2. ตรวจสอบ config:
   ```bash
   sudo nginx -t
   ```

3. ตรวจสอบ logs:
   ```bash
   sudo tail -f /var/log/nginx/error.log
   ```

### Backend ไม่ทำงาน

1. ตรวจสอบ logs:
   ```bash
   docker logs mnp-backend-prod
   ```

2. ตรวจสอบ MongoDB connection:
   ```bash
   docker exec mnp-mongo-prod mongo --eval "db.runCommand('ping')"
   ```

3. ตรวจสอบ environment variables:
   ```bash
   docker exec mnp-backend-prod env | grep -E "MONGODB|JWT"
   ```

### Port ถูกใช้งานแล้ว

```bash
# ตรวจสอบ port ที่ใช้งาน
sudo netstat -tulpn | grep :80
sudo netstat -tulpn | grep :8000

# หยุด service ที่ใช้ port
sudo systemctl stop nginx  # ถ้าใช้ nginx บน host
# หรือเปลี่ยน port ใน docker-compose.yml
```

### Storage Permissions

```bash
# Fix permissions
chmod -R 755 storage
sudo chown -R $USER:$USER storage
```

## 📚 เอกสารเพิ่มเติม

- `README.md` - เอกสารหลัก
- `NGINX_SETUP.md` - การตั้งค่า Nginx แบบละเอียด
- `QUICK_START.md` - Quick Start Guide
- `scripts/ubuntu/deploy.sh` - สคริปต์สำหรับ deploy

## 📞 Support

สำหรับปัญหาหรือคำถามเพิ่มเติม กรุณาติดต่อทีมพัฒนา
