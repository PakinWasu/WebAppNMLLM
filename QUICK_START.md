# Quick Start Guide - การเริ่มต้นใช้งาน

## 🚀 การเริ่มต้นใช้งานอย่างรวดเร็ว

### 1. ตรวจสอบ Services

```bash
# ตรวจสอบสถานะ services
docker compose -f docker-compose.prod.yml ps

# ดู logs
docker compose -f docker-compose.prod.yml logs -f
```

### 2. เข้าถึง Application

#### ใช้ IP Address
- **Frontend**: `http://10.4.15.53` (เปลี่ยนเป็น IP ของ server)
- **Backend API**: `http://10.4.15.53:8000/docs`

#### ใช้ Domain Name (แนะนำ)

**ตั้งค่า Domain:**

```bash
# ตั้งค่า domain name
./setup-domain.sh mnp.example.com

# หรือแก้ไข frontend/nginx.conf โดยตรง
# เปลี่ยน server_name _; เป็น server_name mnp.example.com www.mnp.example.com _;
```

**ตั้งค่า DNS (สำหรับ LAN):**

บนเครื่อง client แต่ละเครื่อง:

**Windows:**
```
แก้ไข: C:\Windows\System32\drivers\etc\hosts
เพิ่ม: 10.4.15.53    mnp.example.com
```

**Linux/Mac:**
```bash
sudo nano /etc/hosts
# เพิ่ม: 10.4.15.53    mnp.example.com
```

**เข้าถึง:**
- **Frontend**: `http://mnp.example.com`
- **Backend API**: `http://mnp.example.com:8000/docs`

### 3. Login

- **Username**: `admin`
- **Password**: `admin123`

⚠️ **เปลี่ยนรหัสผ่านทันทีหลังจาก login ครั้งแรก!**

## 🔧 คำสั่งที่ใช้บ่อย

### Docker Compose Commands

```bash
# ใช้ docker compose (มี space) แทน docker-compose (มี hyphen)

# Start services
docker compose -f docker-compose.prod.yml up -d

# Stop services
docker compose -f docker-compose.prod.yml down

# Restart services
docker compose -f docker-compose.prod.yml restart

# Rebuild และ restart
docker compose -f docker-compose.prod.yml up -d --build

# ดู logs
docker compose -f docker-compose.prod.yml logs -f [service-name]

# ตรวจสอบสถานะ
docker compose -f docker-compose.prod.yml ps
```

### Firewall

```bash
# อนุญาต HTTP (port 80)
sudo ufw allow 80/tcp

# อนุญาต Backend API (port 8000)
sudo ufw allow 8000/tcp

# ตรวจสอบสถานะ
sudo ufw status
```

### ตรวจสอบ IP Address

```bash
# ดู IP address ของ server
hostname -I
# หรือ
ip addr show
```

## 📝 หมายเหตุ

- **Docker Compose V2**: ใช้ `docker compose` (มี space) แทน `docker-compose` (มี hyphen)
- **Domain Name**: สำหรับ LAN ใช้ /etc/hosts, สำหรับ Internet ต้องมี public domain
- **Firewall**: ต้องอนุญาต port 80 และ 8000
- **Storage Permissions**: ถ้ามีปัญหา ให้รัน `./fix-storage-permissions.sh`

## 🔍 การแก้ไขปัญหา

### ไม่สามารถเข้าถึง Frontend

1. ตรวจสอบ services:
   ```bash
   docker compose -f docker-compose.prod.yml ps
   ```

2. ตรวจสอบ logs:
   ```bash
   docker compose -f docker-compose.prod.yml logs frontend
   ```

3. ตรวจสอบ firewall:
   ```bash
   sudo ufw status
   ```

4. ทดสอบจาก server:
   ```bash
   curl http://localhost
   ```

### Domain ไม่ทำงาน

1. ตรวจสอบ DNS resolution:
   ```bash
   nslookup mnp.example.com
   ping mnp.example.com
   ```

2. ตรวจสอบ /etc/hosts (สำหรับ LAN)

3. ตรวจสอบ nginx.conf:
   ```bash
   docker exec mnp-frontend-prod cat /etc/nginx/conf.d/default.conf
   ```

## 📚 เอกสารเพิ่มเติม

- `README.md` - เอกสารหลัก
- `NGINX_SETUP.md` - การตั้งค่า Nginx
- `DOMAIN_SETUP.md` - การตั้งค่า Domain Name
- `STORAGE_FIX.md` - การแก้ไขปัญหา Storage
- `MONGODB_4.4_COMPATIBILITY.md` - MongoDB Compatibility

