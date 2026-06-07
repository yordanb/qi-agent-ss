# QI Agent SS — FastAPI Backend

Backend API for the QI Agent Flutter app. JWT-based authentication, PostgreSQL database, deployed on Docker.

## Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 16 |
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
  "nrp": "61122292",
  "nama": "YORDAN BANIARA",
  "is_admin": true
}
```

---

## SS (Sistem Saran)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ss/stats/{nrp}` | GET | Dashboard stats for user (total_ss, wait_approval, dept) |
| `/api/ss/stats/{nrp}/monthly` | GET | Monthly SS breakdown (year+month params) |
| `/api/ss/by-nrp/{nrp}` | GET | SS records list (paginated: `page`, `page_size`) |
| `/api/ss/dept/stats/{dept}` | GET | Dept-wide stats (year+month) |
| `/api/ss/dept/daily/{dept}` | GET | Daily SS count for dept chart (year+month) |

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
      "grade_ss": "A",
      "created_at": "2026-06-07T11:16:31+08:00"
    }
  ],
  "total": 47,
  "page": 1,
  "page_size": 20
}
```

**Timestamp format:** UTC stored in DB (`timestamptz`), API response auto-converted to WITA (`+08:00`).

---

## ESIC TM

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/esic/` | GET | All ESIC snapshots (paginated) |
| `/api/esic/by-nrp/{nrp}` | GET | ESIC snapshots for user |

---

## Manpower

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/manpower` | GET | List manpower (paginated, filter by `section`, `crew`) |
| `/api/manpower/single` | POST | Create one record |
| `/api/manpower/{id}` | PUT | Update record |
| `/api/manpower/{id}` | DELETE | Delete record |
| `/api/manpower/coverage/summary` | GET | Coverage per crew (year+month) — sorted by % DESC |
| `/api/manpower/coverage/section` | GET | Coverage per crew in section |
| `/api/manpower/coverage/nrp/{nrp}` | GET | Individual coverage |

---

## Upload / PIN

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload/pin` | GET | Generate 6-digit PIN, valid 120 seconds (no auth required) |
| `/api/upload/verify-pin` | GET | Verify PIN — `?pin=123456` (no auth required) |
| `/api/upload/import` | POST | Upload Excel + import (requires JWT + valid PIN) |

**PIN flow:**
1. Call `GET /api/upload/pin` → get 6-digit PIN + `remaining_seconds`
2. Show PIN to user in Flutter app
3. Call `GET /api/upload/verify-pin?pin=xxxxxx` → `{valid: true/false}`
4. On success, allow upload via `POST /api/upload/import`

---

## Database Schema

PostgreSQL database: `db_qi_agent`, host timezone: `Asia/Makassar`

| Schema | Tables |
|--------|--------|
| `tb_ss` | `users`, `ss_records`, `import_log`, `manpower`, `pin_state` |
| `tb_esic` | `esic_tm` |

**Key tables:**
- `tb_ss.users` — NRP, password_hash, is_admin
- `tb_ss.ss_records` — SS submissions with status/grade (`timestamptz` for timestamps)
- `tb_ss.manpower` — staff roster (NRP, crew, target SS)
- `tb_ss.pin_state` — PIN storage (shared across all uvicorn workers)
- `tb_esic.esic_tm` — ESIC snapshots with document metrics

---

## Deployment

### Using docker-compose (recommended)

```bash
cd qi-agent-ss
docker compose -f docker-compose.jwt.yml up -d
```

Config loaded from `.env` file:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@172.18.0.7:5432/db_qi_agent
JWT_SECRET_KEY=<generate-with-openssl-rand-base64-32>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
REFRESH_TOKEN_EXPIRE_DAYS=7
TZ=Asia/Makassar
```

### Manual docker run

```bash
docker run -d \
  --name qi-agent-ss-jwt \
  --network backend-network \
  -p 8001:8000 \
  --env-file .env \
  -e TZ=Asia/Makassar \
  --restart unless-stopped \
  qi-agent-ss-jwt:latest
```

---

**Repo:** [github.com/yordanb/qi-agent-ss](https://github.com/yordanb/qi-agent-ss)
