# Topology LLM Debug Guide

## วิธีทดสอบ LLM Topology Generation ทีละขั้นตอน

### ขั้นตอนที่ 1: ทดสอบ LLM Connection (ผ่าน API)

1. **Login เพื่อรับ Token:**
   ```bash
   curl -X POST "http://10.4.15.167:8000/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "admin123"}'
   ```
   
   คัดลอก `access_token` จาก response

2. **ทดสอบ LLM Connection:**
   ```bash
   curl -X POST "http://10.4.15.167:8000/topology/test-llm" \
     -H "Authorization: Bearer YOUR_TOKEN_HERE" \
     -H "Content-Type: application/json"
   ```

   Endpoint นี้จะทดสอบ:
   - ✅ Ollama connectivity
   - ✅ Model availability (`qwen2.5-coder:14b`)
   - ✅ Simple LLM call
   - ✅ Topology LLM with sample data

3. **ดูผลลัพธ์:**
   - `ollama_accessible`: true/false
   - `model_available`: true/false
   - `simple_call_works`: true/false
   - `topology_call_works`: true/false
   - `errors`: [] (รายการ errors ถ้ามี)

### ขั้นตอนที่ 2: ทดสอบ Generate Topology (จริง)

1. **Generate Topology สำหรับ Project:**
   ```bash
   curl -X POST "http://10.4.15.167:8000/projects/YOUR_PROJECT_ID/topology/generate" \
     -H "Authorization: Bearer YOUR_TOKEN_HERE" \
     -H "Content-Type: application/json"
   ```

2. **ดู Logs จาก Backend Container:**
   ```bash
   sudo docker logs backend --tail 100 | grep -E "Topology|Ollama|ERROR|Error"
   ```

### ขั้นตอนที่ 3: ตรวจสอบปัญหา

#### ปัญหา: `ollama_accessible: false`
**สาเหตุ:** Ollama container ไม่ทำงานหรือไม่สามารถเชื่อมต่อได้

**แก้ไข:**
```bash
# ตรวจสอบว่า Ollama container ทำงานอยู่หรือไม่
sudo docker ps | grep ollama

# ถ้าไม่ทำงาน ให้ start
sudo docker-compose up -d ollama

# ตรวจสอบ logs
sudo docker logs ollama --tail 50
```

#### ปัญหา: `model_available: false`
**สาเหตุ:** Model `qwen2.5-coder:14b` ยังไม่ได้ pull

**แก้ไข:**
```bash
# Pull model
sudo docker exec ollama ollama pull qwen2.5-coder:14b

# ตรวจสอบว่า pull สำเร็จ
sudo docker exec ollama ollama list
```

#### ปัญหา: `simple_call_works: false` หรือ "Simple LLM call timeout"
**สาเหตุ:** Ollama มี **server-side timeout ~60 วินาที** (hardcoded) — ถ้าโมเดลตอบช้ากว่า 60s จะได้ HTTP 500

**แก้ไข (แนะนำ):**
1. **ใช้โมเดล 14b แทน 32b** — 14b เร็วกว่าและมักตอบทันภายใน 60s บน CPU  
   ตรวจสอบ `backend/.env`:
   ```bash
   grep AI_MODEL_NAME backend/.env
   ```
   ควรเป็น `AI_MODEL_NAME=qwen2.5-coder:14b` (ไม่ใช่ 32b)

2. **Pre-load โมเดล 14b** ก่อนทดสอบ (เพื่อไม่ให้รอ load ครั้งแรกเกิน 60s):
   ```bash
   sudo docker exec mnp-ollama ollama run qwen2.5-coder:14b "hello"
   ```
   รอจนตอบกลับ แล้วค่อยยิง test-llm อีกครั้ง

3. **Restart backend** หลังแก้ .env:
   ```bash
   sudo docker compose restart backend
   ```

**ตรวจสอบเพิ่มเติม:**
- ดู `errors` array ใน response
- ตรวจสอบ logs: `sudo docker logs mnp-backend --tail 50`
- ตรวจสอบ resources: `sudo docker stats mnp-ollama`

#### ปัญหา: `topology_call_works: false`
**สาเหตุ:** LLM ไม่สามารถ parse JSON หรือ return structure ไม่ถูกต้อง

**ตรวจสอบ:**
- ดู `errors` array และ `raw_response` ใน response
- ตรวจสอบว่า LLM return JSON format ถูกต้องหรือไม่

### ขั้นตอนที่ 4: ทดสอบผ่าน Swagger UI

1. เปิด Swagger UI: `http://10.4.15.167:8000/docs`

2. **Authorize:**
   - คลิกปุ่ม "Authorize" (🔒)
   - ใส่ token (ไม่ต้องใส่ "Bearer " นำหน้า)
   - คลิก "Authorize" แล้ว "Close"

3. **ทดสอบ `/topology/test-llm`:**
   - หา endpoint `POST /topology/test-llm`
   - คลิก "Try it out"
   - คลิก "Execute"
   - ดูผลลัพธ์

4. **ทดสอบ `/projects/{project_id}/topology/generate`:**
   - หา endpoint `POST /projects/{project_id}/topology/generate`
   - ใส่ `project_id` ที่ต้องการ
   - คลิก "Try it out" แล้ว "Execute"
   - ดูผลลัพธ์และ errors (ถ้ามี)

### ขั้นตอนที่ 5: ตรวจสอบ Backend Logs

```bash
# ดู logs ทั้งหมด
sudo docker logs backend --tail 200

# กรองเฉพาะ Topology-related logs
sudo docker logs backend --tail 200 | grep -i topology

# กรองเฉพาะ Ollama-related logs
sudo docker logs backend --tail 200 | grep -i ollama

# กรองเฉพาะ Errors
sudo docker logs backend --tail 200 | grep -i error
```

### ขั้นตอนที่ 6: ตรวจสอบ Ollama Logs

```bash
# ดู logs ของ Ollama
sudo docker logs ollama --tail 100

# ตรวจสอบว่า model ถูก load หรือไม่
sudo docker exec ollama ollama list

# ทดสอบ Ollama โดยตรง
sudo docker exec ollama ollama run qwen2.5-coder:14b "Say hello"
```

## สรุป Checklist

- [ ] Ollama container ทำงานอยู่
- [ ] Model `qwen2.5-coder:14b` ถูก pull แล้ว
- [ ] `/topology/test-llm` endpoint ทำงานได้
- [ ] `ollama_accessible: true`
- [ ] `model_available: true`
- [ ] `simple_call_works: true`
- [ ] `topology_call_works: true`
- [ ] `/projects/{project_id}/topology/generate` ทำงานได้
- [ ] Topology result ถูกบันทึกใน MongoDB

## Troubleshooting Tips

1. **ถ้า timeout:** ลด `num_predict` ใน `topology_service.py` หรือเพิ่ม timeout
2. **ถ้า JSON parse error:** ตรวจสอบว่า LLM return format ถูกต้อง (ดู `raw_response`)
3. **ถ้า connection error:** ตรวจสอบ network connectivity ระหว่าง backend และ ollama containers
4. **ถ้า model not found:** Pull model อีกครั้ง: `sudo docker exec ollama ollama pull qwen2.5-coder:14b`

## ข้อมูลเพิ่มเติม

- Backend logs: `sudo docker logs backend`
- Ollama logs: `sudo docker logs ollama`
- MongoDB: ตรวจสอบ `parsed_configs` collection ว่ามีข้อมูล devices และ neighbors หรือไม่
