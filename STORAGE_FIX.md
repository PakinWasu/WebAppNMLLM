# การแก้ไขปัญหา Storage Permissions

เอกสารนี้อธิบายการแก้ไขปัญหา storage permissions สำหรับการใช้งานทั้ง Windows และ Ubuntu Server

## 🔧 ปัญหาที่แก้ไข

1. **Storage permissions ใน Ubuntu Server**: ไฟล์ถูกเก็บไว้แต่ไม่สามารถอ่าน/เขียนได้
2. **Cross-platform compatibility**: รองรับการใช้งานทั้ง Windows Desktop และ Ubuntu Server
3. **Nginx LAN access**: ตั้งค่าให้คนใน LAN เข้าถึงได้หลายคนพร้อมกัน

## ✅ การแก้ไขที่ทำ

### 1. ปรับปรุง Nginx Configuration

ไฟล์: `frontend/nginx.conf`

- ✅ Proxy API requests ทั้งหมด (`/auth`, `/users`, `/projects`, `/ai`, `/docs`) ไปยัง backend
- ✅ เพิ่ม timeout สำหรับ long-running requests (600s)
- ✅ เพิ่ม `client_max_body_size` สำหรับ file uploads (10M)
- ✅ ปรับปรุง proxy headers สำหรับ LAN access

### 2. ปรับปรุง Storage Permissions

#### ไฟล์: `backend/init-storage.sh`
- ✅ ตรวจจับ OS (Windows/WSL vs Linux/Ubuntu)
- ✅ ตั้งค่า permissions ที่เหมาะสมสำหรับแต่ละ OS
- ✅ Fix permissions แบบ recursive สำหรับไฟล์และโฟลเดอร์

#### ไฟล์: `backend/app/services/document_storage.py`
- ✅ ปรับปรุง `ensure_storage_base()` ให้จัดการ permissions ดีขึ้น
- ✅ รองรับทั้ง Windows และ Linux
- ✅ Fix permissions แบบ recursive เมื่อสร้าง storage

#### ไฟล์: `docker-compose.prod.yml`
- ✅ เพิ่ม entrypoint script เพื่อ fix permissions ตอน startup
- ✅ เรียก `init-storage.sh` ก่อน start application

### 3. สร้าง Fix Permissions Script

ไฟล์: `fix-storage-permissions.sh`
- ✅ Script สำหรับ fix permissions บน Ubuntu Server
- ✅ ใช้งานได้ทั้ง root และ non-root user

## 🚀 วิธีใช้งาน

### สำหรับ Ubuntu Server

#### 1. Fix Permissions บน Host (ทำครั้งเดียว)

```bash
# ไปที่ directory โปรเจค
cd /home/pakin-asawapol-project/Downloads/manage-network-project

# รัน script fix permissions
./fix-storage-permissions.sh

# หรือถ้ายังมีปัญหา ให้ใช้ sudo
sudo chmod -R 777 ./storage
sudo chown -R $(whoami):$(whoami) ./storage
```

#### 2. Rebuild และ Start Services

```bash
# Stop services (ถ้ากำลังรันอยู่)
docker-compose -f docker-compose.prod.yml down

# Rebuild services
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# ตรวจสอบ logs
docker-compose -f docker-compose.prod.yml logs -f backend
```

#### 3. ตรวจสอบ Storage Permissions ใน Container

```bash
# เข้าไปใน backend container
docker exec -it mnp-backend-prod bash

# ตรวจสอบ permissions
ls -la /app/storage
ls -la /app/storage/*/documents/*/1/

# ถ้ายังมีปัญหา ให้ fix ใน container
chmod -R 777 /app/storage
exit
```

### สำหรับ Windows Desktop

ไม่ต้องทำอะไรเพิ่มเติม - ระบบจะจัดการ permissions อัตโนมัติ

### ตั้งค่า LAN Access

#### 1. ตรวจสอบ Firewall

