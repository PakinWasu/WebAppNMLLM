# 🚀 เริ่มต้นใช้งานบน Ubuntu Server

โปรเจคนี้ **ใช้ LLM** (Ollama remote + Scope 2.3.5) สำหรับวิเคราะห์ config — **เมื่ออัปเดตอะไรก็ตาม (โค้ด, .env, LLM) ให้ restart Docker เสมอ**

คู่มือสั้นๆ สำหรับการติดตั้งและใช้งานโปรเจคบน Ubuntu Server

## ⚡ Quick Start

### วิธีที่ 1: คำสั่งเดียว (Setup + Build + Start)

```bash
chmod +x run-on-ubuntu-server.sh
./run-on-ubuntu-server.sh
```

สคริปต์จะติดตั้ง Docker/ dependencies (ถ้ายังไม่มี) จากนั้น build และ start แอป

### วิธีที่ 2: ทำทีละขั้นตอน (3 ขั้นตอน)

#### 1. รันสคริปต์ Setup

```bash
chmod +x scripts/ubuntu/setup-ubuntu-server.sh
./scripts/ubuntu/setup-ubuntu-server.sh
```

แบบไม่ต้องตอบคำถาม (เหมาะกับสคริปต์อัตโนมัติ):

```bash
NON_INTERACTIVE=1 ./scripts/ubuntu/setup-ubuntu-server.sh
```

สคริปต์จะทำการติดตั้งทุกอย่างให้อัตโนมัติ:
- ✅ Docker และ Docker Compose
- ✅ Nginx และ dependencies
- ✅ Firewall configuration
- ✅ Environment variables
- ✅ Required directories

### 2. Build และ Start Services

#### แบบที่ 1: ใช้แค่ Docker (แนะนำสำหรับเริ่มต้น)

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

- Frontend: `http://<server-ip>:8080`
- Backend API: `http://<server-ip>:8000/docs`

#### แบบที่ 2: ใช้ Nginx บน Host (แนะนำสำหรับ Production)

```bash
# ตั้งค่า Nginx บน host
./scripts/ubuntu/nginx-setup.sh

# Build และ start
docker compose -f docker-compose.prod-nginx-host.yml up -d --build
```

- Frontend: `http://<server-ip>` (พอร์ต 80)
- Backend API: `http://<server-ip>:8000/docs` หรือผ่าน Nginx

### 3. เข้าใช้งาน

- **Frontend (แบบที่ 1)**: `http://<server-ip>:8080`
- **Frontend (แบบที่ 2)**: `http://<server-ip>`
- **Backend API**: `http://<server-ip>:8000/docs`
- **Login**: `admin` / `admin123`

⚠️ **เปลี่ยนรหัสผ่านทันทีหลังจาก login!**

## 📋 คำสั่งที่ใช้บ่อย

```bash
# ⚠️ อัปเดตอะไรก็ตาม (โค้ด, .env, LLM config) → restart Docker เสมอ
./update-and-restart.sh
# หรือ pull แล้ว restart
./update-and-restart.sh --pull

# ดูสถานะ
docker compose -f docker-compose.prod.yml ps

# ดู logs
docker compose -f docker-compose.prod.yml logs -f

# Restart
docker compose -f docker-compose.prod.yml restart

# Stop
docker compose -f docker-compose.prod.yml down
```

## 🔧 การแก้ไขปัญหา

### ไม่สามารถเข้าถึง Frontend

- **แบบที่ 1 (Docker อย่างเดียว)**: ใช้ `http://<server-ip>:8080` และเปิดพอร์ต 8080
- **แบบที่ 2 (Nginx บน host)**: ใช้ `http://<server-ip>` และเปิดพอร์ต 80

```bash
# ตรวจสอบ containers
docker ps

# ตรวจสอบ firewall (เปิดพอร์ตที่ใช้)
sudo ufw status
sudo ufw allow 8080/tcp   # แบบที่ 1
# หรือ sudo ufw allow 80/tcp   # แบบที่ 2

# ทดสอบจาก server (แบบที่ 1 ใช้พอร์ต 8080)
curl http://localhost:8080
```

### Nginx ไม่ทำงาน (แบบที่ 2)

```bash
# ตรวจสอบสถานะ
sudo systemctl status nginx

# ตรวจสอบ config
sudo nginx -t

# Reload
sudo systemctl reload nginx
```

## 📚 เอกสารเพิ่มเติม

- **[UBUNTU_SERVER_SETUP.md](UBUNTU_SERVER_SETUP.md)** - คู่มือละเอียด
- **[README.md](README.md)** - เอกสารหลัก
- **[NGINX_SETUP.md](NGINX_SETUP.md)** - การตั้งค่า Nginx

## 🆘 ต้องการความช่วยเหลือ?

ตรวจสอบ logs:
```bash
docker compose -f docker-compose.prod.yml logs
```

หรือดูเอกสารเพิ่มเติมใน `UBUNTU_SERVER_SETUP.md`
