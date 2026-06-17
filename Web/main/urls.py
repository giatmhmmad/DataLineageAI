from django import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from .views import *

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('tables/', table_list, name='table_list'),
    path('tables/create/', create_table, name='create_table'),
    path('tables/edit/<int:table_id>/', edit_table, name='edit_table'),
    path('tables/view/<int:table_id>/', view_table, name='view_table'),
    path('tables/delete/<int:table_id>/', delete_table, name='delete_table'),
    
    path('lineage/', data_lineage, name='data_lineage'),
    path('hello', show_template_page, name='show_template_page'),  # Keep for backward compatibility

    # Relationship URLs
    path('relationships/', relationship_list, name='relationship_list'),
    path('relationships/upload/', upload_relationships, name='upload_relationships'),

    path('jobs/',job_list, name='job_list'),
    path('jobs/view/<int:job_id>/', view_job, name='view_job'),
    path('jobs/view_by_name/<str:job_name>/', view_job_based_on_name, name='view_job_based_on_name'),
    path('jobs/edit/<int:job_id>/', edit_job, name='edit_job'),
    path('jobs/delete/<int:job_id>/', delete_job, name='delete_job'),
    path('jobs/upload/', upload_job, name='upload_job'),
    path('jobs/send_request/', trigger_n8n_webhook, name='send_request'),
    path('jobs/download_jobs_details/<int:job_id>/', download_job_detail_to_excel, name='download_jobs_details'),
    path('api/get-tables/', get_tables, name='get_tables'),
    path('api/n8n/lineage/', receive_n8n_lineage, name='receive_n8n_lineage'),


    path('upload_logs/', upload_logs, name='upload_logs'),

    path('developers/', developer_list, name='developer_list'),
    path('developers/view/<int:developer_id>/', view_developer, name='view_developer'),
    path('developers/edit/<int:developer_id>/', edit_developer, name='edit_developer'),
    path('developers/delete/<int:developer_id>/', delete_developer, name='delete_developer'),
    path('developers/create/', create_developer, name='create_developer'),
    
    # Add more URL patterns as needed
]
