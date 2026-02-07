# การใช้งานโปรเจคด้วย nmp.local

คู่มือตั้งค่าให้เปิดแอปผ่าน **http://nmp.local** (Nginx บน port 80 + DNS ชื่อ nmp.local)

---

## วิธีที่ 1: ใช้สคริปต์เดียว (แนะนำ)

```bash
cd /path/to/WebAppNMLLM
chmod +x start-nmp-local.sh
./start-nmp-local.sh
```

จากนั้นตั้งค่า Nginx และ DNS (รันด้วย sudo):

```bash
sudo ./setup-nmp-local-nginx.sh
sudo ./setup-hosts-linux.sh 127.0.0.1
```

- **เข้าจากเครื่องเดียว (localhost):** ใช้ `127.0.0.1` ดังด้านบน
- **เข้าจากเครื่องอื่นใน LAN:** ใช้ IP ของเครื่องที่รันแอป เช่น  
  `sudo ./setup-hosts-linux.sh 192.168.1.100`  
  แล้วบนเครื่อง client แก้ไฟล์ hosts ให้ชี้ `nmp.local` ไปที่ IP นั้น

เปิดเบราว์เซอร์: **http://nmp.local**  
Login: **admin** / **admin123**

---

## วิธีที่ 2: ทำทีละขั้น

### 1. เตรียม .env และ start แอป

```bash
# สร้าง .env ถ้ายังไม่มี (ใช้ Ollama ใน Docker)
cp backend/.env.example backend/.env
# แก้ JWT_SECRET และ OLLAMA_BASE_URL=http://ollama:11434

# Start services
docker compose -f docker-compose.prod.yml up -d --build
```

### 2. ตั้งค่า Nginx บน host (port 80 สำหรับ nmp.local)

```bash
sudo ./setup-nmp-local-nginx.sh
```

สคริปต์จะ:
- ติดตั้ง nginx ถ้ายังไม่มี
- สร้าง config ที่ `/etc/nginx/sites-available/mnp`
- proxy ไปที่ frontend (127.0.0.1:8080) และ backend (127.0.0.1:8000)

### 3. ตั้งค่า DNS (hosts) ให้ nmp.local

**Linux / Mac (บนเครื่องที่รันแอป หรือเครื่อง client):**

```bash
sudo ./setup-hosts-linux.sh 127.0.0.1
```

หรือแก้ `/etc/hosts` เอง:

```
127.0.0.1    nmp.local
127.0.0.1    www.nmp.local
```

**Windows (บนเครื่อง client):**

แก้ไข `C:\Windows\System32\drivers\etc\hosts` (ต้อง Run as Administrator):

```
<IP ของเครื่องที่รันแอป>    nmp.local
<IP ของเครื่องที่รันแอป>    www.nmp.local
```

ถ้าเข้าจากเครื่องเดียวใช้ `127.0.0.1`

### 4. ทดสอบ

```bash
ping nmp.local
curl -s -o /dev/null -w "%{http_code}" http://nmp.local
```

เปิดเบราว์เซอร์: **http://nmp.local**

---

## สรุปพอร์ตและ URL

| บริการ    | พอร์ต (Docker) | ผ่าน Nginx (nmp.local)   |
|-----------|----------------|---------------------------|
| Frontend  | 8080           | http://nmp.local/         |
| Backend   | 8001 (ถ้า 8000 ถูกใช้) | http://nmp.local/docs     |
| Login     | -              | http://nmp.local → admin / admin123 |

---

## คำสั่งที่ใช้บ่อย

```bash
# ตรวจสอบสถานะ
docker compose -f docker-compose.prod.yml ps

# ดู logs
docker compose -f docker-compose.prod.yml logs -f

# Restart แอป
docker compose -f docker-compose.prod.yml restart

# ทดสอบ Nginx
sudo nginx -t
sudo systemctl reload nginx
```

---

## แก้ปัญหา

### 502 Bad Gateway
- ตรวจว่า backend และ frontend ทำงาน:  
  `docker compose -f docker-compose.prod.yml ps`
- โปรเจคนี้ใช้ backend พอร์ต **8001** บน host (ถ้า 8000 ถูกใช้แล้ว) — ต้องให้ Nginx proxy API ไปที่ `127.0.0.1:8001`  
  รันใหม่: `sudo ./setup-nmp-local-nginx.sh` แล้ว `sudo systemctl reload nginx`
- ตรวจว่า port 8080 และ 8001 ตอบ:  
  `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080` และ `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/`

### nmp.local ไม่เปิด
- ตรวจ hosts: `grep nmp.local /etc/hosts` (Linux/Mac) หรือดูไฟล์ hosts บน Windows
- ตรวจ Nginx: `sudo nginx -t` และ `sudo systemctl status nginx`

### ใช้ได้แค่ localhost:8080
- ต้องรัน `sudo ./setup-nmp-local-nginx.sh` และ `sudo ./setup-hosts-linux.sh 127.0.0.1` ให้ครบ
