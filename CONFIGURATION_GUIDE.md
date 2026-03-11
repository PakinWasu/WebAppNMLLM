# คู่มือการตั้งค่า WebAppNMLLM (รายละเอียดทั้งหมด)

## 📋 จุดตั้งค่าที่สำคัญทั้งหมด

### 1. ไฟล์ `backend/.env` - คอนฟิกหลักของระบบ

```env
# ========================================
# MongoDB Configuration
# ========================================
MONGODB_URI=mongodb://mongodb:27017
MONGODB_DB_NAME=manage_network_projects

# จุดสำคัญ:
# - ถ้า MongoDB อยู่บนเครื่องอื่น: MONGODB_URI=mongodb://IP_ADDRESS:27017
# - ถ้ามี authentication: MONGODB_URI=mongodb://user:pass@host:27017/db
# - ถ้าใช้ MongoDB Atlas: MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/db

# ========================================
# JWT Security Configuration (สำคัญมาก!)
# ========================================
JWT_SECRET=your-very-secure-random-secret-key-minimum-32-characters
JWT_ALG=HS256
ACCESS_TOKEN_EXPIRE_MIN=1440

# จุดสำคัญ:
# - JWT_SECRET ต้องเปลี่ยนเป็นค่าสุ่มที่ปลอดภัยใน production
# - สร้างด้วย: openssl rand -hex 32
# - ความยาวอย่างน้อย 32 ตัวอักษร
# - อย่าใช้ค่า default "change_me"

# ========================================
# Ollama LLM Configuration
# ========================================
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT=600

# จุดสำคัญ:
# - OLLAMA_BASE_URL: 
#   * ใน Docker: http://ollama:11434
#   * บน host: http://localhost:11434
#   * บน server อื่น: http://IP_ADDRESS:11434
# - OLLAMA_MODEL: 
#   * qwen2.5:7b (เร็ว, RAM 4-6GB)
#   * qwen2.5:14b (คุณภาพดี, RAM 8-10GB)
#   * qwen2.5:32b (คุณภาพสูง, RAM 16-20GB)
# - OLLAMA_TIMEOUT: เวลาหมดอายุ (วินาที)

# ========================================
# Topology Generation Configuration
# ========================================
TOPOLOGY_USE_LLM=true

# จุดสำคัญ:
# - true: ใช้ LLM ช่วยสร้าง topology (แม่นยำกว่า)
# - false: ใช้ rule-based เท่านั้น (เร็วกว่า)
```

### 2. ไฟล์ `docker-compose.prod.yml` - คอนฟิก Docker

#### 2.1 Port Configuration
```yaml
services:
  frontend:
    ports:
      - "8080:80"    # Frontend port (เปลี่ยนได้)
  backend:
    ports:
      - "8001:8000"  # Backend port (เปลี่ยนได้)
  mongodb:
    ports:
      - "27017:27017" # MongoDB port (เปลี่ยนได้)
  ollama:
    ports:
      - "11434:11434" # Ollama port (ไม่ควรเปลี่ยน)
```

#### 2.2 Resource Limits (Ollama)
```yaml
services:
  ollama:
    deploy:
      resources:
        limits:
          memory: 20G  # ปรับตามโมเดล
          cpus: '4'    # ปรับตาม CPU
```

**จุดสำคัญ:**
- **Memory**: ต้องเพียงพอสำหรับโมเดลที่เลือก
- **CPU**: 4 cores ขั้นต่ำ, 8 cores แนะนำ
- **GPU**: ถ้ามี NVIDIA GPU สามารถเปิดได้

#### 2.3 Volume Configuration
```yaml
services:
  backend:
    volumes:
      - ./storage:/app/storage  # ไฟล์อัปโหลด
  mongodb:
    volumes:
      - ./mongo-data:/data/db      # ข้อมูล MongoDB
      - ./mongo-backup:/backup     # Backup MongoDB
  ollama:
    volumes:
      - ollama-data:/root/.ollama  # โมเดล LLM
```

### 3. ไฟล์ `backend/app/core/settings.py` - คอนฟิก Python

