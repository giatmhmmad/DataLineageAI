from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('main', '0013_remove_jobdetail_developer_jobdetail_developers_and_more'),  # Sesuaikan dengan migration terakhir
    ]

    operations = [
        # 1. Hapus kolom developer_id yang lama
        migrations.RemoveField(
            model_name='jobdetail',
            name='developer_id',
        ),
        
        # 2. Buat tabel junction untuk ManyToMany
        migrations.CreateModel(
            name='JobDetail_developers',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('jobdetail', models.ForeignKey(on_delete=models.CASCADE, to='main.jobdetail')),
                ('jobdeveloper', models.ForeignKey(on_delete=models.CASCADE, to='main.jobdeveloper')),
            ],
            options={
                'db_table': 'main_jobdetail_developers',
            },
        ),
        
        # 3. Tambah unique constraint
        migrations.AddConstraint(
            model_name='JobDetail_developers',
            constraint=models.UniqueConstraint(
                fields=['jobdetail', 'jobdeveloper'],
                name='unique_jobdetail_developer'
            ),
        ),
    ]