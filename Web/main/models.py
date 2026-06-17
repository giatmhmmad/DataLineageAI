from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver


class Table(models.Model):
    # 1. Definisikan Pilihan Kategori
    # Format: 'NILAI_DI_DB', 'LABEL_DI_LAYAR'
    CATEGORY_CHOICES = [
        ('DATAMART', 'DATAMART'),
        ('SOURCE DATA', 'SOURCE DATA'),
        ('STAGING', 'STAGING'),
        ('OTHER', 'OTHER'),
    ]

    table_id = models.AutoField(primary_key=True)
    table_name = models.CharField(max_length=255, unique=True)
    
    # 2. Pasang parameter 'choices' di sini
    table_category = models.CharField(
        max_length=100, 
        choices=CATEGORY_CHOICES,  # Ini kuncinya
        default='OTHER',           # Nilai default jika tidak diisi
        null=True, 
        blank=True
    )
    
    table_desc = models.TextField(null=True, blank=True)

    def __str__(self):
        # get_table_category_display() adalah cara Django menampilkan Label (misal: "Master Data")
        # bukan Value (misal: "MASTER")
        return f"{self.table_name} ({self.get_table_category_display()})"

class JobDeveloper(models.Model):

    DEPARTMENT_CHOICES = [
        ('DATA MANAGEMENT', 'DATA MANAGEMENT'),
        ('RETAIL BANKING ANALYTICS', 'RETAIL BANKING ANALYTICS'),
        ('WHOLESALE BANKING ANALYTICS', 'WHOLESALE BANKING ANALYTICS'),
        ('DATA GOVERNANCE', 'DATA GOVERNANCE'),
        ('CAMPAIGN MANAGEMENT', 'CAMPAIGN MANAGEMENT'),
        ('OTHER', 'OTHER'),
    ]

    developer_id = models.AutoField(primary_key=True)
    developer_name = models.CharField(max_length=255)
    department = models.CharField(max_length=255, choices=DEPARTMENT_CHOICES,default='OTHER',blank=False)
    team = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        verbose_name = "Job Developer"
        verbose_name_plural = "Job Developers"

    def __str__(self):
        return self.developer_name

class JobDetail(models.Model): 
    # job_id | PK
    job_id = models.AutoField(primary_key=True)
    
    # job_name (Unik di sini sebagai master data)
    job_name = models.CharField(max_length=255, unique=True)
    
    # pic_job
    pic_job = models.CharField(max_length=255, null=True, blank=True)

    # developer= models.ForeignKey(
    #     JobDeveloper,   
    #     on_delete=models.SET_NULL, 
    #     null=True,  
    #     blank=True,
    #     related_name='developed_jobs'
    # ) 

    developers = models.ManyToManyField(
        JobDeveloper,   
        related_name='developed_jobs',
        blank=True
    ) 

    # Timestamps (Opsional tapi recommended)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.job_name

    # --- Virtual Columns (Logic Hitungan) ---
    
    @property
    def source_table_count(self):
        """
        Menghitung jumlah unik source table (table1) dari tabel Relationship
        yang terhubung ke JobDetail ini.
        """
        # 'relationships' adalah related_name yang kita set di model Relationship
        return self.relationships.values('table1').distinct().count()

    @property
    def target_table_list(self):
        """
        List nama target table (table2)
        Output contoh: ['TableA', 'TableB']
        """
        return list(self.relationships.values_list('table2__table_name', flat=True).distinct())


class Relationship(models.Model):
    relationship_id = models.AutoField(primary_key=True)
    job_name = models.CharField(max_length=255)

    job = models.ForeignKey(
        JobDetail, 
        on_delete=models.CASCADE, 
        related_name='relationships', # Ini nama untuk dipanggil di JobDetail
        null=True, 
        blank=True
    )

    table1 = models.ForeignKey(Table, related_name='table1', on_delete=models.CASCADE)
    table2 = models.ForeignKey(Table, related_name='table2', on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('table1', 'table2', 'job_name')  # Ensure no duplicate relationships between the same tables

    def __str__(self):
        return f"{self.job_name}: {self.table1.table_name} -> {self.table2.table_name}"

class TableDetail(models.Model):
    # 1. details_id PK (int)
    details_id = models.AutoField(primary_key=True)
    table = models.ForeignKey(
        Table, 
        on_delete=models.CASCADE, 
        related_name='columns' # Ini agar nanti bisa panggil: table_obj.columns.all()
    )
    column_name = models.CharField(max_length=255)
    column_desc = models.CharField(max_length=255, null=True, blank=True)
    data_type = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        # Opsional: Mencegah nama kolom kembar di dalam satu tabel yang sama
        unique_together = ('table', 'column_name')
        verbose_name = "Table Detail"
        verbose_name_plural = "Table Details"

    def __str__(self):
        return f"{self.column_name} ({self.data_type}) - {self.table.table_name}"

class SchemaCategoryMapping(models.Model):
    mapping_id = models.AutoField(primary_key=True)
    
    schema_name = models.CharField(
        max_length=100, 
        unique=True,
        help_text="Contoh: newdatamart.pst, prod_bm_bda_pst"
    )
    
    # Kita ambil choices langsung dari class Table agar konsisten
    category = models.CharField(
        max_length=100, 
        choices=Table.CATEGORY_CHOICES, 
        default='OTHER'
    )

    class Meta:
        verbose_name = "Schema Mapping"
        verbose_name_plural = "Schema Mappings"

    def __str__(self):
        return f"{self.schema_name} -> {self.category}"

@receiver(pre_save, sender=Table)
def auto_set_category_from_schema(sender, instance, **kwargs):
    """
    Signal ini berjalan otomatis SEBELUM data Table disimpan ke database.
    Kita tidak perlu mengotak-atik method save() di dalam class Table.
    """
    # Hanya jalankan jika table_category masih kosong, 'OTHER', atau None
    if not instance.table_category or instance.table_category == 'OTHER':
        
        # Cek apakah nama tabel mengandung titik (format SCHEMA.TABLE)
        if '.' in instance.table_name:
            # Ambil bagian depan (Schema), misal: 'STG.SALES' -> 'STG'
            extracted_schema = instance.table_name.split('.')[0].upper()
            
            try:
                # Cari settingan di tabel mapping
                mapping = SchemaCategoryMapping.objects.get(schema_name=extracted_schema)
                # Jika ketemu, update category di instance Table
                instance.table_category = mapping.category
            except SchemaCategoryMapping.DoesNotExist:
                # Jika tidak ada mapping, biarkan saja (tetap default/OTHER)
                pass