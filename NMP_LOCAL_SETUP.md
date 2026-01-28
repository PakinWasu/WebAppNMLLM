# ✅ Domain nmp.local Setup Complete!

## สิ่งที่ทำเสร็จแล้ว

1. ✅ อัปเดต `frontend/nginx.conf` ให้รองรับ `nmp.local`
2. ✅ Rebuild frontend container
3. ✅ Restart frontend container

## สิ่งที่ต้องทำต่อ (ต้องใช้ sudo)

### 1. ตั้งค่า nginx บน host

รันคำสั่งนี้:

```bash
sudo bash setup-nmp-local-nginx.sh
```

หรือรันคำสั่งนี้:

```bash
sudo bash scripts/ubuntu/setup-domain-complete.sh nmp.local
```

### 2. ตั้งค่า DNS (บนเครื่อง client)

#### สำหรับ Windows:
แก้ไขไฟล์: `C:\Windows\System32\drivers\etc\hosts`

เพิ่มบรรทัด:
```
10.4.15.167    nmp.local
10.4.15.167    www.nmp.local
```

#### สำหรับ Linux/Mac:
แก้ไขไฟล์: `/etc/hosts`

เพิ่มบรรทัด:
```
10.4.15.167    nmp.local
10.4.15.167    www.nmp.local
```

**หมายเหตุ:** ต้องใช้ sudo/administrator privileges

### 3. ทดสอบ

หลังจากตั้งค่า DNS แล้ว:

```bash
# ทดสอบ DNS resolution
ping nmp.local

# ทดสอบ access
curl http://nmp.local
```

หรือเปิด browser และไปที่: **http://nmp.local**

## สรุป

- ✅ Frontend container: ตั้งค่า domain แล้ว
- ⏳ Nginx บน host: ต้องรัน `sudo bash setup-nmp-local-nginx.sh`
- ⏳ DNS: ต้องแก้ไข `/etc/hosts` บนเครื่อง client

## การเข้าถึง

หลังจากตั้งค่าทั้งหมดแล้ว:

- **Frontend**: http://nmp.local
- **Backend API**: http://nmp.local/docs
- **Backend API (direct)**: http://10.4.15.167:8000/docs

## คำสั่งที่ใช้บ่อย

```bash
# ตรวจสอบสถานะ
docker compose -f docker-compose.prod.yml ps

# ดู logs
docker compose -f docker-compose.prod.yml logs -f frontend

# Restart frontend
docker compose -f docker-compose.prod.yml restart frontend
```
