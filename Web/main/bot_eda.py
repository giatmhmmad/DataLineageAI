# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models

class JobUploadLogs(models.Model):
    
    log_id = models.AutoField(primary_key=True)
    job = models.ForeignKey('JobUploadSessions', models.DO_NOTHING)
    status = models.CharField(max_length=50, blank=True, null=True)
    log_message = models.TextField(blank=True, null=True)
    update_time = models.DateTimeField(blank=True, null=True, auto_now=True)

    class Meta:
        managed = False
        db_table = 'job_upload_logs'


class JobUploadSessions(models.Model):
    job_id = models.AutoField(primary_key=True)
    job_name = models.CharField(max_length=255, blank=True, null=True)
    job_path = models.TextField(blank=True, null=True)
    pic_job = models.CharField(max_length=100, blank=True, null=True)
    output_table = models.CharField(max_length=255, blank=True, null=True)
    upload_time = models.DateTimeField(blank=True, null=True)


    retry_count = models.IntegerField(default=0)
    original_upload_time = models.DateTimeField(null=True, blank=True)  
    current_status = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        db_index=True  
    )

    def get_current_status(self):
        """
        Mendapatkan status terbaru dari JobUploadLogs.
        Method ini akan selalu query database untuk mendapatkan status fresh.
        """
        latest_log = JobUploadLogs.objects.using('bot_eda').filter(
            job=self
        ).order_by('-update_time').first()
        
        if latest_log:
            return latest_log.status
        return self.current_status  # fallback ke field current_status jika tidak ada log

    def refresh_current_status(self):
        """
        Update field current_status di database dengan status terbaru dari log.
        Panggil method ini jika ingin menyimpan status ke database.
        """
        new_status = self.get_current_status()
        if new_status and new_status != self.current_status:
            self.current_status = new_status
            self.save(using='bot_eda', update_fields=['current_status'])
        return new_status

    class Meta:
        managed = False
        db_table = 'job_upload_sessions'
        indexes = [
            models.Index(fields=['current_status', '-upload_time']),  
        ]


class StagingDetectedTables(models.Model):
    table_id = models.AutoField(primary_key=True)
    job = models.ForeignKey(JobUploadSessions, models.DO_NOTHING)
    table_name = models.CharField(max_length=255, blank=True, null=True)
    table_category = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'staging_detected_tables'
        app_label = 'main'
