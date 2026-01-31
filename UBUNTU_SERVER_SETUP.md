# 🐧 คู่มือติดตั้งโปรเจคบน Ubuntu Server

คู่มือละเอียดสำหรับการติดตั้งและใช้งาน WebAppNMLLM บน Ubuntu Server (20.04 LTS ขึ้นไป)

## 📋 สิ่งที่ต้องเตรียม

- **OS**: Ubuntu Server 20.04 LTS หรือใหม่กว่า (22.04 LTS แนะนำ)
- **RAM**: ขั้นต่ำ 8GB (แนะนำ 16GB+ ถ้าใช้โมเดล LLM ขนาดใหญ่)
- **Disk**: พื้นที่ว่างอย่างน้อย 20GB
- **Network**: พอร์ต 22 (SSH), 80 (HTTP), 443 (HTTPS), 8000 (API ถ้าต้องการ)
- **สิทธิ์**: บัญชีผู้ใช้ที่มี `sudo`

## ⚡ วิธีที่ 1: ติดตั้งอัตโนมัติ (แนะนำ)

### ขั้นตอนเดียว (แบบมีคำถาม)

```bash
cd /path/to/WebAppNMLLM
chmod +x scripts/ubuntu/setup-ubuntu-server.sh
./scripts/ubuntu/setup-ubuntu-server.sh
```

### แบบไม่ต้องตอบคำถาม (Non-interactive)

เหมาะกับสคริปต์หรือ CI – ใช้ค่าตั้งต้นทั้งหมด

```bash
NON_INTERACTIVE=1 ./scripts/ubuntu/setup-ubuntu-server.sh
# หรือ
./scripts/ubuntu/setup-ubuntu-server.sh --yes
```

จากนั้น build และรันแอป:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

---

## 📖 วิธีที่ 2: ติดตั้งทีละขั้นตอน

### 1. อัปเดตระบบ

```bash
sudo apt update
sudo apt upgrade -y
```

### 2. ติดตั้งแพ็กเกจที่จำเป็น

```bash
sudo apt install -y curl wget git ufw nginx certbot python3-certbot-nginx
```

### 3. ติดตั้ง Docker

```bash
curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
sudo sh /tmp/get-docker.sh
rm /tmp/get-docker.sh
sudo usermod -aG docker $USER
# ออกจาก SSH แล้ว login ใหม่ หรือรัน: newgrp docker
```

### 4. ตรวจสอบ Docker Compose

```bash
docker compose version
```

ถ้ายังไม่มี ให้ติดตั้ง Docker Compose plugin ตาม [เอกสาร Docker](https://docs.docker.com/compose/install/).

### 5. ตั้งค่า Firewall

```bash
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'
sudo ufw allow 8000/tcp comment 'Backend API'  # ถ้าต้องการเข้า API โดยตรง
echo "y" | sudo ufw enable
```

### 6. ตั้งค่า Environment

```bash
cd /path/to/WebAppNMLLM/backend
cp .env.example .env
nano .env
```

อย่างน้อยให้เปลี่ยน:

- `JWT_SECRET` – สร้างด้วย `openssl rand -hex 32`
- ตัวแปรอื่นตามความต้องการ (MongoDB, Ollama ใช้ค่าตั้งต้นใน Docker ได้)

### 7. สร้างโฟลเดอร์ที่ใช้เก็บข้อมูล

```bash
cd /path/to/WebAppNMLLM
mkdir -p storage mongo-data mongo-backup backups
chmod -R 755 storage mongo-data
```

---

## 🚀 การรันแอปบน Ubuntu Server

มี 2 แบบหลัก:

### แบบ A: ใช้แค่ Docker (ไม่ใช้ Nginx บน host)

- Frontend เข้าผ่าน **พอร์ต 8080**
- Backend เข้าผ่าน **พอร์ต 8000**

```bash
cd /path/to/WebAppNMLLM
docker compose -f docker-compose.prod.yml up -d --build
```

เข้าใช้งาน:

- **Frontend**: `http://<IP-เซิร์ฟเวอร์>:8080`
- **Backend API**: `http://<IP-เซิร์ฟเวอร์>:8000/docs`

### แบบ B: ใช้ Nginx บน host (Production แนะนำ)

- Frontend เข้าผ่าน **พอร์ต 80** (หรือ 443 ถ้าตั้ง HTTPS)
- Backend ผ่าน Nginx หรือตรงพอร์ต 8000 ก็ได้

```bash
# 1. ตั้งค่า Nginx บน host (ครั้งเดียว)
./scripts/ubuntu/nginx-setup.sh

# 2. รันด้วย compose ที่ใช้ Nginx บน host
docker compose -f docker-compose.prod-nginx-host.yml up -d --build
```

เข้าใช้งาน:

- **Frontend**: `http://<IP-เซิร์ฟเวอร์>` หรือ `http://โดเมนของคุณ`
- **Backend API**: `http://<IP-เซิร์ฟเวอร์>/docs` หรือผ่าน reverse proxy

---

## 📌 ข้อมูลเข้าใช้งานเริ่มต้น

- **Username**: `admin`
- **Password**: `admin123`

**ควรเปลี่ยนรหัสผ่านทันทีหลังล็อกอินครั้งแรก**

---

## 🔄 อัปเดตและ Deploy ใหม่

```bash
cd /path/to/WebAppNMLLM
git pull origin main
docker compose -f docker-compose.prod.yml up -d --build
```

หรือใช้สคริปต์ deploy:

```bash
chmod +x scripts/ubuntu/deploy.sh
./scripts/ubuntu/deploy.sh
```

---

## 🔧 แก้ปัญหาเบื้องต้น

### เข้า Frontend ไม่ได้

- **แบบ Docker อย่างเดียว**: ใช้ `http://<IP>:8080` ไม่ใช่พอร์ต 80
- ตรวจสอบ container: `docker compose -f docker-compose.prod.yml ps`
- ตรวจสอบ firewall: `sudo ufw status` และเปิดพอร์ตที่ใช้ (80 หรือ 8080, 8000)

### Docker: permission denied

```bash
sudo usermod -aG docker $USER
# ออกจาก SSH แล้ว login ใหม่
```

### Nginx (แบบ B) ไม่ทำงาน

```bash
sudo nginx -t
sudo systemctl status nginx
sudo systemctl reload nginx
```

### Container ไม่ยอมขึ้น

```bash
docker compose -f docker-compose.prod.yml logs -f
# ดู backend / frontend / mongodb / ollama ว่าตัวไหน error
```

### พอร์ต 80 หรือ 8080 ถูกใช้แล้ว

```bash
sudo ss -tlnp | grep -E ':80|:8080'
# ปิด process ที่ใช้พอร์ตหรือเปลี่ยนพอร์ตใน docker-compose
```

---

## 📚 เอกสารที่เกี่ยวข้อง

- **[START_UBUNTU.md](START_UBUNTU.md)** – เริ่มต้นแบบสั้น
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** – คู่มือ deploy รวม
- **[NGINX_SETUP.md](NGINX_SETUP.md)** – ตั้งค่า Nginx
- **[README.md](README.md)** – ภาพรวมโปรเจค
