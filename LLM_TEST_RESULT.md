# ผลการตรวจสอบและทดสอบ LLM (ล่าสุด)

## 1) การตรวจสอบ

- **backend/.env เดิม**: มีช่องว่างนำหน้า `OLLAMA_BASE_URL` / `OLLAMA_MODEL` และยังอ้างถึง `ollama:11434` + `qwen2.5-coder:14b`
- **Backend ที่รันอยู่**: ยังใช้ env เก่า (ต้อง restart จึงโหลด .env ใหม่)

## 2) การแก้ไข

- ลบช่องว่างนำหน้าใน `backend/.env` และตั้งค่าให้ชี้ไปที่ Ollama บน Windows:
  - `OLLAMA_BASE_URL=http://10.4.15.152:11434`
  - `OLLAMA_MODEL=deepseek-coder-v2:16b`
  - `OLLAMA_TIMEOUT=300`
  - `TOPOLOGY_USE_LLM=true`

## 3) ผลการทดสอบ

### 3.1 เชื่อมต่อ Ollama ที่ 10.4.15.152

- **ผล**: เชื่อมต่อได้
- **โมเดลที่ติดตั้งบนเซิร์ฟเวอร์**: `qwen2.5-coder:7b`, `deepseek-coder-v2:16b`, `qwen2.5-coder:14b`

### 3.2 ทดสอบยิง "Hello" ไปที่โมเดล (โดยตรงที่ 10.4.15.152)

| โมเดล | ผล |
|--------|-----|
| deepseek-coder-v2:16b | Error: โมเดลต้องการ 9.2 GiB RAM แต่มีแค่ 2.4 GiB |
| qwen2.5-coder:7b | Error: โมเดลต้องการ 4.3 GiB RAM แต่มีแค่ 2.3 GiB |

**สรุป**: เครื่อง Windows (10.4.15.152) มี RAM ไม่พอให้โหลดโมเดลที่ใช้อยู่

## 4) สิ่งที่คุณทำได้

1. **เพิ่ม RAM** ที่เครื่อง Windows ที่รัน Ollama (อย่างน้อย 8–10 GB ถ้าจะใช้ 7b, 16–20 GB ถ้าจะใช้ 16b)
2. **ปิดแอปอื่น** บนเครื่องนั้นเพื่อปล่อย RAM ให้ Ollama
3. **ใช้โมเดลที่เล็กกว่า** ถ้ามี (เช่น tinyllama) ที่ใช้ RAM น้อยกว่า 2.4 GiB
4. **ย้าย Ollama ไปรันบนเครื่องอื่น** ที่มี RAM เพียงพอ

## 5) หลังแก้ RAM / โมเดล แล้ว

1. Restart backend ให้โหลด .env ใหม่:
   ```bash
   ./update-and-restart.sh
   ```
2. ทดสอบสถานะและยิง Hello:
   ```bash
   ./check-llm-status.sh
   ```
   หรือ:
   ```bash
   curl -s http://localhost:8000/health/llm | python3 -m json.tool
   curl -s --max-time 120 "http://localhost:8000/ai/hello" | python3 -m json.tool
   ```
