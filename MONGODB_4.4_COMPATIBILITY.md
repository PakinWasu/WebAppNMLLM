# MongoDB 4.4.18 Compatibility Guide

เอกสารนี้อธิบายการปรับปรุงโปรเจคให้รองรับ MongoDB 4.4.18

## 📋 สารบัญ

- [การเปลี่ยนแปลง](#การเปลี่ยนแปลง)
- [ไฟล์ที่แก้ไข](#ไฟล์ที่แก้ไข)
- [การตรวจสอบ Compatibility](#การตรวจสอบ-compatibility)
- [การทดสอบ](#การทดสอบ)

## การเปลี่ยนแปลง

### 1. Docker Configuration

#### docker-compose.yml (Development)
- ✅ ใช้ `mongo:4.4.18` (ถูกต้องแล้ว)
- ✅ ใช้ `mongo` command สำหรับ healthcheck (ถูกต้องแล้ว)

#### docker-compose.prod.yml (Production)
- ✅ เปลี่ยนจาก `mongo:6.0` เป็น `mongo:4.4.18`
- ✅ เปลี่ยน healthcheck จาก `mongosh` เป็น `mongo`
- ✅ ใช้ `mongo --eval` แทน `mongosh --eval`

### 2. MongoDB Driver

#### Motor Version
- ✅ ระบุ `motor>=3.0.0,<4.0.0` ใน `requirements.txt`
- ✅ Motor 3.x รองรับ MongoDB 4.4.18 อย่างสมบูรณ์

### 3. Code Changes

#### list_indexes() Compatibility
- ✅ เปลี่ยนจาก `list_indexes().to_list()` เป็น `async for` loop
- ✅ รองรับ MongoDB 4.4.18 และ Motor driver

**ก่อน:**
```python
existing_indexes = await _db["parsed_configs"].list_indexes().to_list(length=100)
```

**หลัง:**
```python
index_names = []
async for idx in _db["parsed_configs"].list_indexes():
    index_names.append(idx["name"])
```

### 4. Query Operators

ตรวจสอบแล้วว่า query operators ทั้งหมดที่ใช้รองรับ MongoDB 4.4.18:
- ✅ `$in` - รองรับ
- ✅ `$or` - รองรับ
- ✅ `$and` - รองรับ
- ✅ `$exists` - รองรับ
- ✅ `$regex` - รองรับ
- ✅ `$ne`, `$gt`, `$gte`, `$lt`, `$lte` - รองรับ

### 5. Index Creation

- ✅ `background=True` รองรับใน MongoDB 4.4.18
- ✅ Compound indexes รองรับ
- ✅ Unique indexes รองรับ

### 6. Documentation

- ✅ อัปเดต README.md ให้ใช้ `mongo` แทน `mongosh`

## ไฟล์ที่แก้ไข

1. **docker-compose.prod.yml**
   - เปลี่ยน MongoDB image จาก `mongo:6.0` เป็น `mongo:4.4.18`
   - เปลี่ยน healthcheck จาก `mongosh` เป็น `mongo`

2. **backend/app/db/mongo.py**
   - แก้ไข `list_indexes()` ให้ใช้ `async for` loop แทน `.to_list()`

3. **backend/requirements.txt**
   - ระบุ Motor version: `motor>=3.0.0,<4.0.0`

4. **README.md**
   - เปลี่ยนคำสั่งจาก `mongosh` เป็น `mongo`

## การตรวจสอบ Compatibility

### MongoDB Features ที่ใช้

| Feature | MongoDB 4.4.18 | Status |
|---------|----------------|--------|
| Basic CRUD operations | ✅ | รองรับ |
| Indexes (single, compound, unique) | ✅ | รองรับ |
| Background index creation | ✅ | รองรับ |
| Query operators ($in, $or, $and, etc.) | ✅ | รองรับ |
| Regex queries | ✅ | รองรับ |
| Cursor iteration | ✅ | รองรับ |
| Aggregation (basic) | ✅ | รองรับ |

### Features ที่ไม่ใช้ (MongoDB 6.0+ only)

- ❌ `$function` (MongoDB 5.0+)
- ❌ `$jsonSchema` validation (MongoDB 3.6+ แต่ไม่ใช้)
- ❌ `$merge` (MongoDB 4.2+ แต่ไม่ใช้)
- ❌ `$unionWith` (MongoDB 4.4+ แต่ไม่ใช้)

## การทดสอบ

### 1. ตรวจสอบ MongoDB Version

```bash
# Development
docker exec mnp-mongo mongo --eval "db.version()"

# Production
docker exec mnp-mongo-prod mongo --eval "db.version()"
```

ควรแสดง: `4.4.18`

### 2. ทดสอบ Connection

```bash
# Development
docker exec mnp-mongo mongo --eval "db.runCommand('ping')"

# Production
docker exec mnp-mongo-prod mongo --eval "db.runCommand('ping')"
```

ควรแสดง: `{ "ok" : 1 }`

### 3. ทดสอบ Index Creation

```bash
# เข้าไปใน backend container
docker exec -it mnp-backend-prod bash

# ตรวจสอบ logs ว่า indexes ถูกสร้าง
# หรือทดสอบโดยการ start application
```

### 4. ทดสอบ Query Operations

ทดสอบผ่าน API:
- ✅ List projects
- ✅ Upload documents
- ✅ Query documents by folder_id
- ✅ Get summary

## หมายเหตุ

### MongoDB 4.4.18 Limitations

1. **mongosh vs mongo**
   - MongoDB 4.4.18 ใช้ `mongo` shell (legacy)
   - MongoDB 6.0+ ใช้ `mongosh` shell (new)
   - โปรเจคนี้ใช้ `mongo` สำหรับ compatibility

2. **Index Creation**
   - `background=True` ทำงานได้ปกติ
   - Compound indexes รองรับ
   - Unique constraints รองรับ

3. **Query Performance**
   - Query operators พื้นฐานทำงานได้ดี
   - Indexes ช่วยเพิ่ม performance

### Migration Notes

ถ้าต้องการ migrate จาก MongoDB 6.0 ไป 4.4.18:

1. **Backup ข้อมูลก่อน:**
   ```bash
   docker exec mnp-mongo-prod mongodump --archive=/backup/backup-$(date +%Y%m%d).archive
   ```

2. **Restore ไปยัง MongoDB 4.4.18:**
   ```bash
   docker exec mnp-mongo-prod mongorestore --archive=/backup/backup-YYYYMMDD.archive
   ```

3. **ตรวจสอบข้อมูล:**
   ```bash
   docker exec mnp-mongo-prod mongo --eval "db.stats()"
   ```

## ✅ Checklist

- [x] แก้ไข docker-compose.prod.yml ให้ใช้ mongo:4.4.18
- [x] เปลี่ยน mongosh เป็น mongo ใน healthcheck
- [x] แก้ไข list_indexes() ให้ compatible
- [x] ระบุ Motor version ใน requirements.txt
- [x] อัปเดต README.md
- [x] ตรวจสอบ query operators
- [x] ตรวจสอบ index creation
- [x] สร้างเอกสาร compatibility guide

## 📝 References

- [MongoDB 4.4 Release Notes](https://www.mongodb.com/docs/v4.4/release-notes/4.4/)
- [Motor Documentation](https://motor.readthedocs.io/)
- [MongoDB Compatibility](https://www.mongodb.com/docs/manual/reference/command/)

