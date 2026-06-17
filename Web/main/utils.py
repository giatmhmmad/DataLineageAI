# main/utils.py
from django.db import transaction
from django.utils import timezone
from .bot_eda import JobUploadLogs, JobUploadSessions
from .models import Table


def update_job_status(session, status, log_message):
    """
    ✅ Centralized function untuk update status
    Ensures consistency antara sessions dan logs
    
    Args:
        session: JobUploadSessions instance
        status: Status string ('On Progress', 'Success', 'Upload Failed', etc)
        log_message: Log message string
    
    Returns:
        Updated session instance
    """
    with transaction.atomic():
        # Update session current_status
        session.current_status = status
        session.save(update_fields=['current_status'])
        
        # Insert new log
        JobUploadLogs.objects.using('bot_eda').create(
            job=session,
            status=status,
            log_message=log_message,
            update_time=timezone.now()
        )
    
    return session


def get_or_create_table_ids(target_table_raw, mapping_dict):
    clean_names = [name.strip().upper() for name in target_table_raw]
    unique_names = list(set(clean_names))

    schema_to_cat = {s.upper(): cat for cat, schemas in mapping_dict.items() for s in schemas}

    with transaction.atomic():
        existing_objs = Table.objects.filter(table_name__in=unique_names)
        
        
        table_id_map = {obj.table_name: obj.table_id for obj in existing_objs}

        new_objs_to_create = []
        for name in unique_names:
            if name not in table_id_map:
                schema = name.split('.')[0]
                category = schema_to_cat.get(schema, 'OTHER')
                new_objs_to_create.append(
                    Table(table_name=name, table_category=category, table_desc='(Auto Created)')
                )

        if new_objs_to_create:
            Table.objects.bulk_create(new_objs_to_create)
            
            
            new_names = [obj.table_name for obj in new_objs_to_create]
            newly_created_objs = Table.objects.filter(table_name__in=new_names)
            for obj in newly_created_objs:
                table_id_map[obj.table_name] = obj.table_id

    final_id_list = [table_id_map[name] for name in clean_names]
    final_id_list_int = [int(tid) for tid in final_id_list]
    
    return final_id_list_int