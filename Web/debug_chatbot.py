import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_lineage.settings')
django.setup()

from main.bot_eda import JobUploadSessions, JobUploadLogs
from main.chatbot_views import format_datetime

job_name = 'RDBMS_CDP_NEW_RMTOOLS_DLY_H1'

# Test 1: cari session
session_obj = JobUploadSessions.objects.using('bot_eda').filter(
    job_name=job_name
).first()
print("=== TEST 1: Session ===")
print("Session found:", session_obj)
print("Session job_name:", session_obj.job_name if session_obj else None)
print("Session upload_time:", session_obj.upload_time if session_obj else None)
print("Session type upload_time:", type(session_obj.upload_time) if session_obj else None)

# Test 2: cari logs
print("\n=== TEST 2: Logs ===")
if session_obj:
    logs = list(JobUploadLogs.objects.using('bot_eda').filter(
        job=session_obj
    ).values('log_id', 'status', 'log_message', 'update_time').order_by('update_time'))
    print("Total logs:", len(logs))
    if logs:
        print("Sample log:", logs[0])
        print("Type update_time:", type(logs[0]['update_time']))

# Test 3: test format_datetime yang sudah diperbaiki
print("\n=== TEST 3: Format Datetime (FIXED) ===")
if session_obj and session_obj.upload_time:
    dt = session_obj.upload_time
    print("Input datetime:", dt)
    formatted = format_datetime(dt)
    print("Formatted:", formatted)

# Test 4: cari done time
print("\n=== TEST 4: Done Time ===")
if session_obj:
    done_log = JobUploadLogs.objects.using('bot_eda').filter(
        job=session_obj,
        status__icontains='done'
    ).order_by('-update_time').first()
    print("Done log:", done_log)
    if done_log and done_log.update_time:
        print("Done time raw:", done_log.update_time)
        print("Done time formatted:", format_datetime(done_log.update_time))
    else:
        print("Done time: None")