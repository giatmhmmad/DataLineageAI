"""
Seed data SINTETIS untuk load-testing performa chatbot di skala 1000+ job.

INI BUKAN BAGIAN DARI APLIKASI PRODUKSI. Hanya untuk testing/development
lokal (Fase performa, Task 4.1 IMPLEMENTATION_PLAN.md). Jangan jalankan
terhadap database production/shared - ini menulis data sintetis dalam
jumlah besar ke DB `default` (JobDetail/Table/Relationship/JobDeveloper)
dan opsional ke DB `bot_eda` (JobUploadSessions/JobUploadLogs).

Semua data yang dibuat diberi prefix "LOADTEST_" pada job_name dan
table_name, supaya gampang dibedakan dari data asli dan gampang dibersihkan
lagi lewat --cleanup.

Terpisah dari `Web/utils/seeding.py` yang sudah usang (temuan L1
PROJECT_MEMORY.md, mereferensikan model yang sudah dihapus) - JANGAN
disatukan dengan file itu.

Cara pakai (dari direktori Web/):
    python scripts/seed_load_test.py --jobs 1000
    python scripts/seed_load_test.py --jobs 1000 --with-bot-eda
    python scripts/seed_load_test.py --cleanup
"""
import argparse
import os
import random
import sys

import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "data_lineage.settings")
django.setup()

from django.db import transaction  # noqa: E402

from main.models import JobDetail, JobDeveloper, Relationship, Table  # noqa: E402

PREFIX = "LOADTEST_"

SCHEMAS = ["NEWDATAMART_PST", "PROD_BM_BDA_PST", "SPM_DATA", "PRM", "STAGING_PST"]
CATEGORIES = ["DATAMART", "SOURCE DATA", "STAGING", "OTHER"]
DEPARTMENTS = [
    "DATA MANAGEMENT", "RETAIL BANKING ANALYTICS",
    "WHOLESALE BANKING ANALYTICS", "DATA GOVERNANCE", "CAMPAIGN MANAGEMENT",
]
JOB_NAME_STEMS = [
    "TRX_CHANNEL", "WALLET_SHARE", "TRADE_VOL", "DPK_PIPELINE",
    "KRD_NLTU", "MCM_KLN_TRX", "EALCO_PIPELINE", "COFYOL_DAILY",
    "ANOMALI_AGUNAN", "MASTER_CUST", "KOPRA_SUBSIDI", "PEER_ANALISIS",
]


def make_developer_pool(n=15):
    devs = []
    for i in range(n):
        devs.append(JobDeveloper(
            developer_name=f"{PREFIX}Dev{i:02d}",
            department=random.choice(DEPARTMENTS),
            team=f"Team {i % 5}",
        ))
    # bulk_create(..., ignore_conflicts=True) TIDAK mengisi PK balik ke objek
    # Python-nya (batasan Django) - selalu re-query dari DB supaya
    # developer_id terisi benar sebelum dipakai di M2M through-table insert.
    JobDeveloper.objects.bulk_create(devs, ignore_conflicts=True)
    return list(JobDeveloper.objects.filter(developer_name__startswith=PREFIX))


def make_table_pool(n=300):
    tables = []
    seen = set()
    while len(tables) < n:
        schema = random.choice(SCHEMAS)
        name = f"{PREFIX}{schema}.TBL_{len(tables):04d}"
        if name in seen:
            continue
        seen.add(name)
        tables.append(Table(
            table_name=name,
            table_category=random.choice(CATEGORIES),
            table_desc=f"Synthetic load-test table {len(tables)}",
        ))
    Table.objects.bulk_create(tables, ignore_conflicts=True)
    return list(Table.objects.filter(table_name__startswith=PREFIX))


def seed_default_db(n_jobs, table_pool_size, relationships_per_job_max, batch_size=500):
    print(f"[1/4] Menyiapkan pool developer & tabel...")
    dev_pool = make_developer_pool()
    table_pool = make_table_pool(table_pool_size)
    print(f"      {len(dev_pool)} developer, {len(table_pool)} tabel siap.")

    print(f"[2/4] Membuat {n_jobs} JobDetail sintetis...")
    jobs = []
    for i in range(n_jobs):
        stem = random.choice(JOB_NAME_STEMS)
        jobs.append(JobDetail(
            job_name=f"{PREFIX}{stem}_{i:05d}_DLY_H1",
            pic_job=f"{PREFIX}PIC{i % 20:02d}",
        ))
    JobDetail.objects.bulk_create(jobs, ignore_conflicts=True, batch_size=batch_size)
    created_jobs = list(JobDetail.objects.filter(job_name__startswith=PREFIX).prefetch_related('developers'))
    print(f"      {len(created_jobs)} job tersimpan.")

    print(f"[3/4] Menghubungkan developer (M2M) dan membuat Relationship...")
    through_model = JobDetail.developers.through
    m2m_rows = []
    relationship_rows = []
    seen_rel = set()  # (table1_id, table2_id, job_name) - jaga unique_together

    for job in created_jobs:
        n_devs = random.randint(1, 2)
        for dev in random.sample(dev_pool, min(n_devs, len(dev_pool))):
            m2m_rows.append(through_model(jobdetail_id=job.job_id, jobdeveloper_id=dev.developer_id))

        n_src = random.randint(1, relationships_per_job_max)
        n_tgt = random.randint(1, 2)
        src_tables = random.sample(table_pool, min(n_src, len(table_pool)))
        tgt_tables = random.sample(table_pool, min(n_tgt, len(table_pool)))
        for s in src_tables:
            for t in tgt_tables:
                if s.table_id == t.table_id:
                    continue
                key = (s.table_id, t.table_id, job.job_name)
                if key in seen_rel:
                    continue
                seen_rel.add(key)
                relationship_rows.append(Relationship(
                    job_name=job.job_name, job=job, table1=s, table2=t,
                ))

    through_model.objects.bulk_create(m2m_rows, ignore_conflicts=True, batch_size=batch_size)
    Relationship.objects.bulk_create(relationship_rows, ignore_conflicts=True, batch_size=batch_size)
    print(f"      {len(m2m_rows)} relasi job-developer, {len(relationship_rows)} baris Relationship dibuat.")
    return created_jobs


