# 🚀 การตั้งค่า Domain Name - คู่มือฉบับย่อ

## ⚡ Quick Fix - แก้ไขทันที

### บนเครื่อง Client (เครื่องที่เปิด browser)

#### Windows:
1. คลิกขวา `setup-hosts-windows.bat` → **Run as administrator**
2. หรือแก้ไข `C:\Windows\System32\drivers\etc\hosts` ด้วยตนเอง:
   ```
   10.4.15.53    mnp.local
   ```
3. รัน: `ipconfig /flushdns`

#### Linux/Mac:
```bash
sudo ./setup-hosts-linux.sh
# หรือ
sudo nano /etc/hosts
# เพิ่ม: 10.4.15.53    mnp.local
```

### บน Server (ถ้ายังไม่ได้ตั้งค่า domain ใน nginx)

```bash
# ตั้งค่า domain ใน nginx
./setup-domain.sh mnp.local

# Rebuild frontend
docker compose -f docker-compose.prod.yml build frontend
docker compose -f docker-compose.prod.yml up -d frontend
```

## 📋 Checklist

- [ ] ตั้งค่า hosts file บนเครื่อง client (Windows/Linux/Mac)
- [ ] Clear DNS cache
- [ ] Restart browser
- [ ] ทดสอบ: `http://mnp.local`

## 🔍 ตรวจสอบ

### ทดสอบ DNS Resolution

**Windows:**
```cmd
ping mnp.local
# ควรแสดง: Pinging mnp.local [10.4.15.53]
```

**Linux/Mac:**
```bash
ping mnp.local
# ควรแสดง: PING mnp.local (10.4.15.53)
```

### ทดสอบใน Browser

1. เปิด browser ใหม่ (หรือ Incognito/Private window)
2. ไปที่: `http://mnp.local`
3. ควรเข้าถึงได้

## ⚠️ สิ่งสำคัญ

1. **ต้องตั้งค่า hosts file บนทุกเครื่อง client** ที่ต้องการเข้าถึง
2. **Server IP**: `10.4.15.53` (ตรวจสอบด้วย `hostname -I` บน server)
3. **Domain Name**: `mnp.local` (สามารถเปลี่ยนได้)
4. **Clear browser cache** หลังจากแก้ไข hosts file

## 📚 เอกสารเพิ่มเติม

- `SETUP_HOSTS.md` - คู่มือละเอียด
- `DOMAIN_SETUP.md` - การตั้งค่า domain แบบละเอียด
- `QUICK_START.md` - คู่มือเริ่มต้นใช้งาน

