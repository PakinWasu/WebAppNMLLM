# คู่มือการทดสอบและเปรียบเทียบ Ollama Models

## ภาพรวม

สคริปต์นี้ช่วยให้คุณทดสอบ model ต่างๆ ใน Ollama server และเลือก model ที่ดีที่สุดสำหรับงาน network analysis

## Model ที่มีในระบบ

จาก Ollama server ที่ `http://10.4.15.52:11434`:

- **deepseek-r1:7b** (ปัจจุบันใช้อยู่)
- **qwen2.5:7b**
- **llama3.1:latest**

## วิธีทดสอบ

### วิธีที่ 1: ทดสอบแบบอัตโนมัติ (แนะนำ)

ใช้ script `test-all-models.sh` ที่จะ:
1. เปลี่ยน model ใน backend/.env อัตโนมัติ
2. Restart backend
3. ให้คุณทดสอบใน UI
4. บันทึกผลลัพธ์
5. แนะนำ model ที่ดีที่สุด

```bash
cd /home/nmp/Downloads/WebAppNMLLM
./test-all-models.sh
```

### วิธีที่ 2: ทดสอบด้วยตนเอง

สำหรับแต่ละ model:

1. **อัปเดต backend/.env:**
   ```bash
   # แก้ไข OLLAMA_MODEL
   OLLAMA_MODEL=deepseek-r1:7b  # หรือ model อื่น
   ```

2. **Restart backend:**
   ```bash
   docker compose -f docker-compose.prod.yml restart backend
   ```

3. **ทดสอบใน UI:**
   - เปิดหน้า Summary ของ project ที่มี devices
   - กดปุ่ม "LLM Analysis" ในส่วน Network Overview
   - กดปุ่ม "LLM Analysis" ในส่วน Recommendations
   - บันทึกเวลาและคุณภาพของผลลัพธ์

4. **เปรียบเทียบ:**
   - เวลาที่ใช้ (seconds)
   - คุณภาพของผลลัพธ์ (1-10)
   - ความถูกต้อง
   - ความละเอียด

## เกณฑ์การเปรียบเทียบ

### 1. ความเร็ว (Speed)
- เวลาที่ใช้ในการ generate overview
- เวลาที่ใช้ในการ generate recommendations
- Average time = (overview_time + recommendations_time) / 2

### 2. คุณภาพ (Quality)
- **Overview:**
  - ความถูกต้องของข้อมูล
  - ความละเอียดและครอบคลุม
  - ความชัดเจนและอ่านง่าย
  
- **Recommendations:**
  - จำนวน recommendations ที่มีประโยชน์
  - ความถูกต้องของปัญหา
  - ความชัดเจนของวิธีแก้ไข
  - ความเหมาะสมของ severity level

### 3. คะแนนคุณภาพ (1-10)
- **1-3:** ผลลัพธ์ไม่ดี มีข้อผิดพลาดมาก
- **4-6:** ผลลัพธ์ใช้ได้ แต่ยังมีข้อผิดพลาดบ้าง
- **7-8:** ผลลัพธ์ดี มีข้อผิดพลาดน้อย
- **9-10:** ผลลัพธ์ดีมาก ถูกต้องและละเอียด

## ตัวอย่างการทดสอบ

### Model: deepseek-r1:7b

**Overview:**
- เวลา: 45 seconds
- คุณภาพ: 8/10
- หมายเหตุ: ผลลัพธ์ดี แต่ใช้เวลานาน

**Recommendations:**
- เวลา: 52 seconds
- คุณภาพ: 7/10
- หมายเหตุ: Recommendations ดี แต่บางข้อไม่ชัดเจน

**สรุป:**
- Average time: 48.5s
- Average quality: 7.5/10

### Model: qwen2.5:7b

**Overview:**
- เวลา: 38 seconds
- คุณภาพ: 7/10
- หมายเหตุ: เร็วกว่าแต่คุณภาพต่ำกว่าเล็กน้อย

**Recommendations:**
- เวลา: 41 seconds
- คุณภาพ: 8/10
- หมายเหตุ: Recommendations ดีมาก

**สรุป:**
- Average time: 39.5s
- Average quality: 7.5/10

## การเลือก Model ที่ดีที่สุด

เลือก model ที่มี:
1. **คุณภาพสูงสุด** (Average quality สูงสุด)
2. **ความเร็วเหมาะสม** (ถ้าคุณภาพใกล้เคียงกัน ให้เลือกที่เร็วกว่า)

## อัปเดต Model ที่เลือก

หลังจากเลือก model ที่ดีที่สุดแล้ว:

1. **แก้ไข backend/.env:**
   ```bash
   OLLAMA_MODEL=<best_model_name>
   ```

2. **Restart backend:**
   ```bash
   docker compose -f docker-compose.prod.yml restart backend
   ```

3. **ทดสอบอีกครั้ง** เพื่อยืนยันว่าใช้งานได้ดี

## Tips

- ทดสอบกับ project ที่มี devices หลายตัว (5-10 devices)
- ทดสอบในช่วงเวลาที่ไม่มีการใช้งานจริง
- บันทึกผลลัพธ์เพื่อเปรียบเทียบ
- ทดสอบหลายครั้งเพื่อความแม่นยำ
- ตรวจสอบ logs ถ้ามีปัญหา

## Troubleshooting

### Backend ไม่ restart
```bash
docker compose -f docker-compose.prod.yml restart backend
docker compose -f docker-compose.prod.yml logs backend
```

### Model ไม่ทำงาน
- ตรวจสอบว่า model มีอยู่ใน Ollama server
- ตรวจสอบ logs: `docker compose -f docker-compose.prod.yml logs backend | grep -i error`
- ตรวจสอบ .env file: `cat backend/.env | grep OLLAMA`

### ผลลัพธ์ไม่ดี
- ลอง model อื่น
- ตรวจสอบว่า devices data มีข้อมูลครบถ้วน
- ตรวจสอบ network connectivity ไปยัง Ollama server
