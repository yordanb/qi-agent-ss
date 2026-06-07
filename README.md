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

## Architecture

Modular structure following MTE pattern:

```
app/
├── api/
│   └── v1/
│       └── router.py          # Aggregator (auth, ss, esic, manpower, upload)
├── modules/
│   ├── auth/
│   │   └── router.py          # Thin router → auth_service
│   ├── ss/
│   │   └── router.py          # Thin router → ss_service
│   ├── esic/                  # ESIC endpoints
│   ├── manpower/              # Manpower endpoints
│   └── upload/                # Upload + PIN endpoints
├── services/
│   ├── auth_service.py        # Auth business logic
│   └── ss_service.py          # SS business logic
├── repositories/
│   ├── user_repo.py           # User DB operations
│   └── ss_repo.py             # SS + import_log DB operations
├── core/
│   ├── config.py              # Pydantic settings
│   ├── database.py            # Async engine + session
│   └── security.py            # JWT + bcrypt utilities
├── models.py                  # SQLAlchemy models
└── main.py                    # App factory + middleware
```

**Pattern:**
- **Router** → thin layer, hanya handle request/response
- **Service** → business logic
- **Repository** → database operations

## API v1 Endpoints

Base URL: `https://qi.mibt.my.id/api/v1`

### Auth

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/login` | POST | Login → returns `access_token`, `refresh_token` |
| `/api/v1/auth/refresh` | POST | Refresh expired token |
| `/api/v1/auth/change-password` | POST | Change password (requires old password) |
| `/api/v1/auth/admin/reset-password` | POST | Admin reset user password |

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
  "nama": "Yordan Baniara",
  "is_admin": true
}
```

### SS (Sistem Saran)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/ss/stats/{nrp}` | GET | Dashboard stats (total, closed, outstanding, wait_approval) |
| `/api/v1/ss/stats/{nrp}/monthly` | GET | Monthly breakdown (year, month query params) |
| `/api/v1/ss/by-nrp/{nrp}` | GET | SS records list (paginated: `page`, `page_size`) |
| `/api/v1/ss/dept/stats/{dept}` | GET | Dept-wide stats (year, month) |
| `/api/v1/ss/dept/daily/{dept}` | GET | Daily SS count for chart (year, month) |

**SS List Response:**
```json
{
  "data": [
    {
      "no_ss": "SS-2026-001",
      "judul": "...",
      "nrp": "61122292",
      "nama": "Yordan Baniara",
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

**Stats Response:**
```json
{
  "nrp": "61122292",
  "nama": "Yordan Baniara",
  "dept": "SPL2",
  "total_ss": 3,
  "closed": 2,
  "outstanding": 0,
  "wait_approval": 0,
  "other": 1,
  "last_update": "2026-06-07T11:16:31.570+08:00"
}
```

**Timestamp format:** UTC stored in DB (`timestamptz`), API response auto-converted to WITA (`+08:00`).

### ESIC TM

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/esic/` | GET | All ESIC snapshots (paginated) |
| `/api/v1/esic/by-nrp/{nrp}` | GET | ESIC snapshots for user |

### Manpower

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/manpower` | GET | List manpower (paginated, filter by `section`, `crew`) |
| `/api/v1/manpower/single` | POST | Create one record |
| `/api/v1/manpower/{id}` | PUT | Update record |
| `/api/v1/manpower/{id}` | DELETE | Delete record |
| `/api/v1/manpower/coverage/summary` | GET | Coverage per crew (year+month) |
| `/api/v1/manpower/coverage/section` | GET | Coverage per crew in section |
| `/api/v1/manpower/coverage/nrp/{nrp}` | GET | Individual coverage |

### Upload / PIN

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/upload/pin` | GET | Generate 6-digit PIN, valid 120 seconds (no auth) |
| `/api/v1/upload/verify-pin` | GET | Verify PIN — `?pin=123456` (no auth) |
| `/api/v1/upload/import` | POST | Upload Excel + import (requires JWT + valid PIN) |

**PIN flow:**
1. `GET /api/v1/upload/pin` → get 6-digit PIN + `remaining_seconds`
2. `GET /api/v1/upload/verify-pin?pin=xxxxxx` → `{valid: true/false}`
3. On success, allow upload via `POST /api/v1/upload/import`

### Health Check

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check — returns `{"status": "ok", "version": "4.1.0"}` |

## Database Schema

PostgreSQL database: `db_qi_agent`, host timezone: `Asia/Makassar`

| Schema | Tables |
|--------|--------|
| `tb_ss` | `users`, `ss_records`, `import_log`, `manpower`, `pin_state`, `refresh_tokens` |
| `tb_esic` | `esic_tm` |

**Key tables:**
- `tb_ss.users` — NRP, password_hash, is_admin (login accounts)
- `tb_ss.ss_records` — SS submissions with status/grade (`timestamptz`)
- `tb_ss.manpower` — Employee data (NRP, nama, section, crew)
- `tb_ss.pin_state` — PIN storage (shared across uvicorn workers)
- `tb_ss.refresh_tokens` — JWT refresh tokens
- `tb_esic.esic_tm` — ESIC snapshots with document metrics

**Relations:**
- `users` = login accounts (subset of manpower NRP)
- `manpower` = employee master data
- `ss_records.nrp` → references manpower (no FK, data-driven)
- `refresh_tokens.nrp` → `users.nrp` (FK, cascade delete)

## Auth Flow

1. **Login**: `POST /api/v1/auth/login` with `{nrp, password}`
2. **Auto-create**: If NRP exists in `manpower` but not in `users`, auto-create account with default password `12345`
3. **Token**: Include `Authorization: Bearer <access_token>` in all protected endpoints
4. **Refresh**: `POST /api/v1/auth/refresh` with `{refresh_token}`

## Deployment

### Using docker-compose

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

## Migrations (Alembic)

```bash
# Generate migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Stamp current state
alembic stamp head
```

## Logging

Structured log format:
```
2026-06-07 21:30:00 | INFO | qi-agent | POST /api/v1/auth/login → 200 (45ms)
2026-06-07 21:30:01 | ERROR | qi-agent | GET /api/v1/ss/stats/xxx → ERROR: ... (12ms)
```

## CORS

Restricted to `https://qi.mibt.my.id` (no wildcard).

## Security

- JWT authentication on all protected endpoints
- Bcrypt password hashing
- PIN mechanism for upload approval (DB-backed, multi-worker safe)
- Rate limiting via Cloudflare
- HTTPS via Cloudflare tunnel
- Input validation (year: 2020-2030, month: 1-12, page ≥ 1, page_size: 1-200)

---

**Repo:** [github.com/yordanb/qi-agent-ss](https://github.com/yordanb/qi-agent-ss)
