# 🐳 Docker Compose Commands - คู่มือคำสั่งที่ถูกต้อง

## ⚠️ สิ่งสำคัญ

**โปรดระวัง:** โปรเจคนี้มี 2 docker-compose files:
- `docker-compose.yml` - สำหรับ **Development** (ใช้ npm dev server)
- `docker-compose.prod.yml` - สำหรับ **Production** (ใช้ nginx)

**ต้องใช้ `docker-compose.prod.yml` สำหรับ production environment!**

---

## 📋 คำสั่งพื้นฐานสำหรับ Production

### เริ่มต้น Services

```bash
# ใช้คำสั่งนี้สำหรับ Production
docker compose -f docker-compose.prod.yml up -d
```

**ห้ามใช้:**
```bash
# ❌ อย่าใช้คำสั่งนี้ - จะใช้ docker-compose.yml (development)
docker compose up -d
```

### ตรวจสอบสถานะ

```bash
# ตรวจสอบสถานะ services
docker compose -f docker-compose.prod.yml ps

# ดู logs
docker compose -f docker-compose.prod.yml logs

# ดู logs ของ service เฉพาะ
docker compose -f docker-compose.prod.yml logs backend
docker compose -f docker-compose.prod.yml logs frontend
```

### หยุด Services

```bash
# หยุด services (แต่ยังเก็บ containers และ volumes)
docker compose -f docker-compose.prod.yml stop

# หยุดและลบ containers (แต่ยังเก็บ volumes)
docker compose -f docker-compose.prod.yml down

# หยุดและลบทุกอย่างรวม volumes (ระวัง! จะลบข้อมูล)
docker compose -f docker-compose.prod.yml down -v
```

---

## 🔄 การ Restart และ Update

### Restart Services (ไม่ rebuild)

```bash
# Restart services ทั้งหมด
docker compose -f docker-compose.prod.yml restart

# Restart service เฉพาะ
docker compose -f docker-compose.prod.yml restart backend
docker compose -f docker-compose.prod.yml restart frontend
```

### Update Code (Rebuild และ Restart)

#### 1. Update Backend

```bash
# Rebuild backend image
docker compose -f docker-compose.prod.yml build backend

# Restart backend
docker compose -f docker-compose.prod.yml up -d backend
```

#### 2. Update Frontend

```bash
# Rebuild frontend image
docker compose -f docker-compose.prod.yml build frontend

# Restart frontend
docker compose -f docker-compose.prod.yml up -d frontend
```

#### 3. Update ทั้งหมด

```bash
# Rebuild images ทั้งหมด
docker compose -f docker-compose.prod.yml build

# Restart services ทั้งหมด
docker compose -f docker-compose.prod.yml up -d
```

### Update แบบ Clean (ลบ containers เก่าก่อน)

```bash
# 1. หยุดและลบ containers
docker compose -f docker-compose.prod.yml down

# 2. Rebuild images
docker compose -f docker-compose.prod.yml build

# 3. Start services ใหม่
docker compose -f docker-compose.prod.yml up -d
```

---

## 🔍 การตรวจสอบและแก้ไขปัญหา

### ตรวจสอบ Logs

```bash
# ดู logs ทั้งหมด
docker compose -f docker-compose.prod.yml logs

# ดู logs แบบ real-time
docker compose -f docker-compose.prod.yml logs -f

# ดู logs 50 บรรทัดล่าสุด
docker compose -f docker-compose.prod.yml logs --tail 50

# ดู logs ของ service เฉพาะ
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f frontend
```

### ตรวจสอบ Health Status

```bash
# ดูสถานะ health check
docker compose -f docker-compose.prod.yml ps

# ดู health check details
docker inspect mnp-backend-prod --format='{{json .State.Health}}' | python3 -m json.tool
docker inspect mnp-frontend-prod --format='{{json .State.Health}}' | python3 -m json.tool
```

### ทดสอบการเข้าถึง

```bash
# ทดสอบ frontend
curl -I http://localhost

# ทดสอบ backend API
curl http://localhost:8000/docs
```

### ตรวจสอบ Containers ที่ทำงานอยู่

```bash
# ดู containers ทั้งหมด
docker ps -a

# ดูเฉพาะ containers ของโปรเจค
docker ps -a | grep mnp
```

---

## 🚨 ปัญหาที่พบบ่อย

### ปัญหา: Frontend ไม่สามารถเข้าถึงได้

**สาเหตุ:** อาจใช้ `docker-compose.yml` (development) แทน `docker-compose.prod.yml`

**แก้ไข:**
```bash
# 1. หยุด services ทั้งหมด
docker compose -f docker-compose.prod.yml down
docker compose down  # หยุด development containers ถ้ามี

# 2. ตรวจสอบว่าไม่มี containers เก่าค้างอยู่
docker ps -a | grep frontend

# 3. Start production services
docker compose -f docker-compose.prod.yml up -d

# 4. ตรวจสอบสถานะ
docker compose -f docker-compose.prod.yml ps
```

### ปัญหา: Container Restart Loop

**ตรวจสอบ:**
```bash
# ดู logs เพื่อหาสาเหตุ
docker compose -f docker-compose.prod.yml logs frontend --tail 50
docker compose -f docker-compose.prod.yml logs backend --tail 50
```

