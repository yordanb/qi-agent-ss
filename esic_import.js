/**
 * ESIC TM Import Script (standalone, untuk initial bulk import)
 * Usage: node esic_import.js "path/to/file.xlsx"
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

function cleanText(val) {
  if (val == null || val === '') return '';
  let s = String(val).trim();
  s = s.replace(/[\t\n\r]+/g, ' ').replace(/\s{2,}/g, ' ').trim();
  return s;
}

function parseFilename(fname) {
  const m = fname.match(/(\d{6})/);
  if (m) {
    const ym = m[1];
    return { year: parseInt(ym.slice(0, 4)), month: parseInt(ym.slice(4, 6)) };
  }
  throw new Error(`Cannot parse year/month from filename: ${fname}`);
}

async function importFile(client, filePath) {
  const fname = path.basename(filePath);
  const { year, month } = parseFilename(fname);
  const snapDate = `${year}-${String(month).padStart(2, '0')}-01`;

  const wb = XLSX.readFile(filePath);
  const ws = wb.Sheets[wb.SheetNames[0]];
  const rows = XLSX.utils.sheet_to_json(ws);

  console.log(`\n=== ${fname} (${year}-${String(month).padStart(2, '0')}) ===`);
  console.log(`Total rows: ${rows.length}`);

  let newCount = 0, updatedCount = 0, skipped = 0;

  for (const r of rows) {
    const dept = cleanText(r['Kode Dept']);
    if (!ALLOWED_DEPT.includes(dept)) { skipped++; continue; }

    const nrp = cleanText(r['NRP']);
    if (!nrp) continue;

    // Build monthly metrics
    const monthly = {};
    for (const m of ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']) {
      for (const suffix of ['Jumlah', 'MTD', 'ESIC']) {
        const col = `${m} ${suffix}`;
        if (r[col] != null && typeof r[col] === 'number') {
          monthly[`${m.toLowerCase()}_${suffix.toLowerCase()}`] = r[col];
        }
      }
    }

    const res = await client.query(`
      INSERT INTO tb_esic.esic_tm 
        (nrp, nama, dept, divisi, distrik, posisi, snapshot_date,
         dokumen_diakses, dokumen_mtd, monthly_metrics)
      VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
      ON CONFLICT (nrp, snapshot_date) DO UPDATE SET
        nama=EXCLUDED.nama, dept=EXCLUDED.dept, divisi=EXCLUDED.divisi,
        distrik=EXCLUDED.distrik, posisi=EXCLUDED.posisi,
        dokumen_diakses=EXCLUDED.dokumen_diakses,
        dokumen_mtd=EXCLUDED.dokumen_mtd,
        monthly_metrics=EXCLUDED.monthly_metrics
      RETURNING (xmax = 0) AS is_new
    `, [
      nrp,
      cleanText(r['Nama']),
      dept,
      cleanText(r['Divisi']),
      cleanText(r['Distrik']) || 'KIDE',
      cleanText(r['Posisi']),
      snapDate,
      cleanText(r['Dokumen Yang Diakses']),
      cleanText(r['Dokumen MTD']),
      JSON.stringify(monthly),
    ]);

    if (res.rows[0].is_new) newCount++; else updatedCount++;
  }

  console.log(`Imported: ${newCount} new, ${updatedCount} updated, ${skipped} skipped (other dept)`);
  return { total: newCount + updatedCount, new: newCount, updated: updatedCount, skipped };
}

async function main() {
  const files = process.argv.slice(2);
  if (!files.length) {
    console.log('Usage: node esic_import.js "file1.xlsx" "file2.xlsx" ...');
    process.exit(1);
  }

  const client = new Client(DB);
  await client.connect();
  console.log('Connected to PostgreSQL');

  let grandTotal = 0;
  for (const f of files) {
    const stats = await importFile(client, f);
    grandTotal += stats.total;
  }

  const countRes = await client.query('SELECT COUNT(*) FROM tb_esic.esic_tm');
  console.log(`\nGrand total imported: ${grandTotal}`);
  console.log(`Total records in DB: ${countRes.rows[0].count}`);

  await client.end();
}

main().catch(err => { console.error(err); process.exit(1); });