def seed_bot_eda(jobs, batch_size=500):
    """
    Opsional: isi bot_eda (JobUploadSessions/JobUploadLogs) untuk sebagian
    job, supaya filter status ("gagal", "belum diupload") dan job_logs bisa
    ikut ditest di skala besar. HANYA untuk DB bot_eda LOKAL/DEV milik
    developer sendiri (lihat README - dua database dibuat lokal saat setup).
    """
    from main.bot_eda import JobUploadLogs, JobUploadSessions

    print("[4/4] Mengisi bot_eda (JobUploadSessions/Logs) untuk sebagian job...")
    statuses = ["Done", "Upload Failed", "Done", "Done"]  # skew ke Done
    sessions = []
    # ~70% job dapat session (sisanya sengaja "belum diupload")
    with_session = random.sample(jobs, int(len(jobs) * 0.7))
    for job in with_session:
        sessions.append(JobUploadSessions(
            job_name=job.job_name,
            pic_job=job.pic_job,
            current_status=random.choice(statuses),
        ))
    JobUploadSessions.objects.using('bot_eda').bulk_create(sessions, batch_size=batch_size)
    created_sessions = list(
        JobUploadSessions.objects.using('bot_eda').filter(job_name__startswith=PREFIX)
    )

    logs = []
    for sess in created_sessions:
        n_logs = random.randint(1, 3)
        for _ in range(n_logs):
            logs.append(JobUploadLogs(
                job=sess,
                status=sess.current_status,
                log_message="Synthetic load-test log entry",
            ))
    JobUploadLogs.objects.using('bot_eda').bulk_create(logs, batch_size=batch_size)
    print(f"      {len(created_sessions)} session, {len(logs)} log entri dibuat di bot_eda.")


def cleanup():
    from main.bot_eda import JobUploadLogs, JobUploadSessions

    print("Menghapus data LOADTEST_ ...")
    n_logs, _ = JobUploadLogs.objects.using('bot_eda').filter(
        job__job_name__startswith=PREFIX
    ).delete()
    n_sessions, _ = JobUploadSessions.objects.using('bot_eda').filter(
        job_name__startswith=PREFIX
    ).delete()
    n_rel, _ = Relationship.objects.filter(job_name__startswith=PREFIX).delete()
    n_jobs, _ = JobDetail.objects.filter(job_name__startswith=PREFIX).delete()
    n_tables, _ = Table.objects.filter(table_name__startswith=PREFIX).delete()
    n_devs, _ = JobDeveloper.objects.filter(developer_name__startswith=PREFIX).delete()
    print(f"Selesai: {n_jobs} job, {n_rel} relasi, {n_tables} tabel, {n_devs} developer, "
          f"{n_sessions} session, {n_logs} log dihapus.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs', type=int, default=1000, help='Jumlah job sintetis (default 1000)')
    parser.add_argument('--tables', type=int, default=300, help='Ukuran pool tabel sintetis (default 300)')
    parser.add_argument('--max-src-per-job', type=int, default=6,
                         help='Maksimum source table per job (default 6)')
    parser.add_argument('--with-bot-eda', action='store_true',
                         help='Isi juga JobUploadSessions/Logs di DB bot_eda lokal')
    parser.add_argument('--cleanup', action='store_true',
                         help='Hapus SEMUA data LOADTEST_ (default DB dan bot_eda) lalu keluar')
    parser.add_argument('--seed', type=int, default=42, help='Random seed (default 42, reproducible)')
    args = parser.parse_args()

    random.seed(args.seed)

    if args.cleanup:
        cleanup()
        return

    with transaction.atomic():
        jobs = seed_default_db(args.jobs, args.tables, args.max_src_per_job)

    if args.with_bot_eda:
        seed_bot_eda(jobs)

    print("\nSelesai. Semua data sintetis diberi prefix 'LOADTEST_'.")
    print("Untuk membersihkan: python scripts/seed_load_test.py --cleanup")


if __name__ == '__main__':
    main()
