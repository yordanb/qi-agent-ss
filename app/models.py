from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Numeric, Date, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "tb_ss"}

    nrp = Column(String(20), primary_key=True)
    password_hash = Column(Text, nullable=False)
    role = Column(String(20), default="user", nullable=False)  # 'admin' or 'user'
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SsRecord(Base):
    __tablename__ = "ss_records"
    __table_args__ = {"schema": "tb_ss"}

    no_ss = Column(String(30), primary_key=True)
    judul = Column(Text, nullable=False, default="")
    nrp = Column(String(20), default="", index=True)
    nama = Column(Text, default="")
    dept = Column(String(20), default="", index=True)
    divisi = Column(String(20), default="")
    distrik = Column(String(10), default="KIDE")
    tanggal_laporan = Column(Date)
    grade_ss = Column(String(5), default="")
    kualitas_ss = Column(String(50), default="")
    kategori_ss = Column(String(50), default="")
    reward_ss = Column(Numeric(12, 2), default=0)
    status_karyawan = Column(String(10), default="")
    manfaat_financial = Column(Numeric(18, 2))
    tanggal_menilai = Column(Date)
    dinilai_oleh = Column(Text, default="")
    current_status = Column(String(50), default="", index=True)
    source = Column(String(20), default="", index=True)
    latest_import_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ImportLog(Base):
    __tablename__ = "import_log"
    __table_args__ = {"schema": "tb_ss"}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(Text, nullable=False)
    source_type = Column(String(20), nullable=False)
    total_rows = Column(Integer, default=0)
    new_records = Column(Integer, default=0)
    updated_records = Column(Integer, default=0)
    imported_at = Column(DateTime, default=datetime.utcnow)


class EsicTm(Base):
    __tablename__ = "esic_tm"
    __table_args__ = {"schema": "tb_esic"}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nrp = Column(String(20), nullable=False, index=True)
    nama = Column(Text)
    dept = Column(String(20))
    divisi = Column(String(20))
    distrik = Column(String(10))
    posisi = Column(Text)
    snapshot_date = Column(Date, nullable=False)
    dokumen_diakses = Column(Text)
    dokumen_mtd = Column(Text)
    monthly_metrics = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)


class Manpower(Base):
    __tablename__ = "manpower"
    __table_args__ = {"schema": "tb_ss"}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nrp = Column(String(12), index=True)
    nama = Column(Text)
    section = Column(Text)
    crew = Column(Text)
    posisi = Column(Text)
    target_ss = Column(Integer, default=0)
    status = Column(Text)
    jabatan = Column(Text)
    last_update = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = {"schema": "tb_ss"}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nrp = Column(String(20), index=True)
    token = Column(String(500), unique=True)
    expires_at = Column(DateTime)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class PinState(Base):
    __tablename__ = "pin_state"
    __table_args__ = {"schema": "tb_ss"}

    id = Column(Integer, primary_key=True, default=1)
    pin = Column(String(10), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    fail_count = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
