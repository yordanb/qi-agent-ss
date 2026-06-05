# QI Agent SS — FastAPI Backend

Backend API for the QI Agent Flutter app. JWT-based authentication, PostgreSQL database, deployed on Docker.

## Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 15 |
| Auth | JWT (python-jose, bcrypt) |
| Server | Uvicorn |
| Container | Docker |

## Auth

All protected endpoints require `Authorization: Bearer <token>` header.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/login` | POST | Login → returns `access_token`, `refresh_token` |
| `/api/auth/refresh` | POST | Refresh expired token |
| `/api/auth/change-password` | POST | Change password (requires old password) |

**Login payload:**
```json
{ "nrp": "61122292", "password": "12345" }
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "nrp": "61122292",
    "nama": "YORDAN BANIARA",
    "is_admin": true
  }
}
```

---

## SS (Sistem Saran)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ss/stats/{nrp}` | GET | Dashboard stats for user (total_ss, wait_approval, dept) |
| `/api/ss/stats/{nrp}/monthly` | GET | Monthly SS breakdown (year+month params) |
| `/api/ss/by-nrp/{nrp}` | GET | SS records list (paginated: `page`, `page_size`) |
| `/api/ss/db-stats` | GET | Global stats from DB |
| `/api/ss/dept/stats/{dept}` | GET | Dept-wide stats (year+month) |
| `/api/ss/dept/daily/{dept}` | GET | Daily SS count for dept chart (year+month) |
| `/api/ss/{no_ss}` | GET | Single SS detail |

**SS List Response:**
```json
{
  "data": [
    {
      "no_ss": "SS-2026-001",
      "judul": "...",
      "nrp": "61122292",
      "nama": "YORDAN BANIARA",
      "dept": "SPL2",
      "tanggal_laporan": "2026-05-15",
      "current_status": "approved",
      "grade_ss": "A"
    }
  ],
  "total": 47,
  "page": 1,
  "page_size": 20
}
```

---

## ESIC TM

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/esic/` | GET | All ESIC snapshots (paginated) |
| `/api/esic/by-nrp/{nrp}` | GET | ESIC snapshots for user |
| `/api/esic/compare` | GET | Compare two dates |
| `/api/esic/documents` | GET | Document list |
| `/api/esic/progress` | GET | Monthly progress metrics |

**ESIC Response:**
```json
{
  "data": [
    {
      "id": 1,
      "nrp": "61122292",
      "nama": "YORDAN BANIARA",
      "snapshot_date": "2026-05-01",
      "dokumen_diakses": "Dokumen KPI,Dokumen Laporan",
      "dokumen_mtd": "Modul Safety,Modul Quality",
      "monthly_metrics": "..."
    }
  ]
}
```

---

## Manpower

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/manpower` | GET | List manpower (paginated, filter by `section`, `crew`) |
| `/api/manpower/single` | POST | Create one record |
| `/api/manpower/{id}` | PUT | Update record |
| `/api/manpower/{id}` | DELETE | Delete record |
| `/api/manpower` | DELETE | Clear all records |
| `/api/manpower/coverage/summary` | GET | Coverage per crew (year+month) — sorted by % DESC |
| `/api/manpower/coverage/section` | GET | Coverage per crew in section |
| `/api/manpower/coverage/nrp/{nrp}` | GET | Individual coverage |

**Coverage Summary Response:**
```json
{
  "year": 2026,
  "month": 5,
  "data": [
    {
      "crew": "Grader",
      "total_people": 42,
      "total_ss": 103,
      "total_target": 210,
      "coverage_pct": 49.0
    }
  ]
}
```

**Create/Update Payload:**
```json
{
  "nrp": "61122292",
  "nama": "YORDAN BANIARA",
  "section": "Wheel Maintenance",
  "crew": "MTE",
  "posisi": "Engineer",
  "target_ss": 5,
  "status": "Aktif",
  "jabatan": "Staff"
}
```

---

## Upload / PIN

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload/pin` | GET | Generate 6-digit PIN, valid 120 seconds |
| `/api/upload/verify-pin` | POST | Verify PIN (body: `{"pin": "123456"}`) |

---

## Version Check

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/update` | GET | Forced update check |

**Response:**
```json
{
  "min_version": "5.5.0",
  "latest_version": "5.5.4",
  "latest_url": "https://github.com/yordanb/qi-agent-ss-app/releases"
}
```

---

## Database Schema

PostgreSQL database: `db_qi_agent`

| Schema | Tables |
|--------|--------|
| `tb_ss` | `users`, `ss_records`, `import_log`, `manpower`, `refresh_tokens` |
| `tb_esic` | `esic_tm` |

**Key tables:**
- `tb_ss.users` — NRP (PK), password_hash, is_admin
- `tb_ss.ss_records` — SS submissions with status/grade
- `tb_ss.manpower` — staff roster (NRP, crew, target SS)
- `tb_esic.esic_tm` — ESIC snapshots with document metrics

---

## Deployment

```bash
# Build
docker build -t qi-agent-ss-jwt .

# Run
docker run -d \
  --name qi-agent-ss-jwt \
  --network backend-network \
  -p 8001:8000 \
  -e DATABASE_URL="postgresql+asyncpg://postgres:postgres@172.18.0.5:5432/db_qi_agent" \
  -e REDIS_URL=redis://172.18.0.6:6379/0 \
  -e JWT_SECRET_KEY=<your-secret> \
  qi-agent-ss-jwt \
  sh -c 'uvicorn app.main:app --host 0.0.0.0 --port 8000'
```

---

**Repo:** [github.com/yordanb/qi-agent-ss](https://github.com/yordanb/qi-agent-ss)
