# การตั้งค่า /etc/hosts สำหรับ Domain Name

เมื่อใช้ domain name (เช่น `mnp.local`) แทน IP address ต้องตั้งค่า DNS resolution บนเครื่อง client

## 🔧 วิธีตั้งค่า

### วิธีที่ 1: ใช้ Script (แนะนำ - ง่ายที่สุด)

#### Windows

1. **คลิกขวาที่ไฟล์** `setup-hosts-windows.bat`
2. เลือก **"Run as administrator"**
3. Script จะตั้งค่าให้อัตโนมัติ

หรือรันจาก Command Prompt (as Administrator):
```cmd
cd path\to\manage-network-project
setup-hosts-windows.bat
```

#### Linux / Mac

```bash
# รัน script (จะถาม password)
sudo ./setup-hosts-linux.sh

# หรือระบุ IP address
sudo ./setup-hosts-linux.sh 10.4.15.53
```

### วิธีที่ 2: แก้ไขด้วยตนเอง

#### Windows

1. เปิด Notepad **ในฐานะ Administrator**:
   - คลิกขวาที่ Notepad → "Run as administrator"

2. เปิดไฟล์ hosts:
   - File → Open
   - ไปที่: `C:\Windows\System32\drivers\etc\hosts`
   - เปลี่ยน "Text Documents (*.txt)" เป็น "All Files (*.*)"

3. เพิ่มบรรทัดนี้ (เปลี่ยน IP เป็น IP ของ server):
   ```
   10.4.15.53    mnp.local
   10.4.15.53    www.mnp.local
   ```

4. Save ไฟล์

5. Clear DNS cache:
   ```cmd
   ipconfig /flushdns
   ```

#### Linux / Mac

1. แก้ไขไฟล์ hosts:
   ```bash
   sudo nano /etc/hosts
   # หรือ
   sudo vi /etc/hosts
   ```

2. เพิ่มบรรทัดนี้ (เปลี่ยน IP เป็น IP ของ server):
   ```
   10.4.15.53    mnp.local
   10.4.15.53    www.mnp.local
   ```

3. Save (Ctrl+O, Enter, Ctrl+X สำหรับ nano)

4. Clear DNS cache (ถ้าจำเป็น):
   ```bash
   # Linux
   sudo systemd-resolve --flush-caches
   # หรือ
   sudo resolvectl flush-caches
   
   # Mac
   sudo dscacheutil -flushcache
   sudo killall -HUP mDNSResponder
   ```

## ✅ ตรวจสอบ

### ทดสอบ DNS Resolution

**Windows:**
```cmd
ping mnp.local
nslookup mnp.local
```

**Linux/Mac:**
```bash
ping mnp.local
nslookup mnp.local
# หรือ
host mnp.local
```

ควรแสดง IP address: `10.4.15.53`

### ทดสอบใน Browser

1. เปิด browser
2. ไปที่: `http://mnp.local`
3. ควรเข้าถึงได้

## 🔍 การแก้ไขปัญหา

### ยังเข้าไม่ได้หลังจากตั้งค่า hosts

1. **ตรวจสอบ hosts file:**
   ```bash
   # Linux/Mac
   cat /etc/hosts | grep mnp.local
   
   # Windows
   type C:\Windows\System32\drivers\etc\hosts | findstr mnp.local
   ```

2. **Clear browser cache:**
   - Chrome: Ctrl+Shift+Delete → Clear browsing data
   - หรือเปิด Incognito/Private window

3. **Restart browser** หลังจากแก้ไข hosts file

4. **ตรวจสอบ IP address ของ server:**
   ```bash
   # บน server
   hostname -I
   ```

5. **ทดสอบด้วย curl:**
   ```bash
   curl http://mnp.local
   ```

### Error: "DNS_PROBE_FINISHED_NXDOMAIN"

หมายความว่า DNS ไม่สามารถ resolve domain ได้

**แก้ไข:**
1. ตรวจสอบว่า hosts file ถูกแก้ไขถูกต้อง
2. Clear DNS cache
3. Restart browser
4. ลองใช้ IP address ก่อน: `http://10.4.15.53`

### Error: "This site can't be reached"

**ตรวจสอบ:**
1. Services ทำงานอยู่:
   ```bash
   docker compose -f docker-compose.prod.yml ps
   ```

2. Firewall อนุญาต port 80:
   ```bash
   sudo ufw status
   ```

3. Frontend container ทำงาน:
   ```bash
   docker compose -f docker-compose.prod.yml logs frontend
   ```

## 📝 หมายเหตุ

- **IP Address ของ server**: `10.4.15.53` (ตรวจสอบด้วย `hostname -I`)
- **Domain Name**: `mnp.local` (สามารถเปลี่ยนเป็นชื่ออื่นได้)
- **ต้องตั้งค่า hosts file บนทุกเครื่อง client** ที่ต้องการเข้าถึง
- สำหรับ Internet (public domain) ต้องตั้งค่า DNS records ที่ domain registrar

## 🔄 เปลี่ยน Domain Name

ถ้าต้องการเปลี่ยน domain name:

1. แก้ไข nginx.conf:
   ```bash
   # แก้ไข frontend/nginx.conf
   # เปลี่ยน server_name _; เป็น server_name newdomain.local _;
   ```

2. Rebuild frontend:
   ```bash
   docker compose -f docker-compose.prod.yml build frontend
   docker compose -f docker-compose.prod.yml up -d frontend
   ```

3. อัปเดต hosts file บนทุกเครื่อง client

