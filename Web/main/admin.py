from django.contrib import admin

from django.contrib import admin
from .models import Table, JobDetail, Relationship, TableDetail, SchemaCategoryMapping


@admin.register(SchemaCategoryMapping)
class SchemaCategoryMappingAdmin(admin.ModelAdmin):
    list_display = ('schema_name', 'category')
    search_fields = ('schema_name',)
