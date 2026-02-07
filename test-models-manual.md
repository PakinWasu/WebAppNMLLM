# คู่มือการทดสอบ Model ต่างๆ ใน Ollama

## ขั้นตอนการทดสอบ Model

### 1. ตรวจสอบ Model ที่มีใน Ollama Server

```bash
curl -s http://10.4.15.52:11434/api/tags | python3 -m json.tool
```

หรือใช้ script:
```bash
./test-models-simple.sh
```

### 2. ทดสอบ Model แต่ละตัว

#### วิธีที่ 1: ใช้ Script อัตโนมัติ (แนะนำ)

```bash
# ทดสอบผ่าน API endpoints
./test-models-api.sh
```

#### วิธีที่ 2: ทดสอบด้วยตนเอง

สำหรับแต่ละ model:

1. **อัปเดต backend/.env:**
   ```bash
   # แก้ไข OLLAMA_MODEL ใน backend/.env
   OLLAMA_MODEL=deepseek-r1:7b  # หรือ model อื่นที่ต้องการทดสอบ
   ```

2. **Restart backend:**
   ```bash
   docker compose -f docker-compose.prod.yml restart backend
   ```

3. **ทดสอบใน UI:**
   - เปิดหน้า Summary ของ project ที่มี devices
   - กดปุ่ม "LLM Analysis" ในส่วน Network Overview
   - กดปุ่ม "LLM Analysis" ในส่วน Recommendations
   - บันทึกเวลาและผลลัพธ์

4. **เปรียบเทียบผลลัพธ์:**
   - เวลาที่ใช้ในการ generate
   - คุณภาพของผลลัพธ์ (overview text, recommendations)
   - จำนวน tokens ที่ใช้
   - ความถูกต้องของผลลัพธ์

### 3. Model ที่มีในระบบ

จาก Ollama server ที่ `http://10.4.15.52:11434`:

- **deepseek-r1:7b** (ปัจจุบันใช้อยู่)
- **qwen2.5:7b**
- **llama3.1:latest**

### 4. เกณฑ์การเปรียบเทียบ

1. **ความเร็ว (Speed)**
   - เวลาที่ใช้ในการ generate overview
   - เวลาที่ใช้ในการ generate recommendations
   - Average time = (overview_time + recommendations_time) / 2

2. **คุณภาพ (Quality)**
   - ความถูกต้องของผลลัพธ์
   - ความละเอียดของ overview
   - จำนวนและคุณภาพของ recommendations

3. **ประสิทธิภาพ (Efficiency)**
   - จำนวน tokens ที่ใช้
   - Memory usage
   - CPU usage

### 5. แนะนำ Model ที่ดีที่สุด

หลังจากทดสอบแล้ว ให้อัปเดต `backend/.env`:

```env
OLLAMA_MODEL=<best_model_name>
```

แล้ว restart backend:
```bash
docker compose -f docker-compose.prod.yml restart backend
```

### 6. สคริปต์สำหรับทดสอบแบบละเอียด

ใช้ Python script สำหรับทดสอบแบบละเอียด:

```bash
# รันจากใน backend container
docker compose -f docker-compose.prod.yml exec backend python3 /app/scripts/test_models.py
```

หรือรันจาก host (ต้องมี dependencies):
```bash
cd backend
python3 scripts/test_models.py
```

### หมายเหตุ

- การทดสอบแต่ละ model อาจใช้เวลานาน (1-2 นาทีต่อ task)
- แนะนำให้ทดสอบในช่วงเวลาที่ไม่มีการใช้งานจริง
- บันทึกผลลัพธ์เพื่อเปรียบเทียบ