**แก้ไข:**
```bash
# Rebuild และ restart
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

### ปัญหา: Port Already in Use

**ตรวจสอบ:**
```bash
# ดูว่า port ไหนถูกใช้
sudo netstat -tulpn | grep :80
sudo netstat -tulpn | grep :8000
```

**แก้ไข:**
```bash
# หยุด containers ทั้งหมด
docker compose -f docker-compose.prod.yml down
docker compose down  # ถ้ามี development containers

# ตรวจสอบว่าไม่มี containers เก่า
docker ps -a

# Start ใหม่
docker compose -f docker-compose.prod.yml up -d
```

---

## 📝 Checklist สำหรับการ Update

### ก่อน Update

- [ ] Backup ข้อมูล (ถ้าจำเป็น)
- [ ] ตรวจสอบสถานะ services ปัจจุบัน
- [ ] ดู logs เพื่อตรวจสอบว่าไม่มีปัญหา

### ระหว่าง Update

- [ ] Pull code ใหม่ (ถ้ามี)
- [ ] Rebuild images
- [ ] Restart services
- [ ] ตรวจสอบ logs

### หลัง Update

- [ ] ตรวจสอบสถานะ services (`docker compose -f docker-compose.prod.yml ps`)
- [ ] ทดสอบ frontend (`curl http://localhost`)
- [ ] ทดสอบ backend API (`curl http://localhost:8000/docs`)
- [ ] ตรวจสอบ logs (`docker compose -f docker-compose.prod.yml logs --tail 50`)

---

## 🔄 Workflow สำหรับการ Update Code

### Scenario 1: Update Backend Code

```bash
# 1. Pull code ใหม่ (ถ้าใช้ git)
git pull

# 2. Rebuild backend
docker compose -f docker-compose.prod.yml build backend

# 3. Restart backend
docker compose -f docker-compose.prod.yml up -d backend

# 4. ตรวจสอบ logs
docker compose -f docker-compose.prod.yml logs backend --tail 20
```

### Scenario 2: Update Frontend Code

```bash
# 1. Pull code ใหม่ (ถ้าใช้ git)
git pull

# 2. Rebuild frontend
docker compose -f docker-compose.prod.yml build frontend

# 3. Restart frontend
docker compose -f docker-compose.prod.yml up -d frontend

# 4. ตรวจสอบ logs
docker compose -f docker-compose.prod.yml logs frontend --tail 20
```

### Scenario 3: Update ทั้งหมด

```bash
# 1. Pull code ใหม่ (ถ้าใช้ git)
git pull

# 2. Rebuild ทั้งหมด
docker compose -f docker-compose.prod.yml build

# 3. Restart ทั้งหมด
docker compose -f docker-compose.prod.yml up -d

# 4. ตรวจสอบสถานะ
docker compose -f docker-compose.prod.yml ps
```

### Scenario 4: Clean Update (ลบทุกอย่างแล้ว rebuild)

```bash
# 1. Pull code ใหม่ (ถ้าใช้ git)
git pull

# 2. หยุดและลบ containers
docker compose -f docker-compose.prod.yml down

# 3. Rebuild images (--no-cache ถ้าต้องการ rebuild ใหม่ทั้งหมด)
docker compose -f docker-compose.prod.yml build

# 4. Start services ใหม่
docker compose -f docker-compose.prod.yml up -d

# 5. ตรวจสอบสถานะ
docker compose -f docker-compose.prod.yml ps
```

---

## 🎯 Quick Reference

### คำสั่งที่ใช้บ่อย

```bash
# ✅ ใช้สำหรับ Production
docker compose -f docker-compose.prod.yml up -d          # Start
docker compose -f docker-compose.prod.yml down          # Stop
docker compose -f docker-compose.prod.yml restart        # Restart
docker compose -f docker-compose.prod.yml ps             # Status
docker compose -f docker-compose.prod.yml logs -f        # Logs
docker compose -f docker-compose.prod.yml build           # Rebuild
```

### ❌ คำสั่งที่ห้ามใช้ (ถ้าไม่ใช่ development)

```bash
# ❌ อย่าใช้ - จะใช้ docker-compose.yml (development)
docker compose up -d
docker compose down
docker compose restart
```

---

## 📚 เอกสารเพิ่มเติม

- `README.md` - เอกสารหลัก
- `QUICK_START.md` - คู่มือเริ่มต้นใช้งาน
- `NGINX_SETUP.md` - การตั้งค่า Nginx
- `DOMAIN_SETUP.md` - การตั้งค่า Domain Name

---

## 💡 Tips

1. **ใช้ `-f docker-compose.prod.yml` เสมอ** สำหรับ production
2. **ตรวจสอบ logs** หลังจาก restart เพื่อดูว่ามี error หรือไม่
3. **Backup ข้อมูล** ก่อนทำการ update สำคัญ
4. **ทดสอบ** หลัง update ทุกครั้ง
5. **ใช้ `docker compose` (มี space)** ไม่ใช่ `docker-compose` (มี hyphen) สำหรับ Docker Compose V2

