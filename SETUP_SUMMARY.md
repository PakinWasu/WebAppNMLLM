# สรุปการตั้งค่าระบบ Development บน Windows

เอกสารนี้สรุปการตั้งค่าระบบให้สามารถพัฒนาโปรเจคบน Windows PC และ sync ไปยัง Ubuntu Server ผ่าน GitHub

## ✅ สิ่งที่ได้ตั้งค่าแล้ว

### 1. เอกสาร

- ✅ **WINDOWS_DEVELOPMENT.md** - คู่มือการพัฒนาบน Windows PC
- ✅ **GITHUB_WORKFLOW.md** - Workflow การทำงานผ่าน GitHub
- ✅ **QUICK_REFERENCE.md** - Quick reference สำหรับคำสั่งที่ใช้บ่อย
- ✅ **scripts/README.md** - เอกสารสำหรับ scripts

### 2. Scripts

#### Windows (PowerShell)
- ✅ `scripts/windows/dev-start.ps1` - เริ่ม development environment
- ✅ `scripts/windows/git-push.ps1` - Push โค้ดไป GitHub

#### Ubuntu (Bash)
- ✅ `scripts/ubuntu/deploy.sh` - Pull และ deploy บน Ubuntu Server

### 3. Configuration Files

- ✅ `backend/.env.example` - Template สำหรับ environment variables

### 4. Documentation Updates

- ✅ อัปเดต `README.md` เพื่อเพิ่มลิงก์ไปยังเอกสารใหม่

## 🚀 ขั้นตอนต่อไป

### บน Windows PC

1. **ติดตั้ง Tools ที่จำเป็น**
   - Git for Windows
   - Docker Desktop for Windows
   - Visual Studio Code (แนะนำ)

2. **ตั้งค่า Environment Variables**
   ```powershell
   Copy-Item backend\.env.example backend\.env
   # แก้ไข backend\.env
   ```

3. **ทดสอบ Development Environment**
   ```powershell
   .\scripts\windows\dev-start.ps1
   ```

4. **ทดสอบ Git Push**
   ```powershell
   .\scripts\windows\git-push.ps1 -Message "Initial setup"
   ```

### บน Ubuntu Server

1. **Clone หรือ Pull โปรเจค**
   ```bash
   git clone https://github.com/PakinWasu/WebAppNMLLM.git
   # หรือ
   cd /path/to/WebAppNMLLM
   git pull origin main
   ```

2. **ตั้งค่า Environment Variables**
   ```bash
   cp backend/.env.example backend/.env
   nano backend/.env
   ```

3. **ให้ Permission สำหรับ Deploy Script**
   ```bash
   chmod +x scripts/ubuntu/deploy.sh
   ```

4. **ทดสอบ Deploy**
   ```bash
   ./scripts/ubuntu/deploy.sh
   ```

## 📋 Workflow

### การพัฒนา (Windows PC)

```
1. เริ่มทำงาน
   .\scripts\windows\dev-start.ps1

2. พัฒนาโค้ด
   - แก้ไขไฟล์
   - ทดสอบบน localhost

3. Commit และ Push
   .\scripts\windows\git-push.ps1 -Message "Description"
```

### การ Deploy (Ubuntu Server)

```
1. SSH เข้า server
   ssh user@your-server-ip

2. Pull และ Deploy
   cd /path/to/WebAppNMLLM
   ./scripts/ubuntu/deploy.sh
```

## 🔗 Links

- **GitHub Repository**: https://github.com/PakinWasu/WebAppNMLLM
- **เอกสารหลัก**: `README.md`
- **Windows Development**: `WINDOWS_DEVELOPMENT.md`
- **GitHub Workflow**: `GITHUB_WORKFLOW.md`
- **Quick Reference**: `QUICK_REFERENCE.md`

## 📝 หมายเหตุ

- ไฟล์ `.env` ไม่ควร commit ไป GitHub (อยู่ใน `.gitignore` แล้ว)
- ใช้ `.env.example` เป็น template
- Scripts สามารถแก้ไขได้ตามความต้องการ
- ทดสอบ scripts ก่อนใช้ใน production

## 🆘 การแก้ไขปัญหา

ดูเอกสาร:
- `WINDOWS_DEVELOPMENT.md` - ส่วน "การแก้ไขปัญหา"
- `GITHUB_WORKFLOW.md` - ส่วน "การแก้ไขปัญหา"
- `QUICK_REFERENCE.md` - ส่วน "Troubleshooting"
