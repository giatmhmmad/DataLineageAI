import os
import django
from django.test import Client

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_lineage.settings')
django.setup()

client = Client()
# We need a job id. Let's find the first JobDetail in DB
from main.models import JobDetail
job = JobDetail.objects.first()
if not job:
    print("No jobs found")
else:
    response = client.get(f'/jobs/edit/{job.job_id}/')
    html = response.content.decode('utf-8')
    print("--- RESPONSE STATUS ---", response.status_code)
    
    # Let's extract the JS block
    start_str = 'const ALL_TABLES'
    if start_str in html:
        js_block = html[html.find(start_str):]
        # print only up to 30 lines
        lines = js_block.split('\n')
        print("--- JS BLOCK START ---")
        for i in range(min(50, len(lines))):
            print(lines[i])
    else:
        print("ALL_TABLES not found in HTML!")