```python
class Settings(BaseSettings):
    # MongoDB
    MONGODB_URI: str = "mongodb://mongodb:27017"
    MONGODB_DB_NAME: str = "manage_network_projects"
    
    # AI Model
    AI_MODEL_NAME: str = "qwen2.5:7b"
    AI_MODEL_ENDPOINT: str = "http://ollama:11434"
    
    # JWT
    JWT_SECRET: str = "change_me"
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MIN: int = 60 * 24
    
    # Temp Password Encryption
    TEMP_PASSWORD_ENCRYPTION_KEY: str = "change_me_temp_pwd_key"
```

**จุดสำคัญ:**
- ค่าเหล่านี้ถูก override โดย environment variables (.env)
- TEMP_PASSWORD_ENCRYPTION_KEY ควรเปลี่ยนใน production

### 4. ไฟล์ `frontend/src/api.js` - API Configuration

```javascript
const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? 'http://localhost:8001' 
  : 'http://localhost:8000';
```

**จุดสำคัญ:**
- ต้องตรงกับ backend port ที่ตั้งค่าใน docker-compose
- ถ้าเปลี่ยน backend port ต้องอัปเดตที่นี่ด้วย

## 🔧 การแก้ไขการตั้งค่าแต่ละส่วน

### 1. เปลี่ยน MongoDB Connection

**วิธีที่ 1: แก้ไฟล์ .env**
```env
MONGODB_URI=mongodb://new-host:27017
MONGODB_DB_NAME=new_database_name
```

**วิธีที่ 2: ใช้ MongoDB Atlas**
```env
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/your_db
```

**วิธีที่ 3: ใช้ Authentication**
```env
MONGODB_URI=mongodb://admin:password@mongodb:27017/your_db?authSource=admin
```

### 2. เปลี่ยน LLM Model

**แก้ไฟล์ .env:**
```env
OLLAMA_MODEL=qwen2.5:14b
```

**ดาวน์โหลดโมเดลใหม่:**
```bash
docker compose -f docker-compose.prod.yml exec ollama ollama pull qwen2.5:14b
```

**ปรับ resource limits (ถ้าจำเป็น):**
```yaml
# ใน docker-compose.prod.yml
deploy:
  resources:
    limits:
      memory: 32G  # เพิ่มสำหรับ 14b model
      cpus: '8'    # เพิ่ม CPU
```

### 3. เปลี่ยน Ports

**Frontend Port:**
```yaml
# docker-compose.prod.yml
services:
  frontend:
    ports:
      - "8081:80"  # เปลี่ยนจาก 8080
```

**Backend Port:**
```yaml
# docker-compose.prod.yml
services:
  backend:
    ports:
      - "8002:8000"  # เปลี่ยนจาก 8001
```

**อัปเดต frontend API URL:**
```javascript
// frontend/src/api.js
const API_BASE_URL = 'http://localhost:8002';  // เปลี่ยนตาม backend port
```

### 4. เปลี่ยน Resource Limits

**เพิ่ม Memory:**
```yaml
# docker-compose.prod.yml
services:
  ollama:
    deploy:
      resources:
        limits:
          memory: 32G  # เพิ่มจาก 20G
```

**เพิ่ม CPU:**
```yaml
services:
  ollama:
    deploy:
      resources:
        limits:
          cpus: '8'    # เพิ่มจาก 4
```

### 5. เปิดใช้ GPU

**ตรวจสอบ NVIDIA Docker:**
```bash
# ติดตั้ง nvidia-docker2
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

**แก้ไฟล์ docker-compose.prod.yml:**
```yaml
services:
  ollama:
    deploy:
      reservations:
        devices:
          - driver: nvidia
            count: all
            capabilities: [ "gpu" ]
```

### 6. เปลี่ยน Timezone

**Backend:**
```yaml
# docker-compose.prod.yml
services:
  backend:
    environment:
      - TZ=Asia/Bangkok
```

**MongoDB:**
```yaml
services:
  mongodb:
    environment:
      - TZ=Asia/Bangkok
