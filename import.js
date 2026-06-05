/**
 * qi-agent-ss Import Script
 * Import Excel (closed + outstanding) ke PostgreSQL tb_ss schema
 * Filter: hanya departemen SPL2 dan STYR
 * 
 * Usage:
 *   node import.js closed "path/to/closed.xlsx"
 *   node import.js outstanding "path/to/outstanding.xlsx"
 *   node import.js both "closed.xlsx" "outstanding.xlsx"
 */

const { Client } = require('pg');
const XLSX = require('xlsx');
const path = require('path');

const DB = {
  host: '127.0.0.1',
  port: 5432,
  database: 'db_qi_agent',
  user: 'postgres',
  password: 'postgres',
};

const ALLOWED_DEPT = ['SPL2', 'STYR'];

// --- Helpers ---
function cleanText(val) {
  if (val == null || val === '') return '';
  let s = String(val).trim();
  s = s.replace(/[\t\n\r]+/g, ' ').replace(/\s{2,}/g, ' ').trim();
  return s;
}

function parseDate(val) {
  if (val == null || val === '') return null;
  const s = String(val).trim();
  const match = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (match) {
    const [, d, m, y] = match;
    return `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
  }
  const dt = new Date(s);
  if (!isNaN(dt.getTime())) {
    return dt.toISOString().split('T')[0];
  }
  return null;
}

function parseNum(val) {
  if (val == null || val === '') return null;
  const n = Number(String(val).replace(/[^0-9.\-]/g, ''));
  return isNaN(n) ? null : n;
}

// --- Importers ---
async function importClosed(client, filePath, importId) {
  const wb = XLSX.readFile(filePath);
  const ws = wb.Sheets['Report'];
  const rows = XLSX.utils.sheet_to_json(ws);

  const filtered = rows.filter(r => ALLOWED_DEPT.includes(cleanText(r['DEPT'])));
  console.log(`Closed: ${rows.length} total, ${filtered.length} SPL2+STYR`);

  let newCount = 0, updatedCount = 0;

  for (const r of filtered) {
    const noSs = cleanText(r['NO SS']);
    if (!noSs) continue;

    const vals = [
      noSs,
      cleanText(r['JUDUL']),
      cleanText(r['NRP']),
      cleanText(r['PENCETUS IDE']),
      cleanText(r['DEPT']),
      '',
      cleanText(r['DISTRIK']) || 'KIDE',
      parseDate(r['TANGGAL LAPORAN']),
      cleanText(r['GRADE SS']),
      cleanText(r['KUALITAS SS']),
      cleanText(r['KATEGORI SS']),
      parseNum(r['REWARD SS']) || 0,
      cleanText(r['STATUS KARYAWAN']),
      parseNum(r['MANFAAT FINANCIAL']),
      parseDate(r['TANGGAL MENILAI']),
      cleanText(r['DINILAI OLEH']),
      'closed',
      'closed',
      importId,
    ];

    const q = `
      INSERT INTO tb_ss.ss_records 
        (no_ss, judul, nrp, nama, dept, divisi, distrik, tanggal_laporan,
         grade_ss, kualitas_ss, kategori_ss, reward_ss, status_karyawan,
         manfaat_financial, tanggal_menilai, dinilai_oleh, 
         current_status, source, latest_import_id)
      VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19)
      ON CONFLICT (no_ss) DO UPDATE SET
        judul = EXCLUDED.judul, nrp = EXCLUDED.nrp, nama = EXCLUDED.nama,
        dept = EXCLUDED.dept, divisi = EXCLUDED.divisi, distrik = EXCLUDED.distrik,
        tanggal_laporan = EXCLUDED.tanggal_laporan, grade_ss = EXCLUDED.grade_ss,
        kualitas_ss = EXCLUDED.kualitas_ss, kategori_ss = EXCLUDED.kategori_ss,
        reward_ss = EXCLUDED.reward_ss, status_karyawan = EXCLUDED.status_karyawan,
        manfaat_financial = EXCLUDED.manfaat_financial,
        tanggal_menilai = EXCLUDED.tanggal_menilai,
        dinilai_oleh = EXCLUDED.dinilai_oleh,
        current_status = EXCLUDED.current_status,
        source = EXCLUDED.source, latest_import_id = EXCLUDED.latest_import_id
      RETURNING (xmax = 0) AS is_new;
    `;

    const res = await client.query(q, vals);
    if (res.rows[0].is_new) newCount++; else updatedCount++;
  }

  console.log(`Closed done: ${newCount} new, ${updatedCount} updated`);
  return { total: filtered.length, new: newCount, updated: updatedCount };
}

async function importOutstanding(client, filePath, importId) {
  const wb = XLSX.readFile(filePath);
  const ws = wb.Sheets['Report'];
  const rows = XLSX.utils.sheet_to_json(ws);

  const filtered = rows.filter(r => {
    const dept = cleanText(r['DEPT']);
    return ALLOWED_DEPT.includes(dept);
  });
  console.log(`Outstanding: ${rows.length} total, ${filtered.length} SPL2+STYR`);

  let newCount = 0, updatedCount = 0;

  for (const r of filtered) {
    const noSs = cleanText(r['NO SS']);
    if (!noSs) continue;

    const vals = [
      noSs,
      cleanText(r['JUDUL']),
      cleanText(r['NRP']),
      cleanText(r['NAMA']),
      cleanText(r['DEPT']),
      cleanText(r['DIVISI']),
      cleanText(r['DISTRIK']) || 'KIDE',
      parseDate(r['TANGGAL LAPORAN']),
      '', '', '', 0, '', null, null, '',
      cleanText(r['STATUS']),
      'outstanding',
      importId,
    ];

    const q = `
      INSERT INTO tb_ss.ss_records 
        (no_ss, judul, nrp, nama, dept, divisi, distrik, tanggal_laporan,
         grade_ss, kualitas_ss, kategori_ss, reward_ss, status_karyawan,
         manfaat_financial, tanggal_menilai, dinilai_oleh, 
         current_status, source, latest_import_id)
      VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19)
      ON CONFLICT (no_ss) DO UPDATE SET
        judul = EXCLUDED.judul, nrp = EXCLUDED.nrp, nama = EXCLUDED.nama,
        dept = EXCLUDED.dept, divisi = EXCLUDED.divisi, distrik = EXCLUDED.distrik,
        tanggal_laporan = EXCLUDED.tanggal_laporan,
        current_status = EXCLUDED.current_status,
        source = EXCLUDED.source, latest_import_id = EXCLUDED.latest_import_id
      RETURNING (xmax = 0) AS is_new;
    `;

    const res = await client.query(q, vals);
    if (res.rows[0].is_new) newCount++; else updatedCount++;
  }

  console.log(`Outstanding done: ${newCount} new, ${updatedCount} updated`);
  return { total: filtered.length, new: newCount, updated: updatedCount };
}

// --- Main ---
async function main() {
  const args = process.argv.slice(2);
  const mode = args[0];
  const files = args.slice(1);

  if (!mode || !files.length) {
    console.log('Usage:');
    console.log('  node import.js closed "closed.xlsx"');
    console.log('  node import.js outstanding "outstanding.xlsx"');
    console.log('  node import.js both "closed.xlsx" "outstanding.xlsx"');
    console.log('Filter: SPL2 + STYR only');
    process.exit(1);
  }

  const client = new Client(DB);
  await client.connect();
  console.log('Connected to PostgreSQL');

  try {
    if (mode === 'closed' || mode === 'both') {
      const closedFile = files[0];
      const logRes = await client.query(
        `INSERT INTO tb_ss.import_log (filename, source_type) VALUES ($1, 'closed') RETURNING id`,
        [path.basename(closedFile)]
      );
      const importId = logRes.rows[0].id;
      const stats = await importClosed(client, closedFile, importId);
      await client.query(
        `UPDATE tb_ss.import_log SET total_rows=$1, new_records=$2, updated_records=$3 WHERE id=$4`,
        [stats.total, stats.new, stats.updated, importId]
      );
      console.log(`Import log #${importId} updated`);
    }

    if (mode === 'outstanding' || mode === 'both') {
      const outstandingFile = mode === 'both' ? files[1] : files[0];
      const logRes = await client.query(
        `INSERT INTO tb_ss.import_log (filename, source_type) VALUES ($1, 'outstanding') RETURNING id`,
        [path.basename(outstandingFile)]
      );
      const importId = logRes.rows[0].id;
      const stats = await importOutstanding(client, outstandingFile, importId);
      await client.query(
        `UPDATE tb_ss.import_log SET total_rows=$1, new_records=$2, updated_records=$3 WHERE id=$4`,
        [stats.total, stats.new, stats.updated, importId]
      );
      console.log(`Import log #${importId} updated`);
    }

    const countRes = await client.query('SELECT COUNT(*) as total FROM tb_ss.ss_records');
    console.log(`\nTotal records in DB: ${countRes.rows[0].total}`);
  } catch (err) {
    console.error('Import error:', err.message);
    process.exit(1);
  } finally {
    await client.end();
  }
}

main();