```bash
# อนุญาต HTTP (port 80)
sudo ufw allow 80/tcp

# ตรวจสอบสถานะ
sudo ufw status
```

#### 2. ตรวจสอบ IP Address

```bash
# ดู IP address ของ server
ip addr show
# หรือ
hostname -I
```

#### 3. เข้าถึงจาก LAN

- **Frontend**: `http://<server-ip>`
- **Backend API**: `http://<server-ip>:8000/docs`

#### 4. ทดสอบจากเครื่องอื่นใน LAN

```bash
# ทดสอบ frontend
curl http://<server-ip>/

# ทดสอบ backend API
curl http://<server-ip>:8000/

# ทดสอบ login
curl http://<server-ip>/auth/login -X POST \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

## 🔍 การตรวจสอบ

### 1. ตรวจสอบว่า Storage ทำงาน

```bash
# ดู logs ของ backend
docker logs mnp-backend-prod | grep -i storage

# ตรวจสอบว่าไฟล์ถูกสร้าง
ls -la ./storage/*/documents/*/1/
```

### 2. ตรวจสอบ Nginx Proxy

```bash
# ดู logs ของ frontend
docker logs mnp-frontend-prod

# ทดสอบ API endpoint
curl -v http://localhost/auth/login -X POST \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

### 3. ตรวจสอบ Network Connectivity

```bash
# ตรวจสอบว่า containers อยู่ใน network เดียวกัน
docker network inspect manage-network-project_mnp-network

# ทดสอบ connection จาก frontend ไป backend
docker exec mnp-frontend-prod wget -O- http://backend:8000/
```

## 🐛 การแก้ไขปัญหา

### ปัญหา: ยังไม่สามารถอ่าน/เขียนไฟล์ได้

**แก้ไข**:
```bash
# 1. Fix permissions บน host
sudo chmod -R 777 ./storage
sudo chown -R $(whoami):$(whoami) ./storage

# 2. Restart containers
docker-compose -f docker-compose.prod.yml restart backend

# 3. Fix permissions ใน container
docker exec mnp-backend-prod chmod -R 777 /app/storage
```

### ปัญหา: Nginx ไม่สามารถ proxy ไปยัง backend

**แก้ไข**:
```bash
# 1. ตรวจสอบว่า backend ทำงาน
docker-compose -f docker-compose.prod.yml ps

# 2. ตรวจสอบ network
docker network inspect manage-network-project_mnp-network

# 3. ทดสอบ connection
docker exec mnp-frontend-prod ping backend
docker exec mnp-frontend-prod wget -O- http://backend:8000/
```

### ปัญหา: ไม่สามารถเข้าถึงจาก LAN

**แก้ไข**:
```bash
# 1. ตรวจสอบ firewall
sudo ufw status
sudo ufw allow 80/tcp

# 2. ตรวจสอบว่า service bind ที่ 0.0.0.0
docker-compose -f docker-compose.prod.yml ps
# ดูว่า ports แสดงเป็น "0.0.0.0:80->80/tcp"

# 3. ตรวจสอบ IP address
ip addr show
```

## 📝 หมายเหตุ

- Storage directory (`./storage`) จะถูก mount จาก host เข้า container
- Permissions จะถูก fix อัตโนมัติเมื่อ container start
- สำหรับ production, แนะนำให้ backup storage directory เป็นประจำ
- ไฟล์เก่าที่มีอยู่แล้วจะยังคงอยู่ แต่ต้อง fix permissions ให้ถูกต้อง

## ✅ Checklist

- [ ] รัน `fix-storage-permissions.sh` บน Ubuntu Server
- [ ] Rebuild และ restart services
- [ ] ตรวจสอบว่า storage permissions ถูกต้อง
- [ ] ทดสอบ upload/delete ไฟล์
- [ ] ตั้งค่า firewall สำหรับ LAN access
- [ ] ทดสอบเข้าถึงจากเครื่องอื่นใน LAN
- [ ] ตรวจสอบ Nginx proxy ทำงานถูกต้อง