```

### 7. ตั้งค่า SSL/HTTPS

**วิธีที่ 1: ใช้ Nginx Reverse Proxy**
```yaml
# docker-compose.ssl.yml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
```

**วิธีที่ 2: ใช้ Traefik**
```yaml
# docker-compose.traefik.yml
services:
  traefik:
    image: traefik:v2.10
    ports:
      - "443:443"
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--entrypoints.websecure.address=:443"
```

## 🚨 จุดที่ต้องตรวจสอบอย่างละเอียด

### 1. Security Configuration

**JWT Secret:**
```bash
# ตรวจสอบว่าไม่ใช่ค่า default
grep JWT_SECRET backend/.env

# ถ้าเป็นค่า default ต้องเปลี่ยนทันที
JWT_SECRET=change_me  # ❌ อย่าใช้นี้
JWT_SECRET=abc123def456...  # ✅ ใช้ค่าสุ่ม
```

**Database Connection:**
```bash
# ตรวจสอบว่า MongoDB ไม่โผล่ออกนอก
docker compose -f docker-compose.prod.yml ps mongodb
netstat -tlnp | grep :27017
```

### 2. Resource Allocation

**Memory Usage:**
```bash
# ตรวจสอบการใช้หน่วยความจำ
docker stats mnp-ollama-prod

# ตรวจสอบว่ามีพอสำหรับโมเดล
free -h
```

**CPU Usage:**
```bash
# ตรวจสอบการใช้ CPU
top -p $(pgrep -f ollama)
```

### 3. Network Configuration

**Port Conflicts:**
```bash
# ตรวจสอบ ports ที่ใช้
netstat -tlnp | grep -E ":8080|:8001|:27017|:11434"
```

**Docker Network:**
```bash
# ตรวจสอบ network
docker network ls | grep mnp
docker network inspect mnp-network
```

### 4. File Permissions

**Storage Directory:**
```bash
# ตรวจสอบ permissions
ls -la storage/
ls -la mongo-data/
ls -la mongo-backup/

# แก้ไขถ้าจำเป็น
sudo chmod -R 777 storage/
sudo chown -R $USER:$USER storage/
```

### 5. Service Health

**Backend Health:**
```bash
curl -f http://localhost:8001/ || echo "Backend not responding"
```

**Frontend Health:**
```bash
curl -f http://localhost:8080/ || echo "Frontend not responding"
```

**MongoDB Health:**
```bash
docker compose -f docker-compose.prod.yml exec mongodb mongo --eval "db.adminCommand('ping')"
```

**Ollama Health:**
```bash
curl -f http://localhost:11434/api/tags || echo "Ollama not responding"
```

## 📝 การตรวจสอบหลังการติดตั้ง

### Checklist ก่อนใช้งานจริง

- [ ] JWT_SECRET เปลี่ยนเป็นค่าสุ่มที่ปลอดภัย
- [ ] เปลี่ยนรหัสผ่าน admin ครั้งแรก
- [ ] ตรวจสอบว่า ports ไม่ conflict
- [ ] ตรวจสอบว่า memory เพียงพอสำหรับ LLM
- [ ] ตรวจสอบ file permissions
- [ ] ทดสอบการเชื่อมต่อ MongoDB
- [ ] ทดสอบการเชื่อมต่อ Ollama
- [ ] ดาวน์โหลด LLM model สำเร็จ
- [ ] ทดสอบ login สำเร็จ
- [ ] ทดสอบสร้างโปรเจคใหม่
- [ ] ทดสอบอัปโหลดไฟล์
- [ ] ทดสอบวิเคราะห์ config
- [ ] ตั้งค่า backup (ถ้าจำเป็น)

---

## 🔗 ข้อมูลเพิ่มเติม

- [คู่มือการติดตั้ง Linux](INSTALL_LINUX.md)
- [README หลัก](README.md)
- [API Documentation](http://localhost:8001/docs)
- [Ollama Documentation](https://github.com/ollama/ollama)

---

**⚠️ คำเตือน**: การตั้งค่าผิดพลาดอาจทำให้ระบบไม่ทำงานหรือมีช่องโหว่ด้านความปลอดภัย กรุณาตรวจสอบอย่างละเอียดก่อนใช้งานจริง
