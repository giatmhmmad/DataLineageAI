from urllib import request

from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import connection, transaction
from django.db.models import Q
from django.views.decorators.http import require_GET
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from zoneinfo import ZoneInfo
import json
import csv
import io
import logging
import os
import requests
import io
import openpyxl
from .models import SchemaCategoryMapping, Table, Relationship, JobDetail, TableDetail, JobDeveloper
from .bot_eda import JobUploadLogs, JobUploadSessions, StagingDetectedTables
from .forms import DeveloperForm
from collections import defaultdict
from .utils import update_job_status, get_or_create_table_ids 
from django.db.models import OuterRef, Subquery, F, Q, Max, Count




# Set up logging
logger = logging.getLogger(__name__)

# Create your views here.
def dashboard(request):
    """
    Render the main dashboard with statistics and navigation.
    """
    # Get statistics for the dashboard
    tables_count = Table.objects.count()
    relationships_count = Relationship.objects.count()
    
    # Calculate data sources (unique source tables in relationships)
    data_sources_count = Relationship.objects.values('table1').distinct().count()

    # Calculate job count
    job_count = JobDetail.objects.count()
    
    context = {
        'tables_count': tables_count,
        'relationships_count': relationships_count,
        'data_sources_count': data_sources_count,
        'job_count': job_count,
    }
    return render(request, 'dashboard.html', context)

def table_list(request):
    """
    Render the table list page with search functionality.
    """
    # 1. Ambil kata kunci pencarian dari URL
    search_query = request.GET.get('q', '')
    category_query = request.GET.get('category', '')

    # 2. Ambil semua data awal
    tables = get_all_tables(request)
    
    # Hitung jumlah untuk tiap kategori sebelum filter diaplikasikan
    category_counts = {
        'all': 0,
        'datamart': 0,
        'staging': 0,
        'source_data': 0,
        'other': 0
    }
    
    try:
        # Jika tables adalah QuerySet
        category_counts['all'] = tables.count()
        category_counts['datamart'] = tables.filter(table_category='DATAMART').count()
        category_counts['staging'] = tables.filter(table_category='STAGING').count()
        category_counts['source_data'] = tables.filter(table_category='SOURCE DATA').count()
        category_counts['other'] = tables.filter(table_category='OTHER').count()
    except AttributeError:
        # Jika tables adalah list biasa
        category_counts['all'] = len(tables)
        category_counts['datamart'] = sum(1 for t in tables if getattr(t, 'table_category', '') == 'DATAMART')
        category_counts['staging'] = sum(1 for t in tables if getattr(t, 'table_category', '') == 'STAGING')
        category_counts['source_data'] = sum(1 for t in tables if getattr(t, 'table_category', '') == 'SOURCE DATA')
        category_counts['other'] = sum(1 for t in tables if getattr(t, 'table_category', '') == 'OTHER')

    # 3. Lakukan filter jika ada kata kunci pencarian atau kategori
    try:
        if search_query:
            tables = tables.filter(
                Q(table_name__icontains=search_query) |  # Cari di Nama Tabel
                Q(table_id__icontains=search_query)      # Cari di ID Tabel
            )
        if category_query:
            tables = tables.filter(table_category=category_query)
        current_count = tables.count()
    except AttributeError:
        # JAGA-JAGA: Jika get_all_tables mengembalikan "List" Python biasa (bukan QuerySet)
        # Kita gunakan filter manual Python
        if search_query:
            tables = [
                t for t in tables 
                if search_query.lower() in t.table_name.lower() 
                or search_query.lower() in str(t.table_id).lower()
            ]
        if category_query:
            tables = [
                t for t in tables
                if getattr(t, 'table_category', '') == category_query
            ]
        current_count = len(tables)

    context = {
        'tables': tables,
        'search_query': search_query, # Kirim balik ke template agar input text tidak hilang
        'category_query': category_query, # Kirim category agar UI tahu mana yang aktif
        'category_counts': category_counts,
        'current_count': current_count,
    }
    
    return render(request, 'table_list.html', context)

def data_lineage(request):
    """
    Render the data lineage page.
    Only passes minimal metadata – full graph data is fetched lazily via AJAX.
    """
    tables = Table.objects.annotate(
        incoming_count=Count('table2', distinct=True),
        outgoing_count=Count('table1', distinct=True),
    ).order_by('table_name')

    relationships_count = Relationship.objects.count()

    # Minimal table list for autocomplete (id, name, category, connection_count)
    tables_data = [
        {
            'id': t.table_id,
            'name': t.table_name,
            'category': t.table_category or 'OTHER',
            'connection_count': t.incoming_count + t.outgoing_count,
        }
        for t in tables
    ]

    # Top-5 most connected tables for "popular" suggestions
    popular = sorted(tables_data, key=lambda x: x['connection_count'], reverse=True)[:5]

    context = {
        'tables': tables,
        'relationships_count': relationships_count,
        'tables_json': json.dumps(tables_data),
        'popular_json': json.dumps(popular),
    }
    return render(request, 'data_lineage.html', context)


@require_GET
def api_search_tables(request):
    """
    AJAX: Search tables by name with optional category filter.
    Returns paginated JSON list for autocomplete dropdown.
    """
    query    = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    limit    = min(int(request.GET.get('limit', 30)), 100)

    tables = Table.objects.annotate(
        incoming_count=Count('table2', distinct=True),
        outgoing_count=Count('table1', distinct=True),
    )

    if query:
        tables = tables.filter(table_name__icontains=query)
    if category and category != 'ALL':
        tables = tables.filter(table_category=category)

    tables = tables.order_by('-incoming_count', '-outgoing_count', 'table_name')[:limit]

    data = [
        {
            'id': t.table_id,
            'name': t.table_name,
            'category': t.table_category or 'OTHER',
            'connection_count': t.incoming_count + t.outgoing_count,
            'incoming_count': t.incoming_count,
            'outgoing_count': t.outgoing_count,
        }
        for t in tables
    ]
    return JsonResponse({'tables': data})


@require_GET
def api_get_lineage(request, table_id):
    """
    AJAX: Return lineage nodes + edges for a specific focus table.
    Traverses upstream (sources) and downstream (targets) up to depth_limit levels.
    """
    try:
        focus_table = Table.objects.get(table_id=table_id)
    except Table.DoesNotExist:
        return JsonResponse({'error': 'Table not found'}, status=404)

    depth_limit_raw = request.GET.get('depth', '')
    depth_limit = int(depth_limit_raw) if depth_limit_raw.isdigit() else None

    # Load all relationships into memory for traversal (avoids N+1 queries)
    all_rels = list(
        Relationship.objects.select_related('table1', 'table2')
        .values('table1_id', 'table2_id', 'job_name')
    )

    # Build adjacency maps
    downstream_map = {}  # source_id -> [(target_id, job_name)]
    upstream_map   = {}  # target_id -> [(source_id, job_name)]
    for r in all_rels:
        downstream_map.setdefault(r['table1_id'], []).append((r['table2_id'], r['job_name']))
        upstream_map.setdefault(r['table2_id'], []).append((r['table1_id'], r['job_name']))

    # Iterative BFS traversal – safe for large/cyclic graphs
    included_nodes = {}  # table_id -> depth (0=focus, negative=upstream, positive=downstream)
    included_edges = []  # list of {source, target, job_name, direction}

    included_nodes[table_id] = 0

    from collections import deque

    # ── Upstream BFS ──────────────────────────────────────────────
    visited_up = {table_id}
    queue = deque([(table_id, 0)])
    while queue:
        tid, depth = queue.popleft()
        for (src_id, job) in upstream_map.get(tid, []):
            new_depth = depth - 1
            if depth_limit is not None and abs(new_depth) > depth_limit:
                continue
            included_edges.append({'source': src_id, 'target': tid, 'job_name': job, 'direction': 'upstream'})
            if src_id not in visited_up:
                visited_up.add(src_id)
                if src_id not in included_nodes:
                    included_nodes[src_id] = new_depth
                queue.append((src_id, new_depth))

    # ── Downstream BFS ────────────────────────────────────────────
    visited_down = {table_id}
    queue = deque([(table_id, 0)])
    while queue:
        tid, depth = queue.popleft()
        for (tgt_id, job) in downstream_map.get(tid, []):
            new_depth = depth + 1
            if depth_limit is not None and new_depth > depth_limit:
                continue
            included_edges.append({'source': tid, 'target': tgt_id, 'job_name': job, 'direction': 'downstream'})
            if tgt_id not in visited_down:
                visited_down.add(tgt_id)
                if tgt_id not in included_nodes:
                    included_nodes[tgt_id] = new_depth
                queue.append((tgt_id, new_depth))

    # Deduplicate edges (keep unique source-target-job combos)
    seen_edges = set()
    unique_edges = []
    for e in included_edges:
        key = (e['source'], e['target'], e['job_name'])
        if key not in seen_edges:
            seen_edges.add(key)
            unique_edges.append(e)

    # Fetch table metadata for included nodes
    node_ids = list(included_nodes.keys())
    node_qs = Table.objects.filter(table_id__in=node_ids).annotate(
        incoming_count=Count('table2', distinct=True),
        outgoing_count=Count('table1', distinct=True),
    )

    # Collect upstream/downstream job names per node for rich tooltip
    upstream_jobs_map   = {}   # table_id -> {source_id: [job_names]}
    downstream_jobs_map = {}   # table_id -> {target_id: [job_names]}
    for e in unique_edges:
        downstream_jobs_map.setdefault(e['source'], {}).setdefault(e['target'], []).append(e['job_name'])
        upstream_jobs_map.setdefault(e['target'], {}).setdefault(e['source'], []).append(e['job_name'])

    nodes = []
    for t in node_qs:
        depth = included_nodes[t.table_id]
        nodes.append({
            'id': t.table_id,
            'name': t.table_name,
            'category': t.table_category or 'OTHER',
            'connection_count': t.incoming_count + t.outgoing_count,
            'incoming_count': t.incoming_count,
            'outgoing_count': t.outgoing_count,
            'depth': depth,
            'is_focus': t.table_id == table_id,
        })

    return JsonResponse({
        'focus_id': table_id,
        'focus_name': focus_table.table_name,
        'nodes': nodes,
        'edges': unique_edges,
        'upstream_count': sum(1 for d in included_nodes.values() if d < 0),
        'downstream_count': sum(1 for d in included_nodes.values() if d > 0),
    })

def show_template_page(request):
    """
    Render the template page (deprecated - use dashboard instead).
    """
    return render(request, 'template_page.html')

def get_all_tables(request):
    """
    Fetch and return all tables from the database, sorted by table_id.
    """
    
    tables = Table.objects.all().order_by('table_id')
    return tables

@require_http_methods(["GET", "POST"])
def create_table(request):
    """
    Handle the creation of new tables via CSV upload OR Manual Input.
    """
    if request.method == 'POST':
        action_type = request.POST.get('action_type')
        
        # ==========================================
        # 1. LOGIC MANUAL CREATE
        # ==========================================
        if action_type == 'manual_create':
            try:
                # Ambil data dari form
                table_name = request.POST.get('table_name', '').strip().upper()
                table_category = request.POST.get('table_category', 'OTHER')
                table_desc = request.POST.get('table_desc', '').strip()

                # Validasi field wajib
                if not table_name:
                    return JsonResponse({'success': False, 'error': 'Table name is required'}, status=400)

                # Validasi duplikasi nama tabel
                if Table.objects.filter(table_name=table_name).exists():
                    return JsonResponse({'success': False, 'error': f'Table "{table_name}" already exists'}, status=400)

                # Simpan ke Database
                new_table = Table.objects.create(
                    table_name=table_name,
                    table_category=table_category,
                    table_desc=table_desc
                )

                # Kembalikan response sukses standar
                return JsonResponse({
                    'success': True, 
                    'message': f'Table "{table_name}" created successfully',
                    'created_tables': [{
                        'table_name': new_table.table_name,
                        'table_category': new_table.table_category,
                        'table_desc': new_table.table_desc
                    }],
                    'error_count': 0
                })

            except Exception as e:
                logger.error(f"Error creating table manually: {str(e)}")
                return JsonResponse({'success': False, 'error': str(e)}, status=500)

        # ==========================================
        # 2. LOGIC UPLOAD CSV
        # ==========================================
        elif action_type == 'upload_csv':
            try:
                logger.info(f"POST request received for CSV upload from {request.META.get('REMOTE_ADDR')}")

                # Cek keberadaan file
                if 'csv_file' not in request.FILES:
                    logger.error("No CSV file uploaded")
                    return JsonResponse({'success': False, 'error': 'No CSV file uploaded'}, status=400)
                
                csv_file = request.FILES['csv_file']
                
                # Validasi tipe file
                if not csv_file.name.endswith('.csv'):
                    logger.error(f"Invalid file type: {csv_file.name}")
                    return JsonResponse({'success': False, 'error': 'Please upload a CSV file'}, status=400)
                
                try:
                    # Baca file (Gunakan utf-8-sig untuk menangani BOM excel)
                    file_data = csv_file.read().decode('utf-8-sig')
                    csv_reader = csv.DictReader(io.StringIO(file_data))
                    
                    # Normalisasi Header CSV (hilangkan spasi, jadikan lowercase biar aman)
                    # Ini agar user bisa upload header "Table Name" atau "table_name"
                    original_headers = csv_reader.fieldnames or []
                    headers_map = {h.strip().lower().replace(' ', '_'): h for h in original_headers}
                    
                    # Cek kolom wajib (Hanya table_name yang wajib sekarang)
                    # Kita support 'table_name' (format baru) atau 'table_name' (format lama)
                    key_table_name = headers_map.get('table_name') or headers_map.get('tablename')

                    if not key_table_name:
                        return JsonResponse({
                            'success': False,
                            'error': 'CSV must contain "table_name" column'
                        }, status=400)
                    
                    created_tables = []
                    errors = []
                    
                    # Loop baris per baris
                    for row_num, row in enumerate(csv_reader, start=2):
                        # Ambil data menggunakan key asli dari CSV
                        t_name = row.get(key_table_name, '').strip()
                        
                        # Ambil optional fields (Category & Desc & ID)
                        # Cari key yang cocok di header map
                        key_cat = headers_map.get('table_category') or headers_map.get('category')
                        key_desc = headers_map.get('table_desc') or headers_map.get('description')
                        key_id = headers_map.get('table_id') or headers_map.get('id')

                        t_cat = row.get(key_cat, 'OTHER').strip() if key_cat else 'OTHER'
                        t_desc = row.get(key_desc, '').strip() if key_desc else ''
                        t_id = row.get(key_id, '').strip() if key_id else None
                        
                        # Validasi Nama Kosong
                        if not t_name:
                            errors.append(f'Row {row_num}: Table name is required')
                            continue
                        
                        # Validasi Duplikasi Nama
                        if Table.objects.filter(table_name=t_name).exists():
                            errors.append(f'Row {row_num}: Table "{t_name}" already exists')
                            continue
                        
                        try:
                            # Siapkan data dictionary
                            table_data = {
                                'table_name': t_name,
                                'table_category': t_cat,
                                'table_desc': t_desc
                            }

                            # Logic ID: Jika di CSV ada ID, pakai itu. Jika tidak, biarkan AutoField
                            if t_id and t_id.isdigit():
                                if Table.objects.filter(table_id=int(t_id)).exists():
                                    errors.append(f'Row {row_num}: ID {t_id} already used')
                                    continue
                                table_data['table_id'] = int(t_id)

                            # Create Table
                            new_table = Table.objects.create(**table_data)
                            
                            created_tables.append({
                                'table_id': new_table.table_id,
                                'table_name': new_table.table_name,
                                'table_category': new_table.table_category,
                                'table_desc': new_table.table_desc
                            })

                        except Exception as e:
                            errors.append(f'Row {row_num}: Error creating "{t_name}" - {str(e)}')
                    
                    # Susun Response Akhir
                    response_data = {
                        'success': True,
                        'created_count': len(created_tables),
                        'created_tables': created_tables,
                        'error_count': len(errors),
                        'errors': errors
                    }
                    
                    # Tentukan pesan status
                    if errors and not created_tables:
                        response_data['success'] = False
                        response_data['error'] = 'Failed to create any tables. See errors list.'
                    elif errors:
                        response_data['message'] = f'Partially successful: {len(created_tables)} tables created, {len(errors)} errors.'
                    else:
                        response_data['message'] = f'Successfully created {len(created_tables)} tables.'
                    
                    return JsonResponse(response_data)
                    
                except UnicodeDecodeError:
                    return JsonResponse({'success': False, 'error': 'Invalid CSV encoding. Please save as UTF-8.'}, status=400)
                except Exception as e:
                    return JsonResponse({'success': False, 'error': f'Error reading CSV: {str(e)}'}, status=400)

            except Exception as e:
                logger.error(f"Server Error during CSV upload: {str(e)}")
                return JsonResponse({'success': False, 'error': f'Server Error: {str(e)}'}, status=500)

        # Jika action_type tidak dikenali
        else:
             return JsonResponse({'success': False, 'error': 'Invalid action type'}, status=400)

    # GET request render page
    return render(request, 'create_table.html')

def edit_table(request, table_id):
    table = get_object_or_404(Table, table_id=table_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 1. Update Data Table Utama
                new_table_name = request.POST.get('table_name', '').strip().upper()
                new_category = request.POST.get('table_category')
                new_desc = request.POST.get('table_desc', '').strip()
                
                if not new_table_name:
                    return JsonResponse({'success': False, 'error': 'Table name is required'})
                
                if Table.objects.filter(table_name=new_table_name).exclude(table_id=table_id).exists():
                    return JsonResponse({'success': False, 'error': 'Table name already exists'})
                
                table.table_name = new_table_name
                if new_category: table.table_category = new_category
                table.table_desc = new_desc
                table.save()
                
                # 2. Handle Hapus Data (Deleted IDs)
                deleted_ids_json = request.POST.get('deleted_col_ids')
                if deleted_ids_json:
                    try:
                        deleted_ids = json.loads(deleted_ids_json)
                        if deleted_ids:
                            TableDetail.objects.filter(details_id__in=deleted_ids, table_id=table.table_id).delete()
                    except:
                        pass 

                # 3. Handle Tambah & Edit Kolom
                col_ids = request.POST.getlist('col_id[]')
                col_names = request.POST.getlist('col_name[]')
                col_types = request.POST.getlist('col_type[]')
                col_descs = request.POST.getlist('col_desc[]')

                # Set untuk mengecek duplikat di dalam Form itu sendiri (misal user input "ID" dua kali di form)
                processed_names = set()

                for i in range(len(col_ids)):
                    c_id = col_ids[i]
                    c_name = col_names[i].strip() # Case sensitive? kalau tidak, tambah .upper() atau .lower()
                    c_type = col_types[i].strip()
                    c_desc = col_descs[i].strip()

                    if not c_name:
                        continue
                    
                    # --- VALIDASI 1: Cek duplikat di input form user saat ini ---
                    if c_name in processed_names:
                        raise Exception(f"Duplicate column name '{c_name}' in your input list.")
                    processed_names.add(c_name)

                    # --- VALIDASI 2: Cek duplikat di Database ---
                    # Cek apakah nama ini sudah dipakai oleh ID LAIN di tabel yang sama
                    duplicate_check = TableDetail.objects.filter(
                        table_id=table.table_id, 
                        column_name=c_name
                    )
                    
                    if c_id != 'new':
                        # Jika update, exclude diri sendiri dari pengecekan
                        duplicate_check = duplicate_check.exclude(details_id=c_id)
                    
                    if duplicate_check.exists():
                        raise Exception(f"Column name '{c_name}' already exists in this table.")

                    # --- EKSEKUSI SIMPAN ---
                    if c_id == 'new':
                        TableDetail.objects.create(
                            table_id=table.table_id,
                            column_name=c_name,
                            data_type=c_type,
                            column_desc=c_desc
                        )
                    else:
                        TableDetail.objects.filter(details_id=c_id, table_id=table.table_id).update(
                            column_name=c_name,
                            data_type=c_type,
                            column_desc=c_desc
                        )
            
            return JsonResponse({
                'success': True, 
                'message': f'Table "{new_table_name}" updated successfully!'
            })
            
        except Exception as e:
            # Error ini akan ditangkap Javascript dan ditampilkan di alert merah
            return JsonResponse({'success': False, 'error': str(e)})
    
    # GET Request
    columns = TableDetail.objects.filter(table_id=table_id).order_by('details_id')
    context = {'table': table, 'columns': columns}
    return render(request, 'edit_table.html', context)

def view_table(request, table_id):
    """
    Display detailed view of a table with its relationships.
    """
    try:
        table = Table.objects.get(table_id=table_id)
    except Table.DoesNotExist:
        messages.error(request, 'Table not found')
        return redirect('table_list')
    
    # Get relationships where this table is the source (outgoing)
    outgoing_relationships = Relationship.objects.filter(table1=table).select_related('table2')
    
    # Get relationships where this table is the target (incoming)
    incoming_relationships = Relationship.objects.filter(table2=table).select_related('table1')
    
    columns = TableDetail.objects.filter(table_id=table_id).order_by('details_id')

    context = {
        'table': table,
        'columns': columns,
        'outgoing_relationships': outgoing_relationships,
        'incoming_relationships': incoming_relationships,
        'total_relationships': outgoing_relationships.count() + incoming_relationships.count()
    }
    return render(request, 'view_table.html', context)

def delete_table(request, table_id):
    """
    Handle deletion of a table.
    """
    try:
        table = Table.objects.get(table_id=table_id)
    except Table.DoesNotExist:
        messages.error(request, 'Table not found')
        return redirect('table_list')
    
    if request.method == 'POST':
        table_name = table.table_name
        table.delete()
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT setval(
                    pg_get_serial_sequence('main_table', 'table_id'), 
                    COALESCE((SELECT MAX(table_id) FROM main_table), 1)
                );
            """)
        messages.success(request, f'Table "{table_name}" has been deleted successfully')
        return redirect('table_list')
    
    # If GET request, redirect to table list
    return redirect('table_list')


@csrf_exempt 
def upload_relationships(request):
    """
    Handle the upload of relationships via CSV.
    CSV should contain columns: Job Name, Target Table Name, Source Table Names
    Source Table Names can be comma-separated for multiple sources.
    """
    if request.method == 'POST':
        try:
            # Check if file was uploaded
            if 'csv_file' not in request.FILES:
                return JsonResponse({'error': 'No CSV file uploaded'}, status=400)
            
            csv_file = request.FILES['csv_file']
            
            # Validate file type
            if not csv_file.name.endswith('.csv'):
                return JsonResponse({'error': 'Please upload a CSV file'}, status=400)
            
            # Read and parse CSV file
            try:
                file_data = csv_file.read().decode('utf-8')
                csv_reader = csv.DictReader(io.StringIO(file_data))
                
                # Check if required columns exist
                required_columns = ['Job Name', 'Target Table Name', 'Source Table Names']
                missing_columns = [col for col in required_columns if col not in csv_reader.fieldnames]
                
                if missing_columns:
                    return JsonResponse({
                        'error': f'CSV must contain the following columns: {", ".join(missing_columns)}'
                    }, status=400)
                
                created_relationships = []
                errors = []
                
                for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 because row 1 is header
                    job_name = row.get('Job Name', '').strip()
                    target_table_name = row.get('Target Table Name', '').strip()
                    source_table_names = row.get('Source Table Names', '').strip()
                    
                    # Validate required fields
                    if not job_name:
                        errors.append(f'Row {row_num}: Job Name is required')
                        continue
                    
                    if not target_table_name:
                        errors.append(f'Row {row_num}: Target Table Name is required')
                        continue
                    
                    if not source_table_names:
                        errors.append(f'Row {row_num}: Source Table Names is required')
                        continue

                    # [TAMBAHAN BARU 1]: Logic JobDetail
                    try:
                        # Cari JobDetail berdasarkan nama, kalau belum ada -> Buat Baru
                        job_obj, created = JobDetail.objects.get_or_create(
                            job_name=job_name,
                            defaults={'pic_job': '-'} # Default PIC jika baru
                        )
                    except Exception as e:
                        errors.append(f'Row {row_num}: Error processing Job Detail - {str(e)}')
                        continue

                    # Find target table
                    try:
                        target_table = Table.objects.get(table_name=target_table_name)
                    except Table.DoesNotExist:
                        errors.append(f'Row {row_num}: Target table "{target_table_name}" does not exist')
                        continue
                    
                    # Parse source table names (split by comma and strip spaces)
                    source_names = [name.strip() for name in source_table_names.split(',') if name.strip()]
                    
                    if not source_names:
                        errors.append(f'Row {row_num}: No valid source table names found')
                        continue
                    
                    # Create relationships for each source table
                    row_relationships = []
                    for source_name in source_names:
                        try:
                            source_table = Table.objects.get(table_name=source_name)
                        except Table.DoesNotExist:
                            errors.append(f'Row {row_num}: Source table "{source_name}" does not exist')
                            continue
                        
                        # Check if relationship already exists
                        if Relationship.objects.filter(
                            job_name=job_name,
                            table1=source_table,
                            table2=target_table
                        ).exists():
                            errors.append(f'Row {row_num}: Relationship from "{source_name}" to "{target_table_name}" with job "{job_name}" already exists')
                            continue
                        
                        # Create the relationship
                        try:
                            relationship = Relationship.objects.create(
                                job_name=job_name,
                                job=job_obj,
                                table1=source_table,  # source
                                table2=target_table   # target
                            )
                            row_relationships.append({
                                'job_name': job_name,
                                'source_table': source_name,
                                'target_table': target_table_name
                            })
                        except Exception as e:
                            errors.append(f'Row {row_num}: Error creating relationship from "{source_name}" to "{target_table_name}" - {str(e)}')
                    
                    created_relationships.extend(row_relationships)
                
                # Return response with results
                response_data = {
                    'success': True,
                    'created_count': len(created_relationships),
                    'created_relationships': created_relationships,
                    'error_count': len(errors),
                    'errors': errors
                }
                
                if errors:
                    response_data['message'] = f'Processed CSV: {len(created_relationships)} relationships created, {len(errors)} errors'
                else:
                    response_data['message'] = f'Successfully created {len(created_relationships)} relationships'
                
                return JsonResponse(response_data)
                
            except Exception as e:
                return JsonResponse({'error': f'Error reading CSV file: {str(e)}'}, status=400)
            
        except Exception as e:
            return JsonResponse({'error': f'Error processing request: {str(e)}'}, status=500)
    
    # GET request - render the upload form
    return render(request, 'upload_relationships.html')

@csrf_exempt
@require_http_methods(["POST"])
def receive_n8n_lineage(request):
    """
    Handle lineage data from n8n webhook.
    Receives JSON array with source table information and creates relationships.
    
    Expected JSON format:
    [
        {
            "source_table_name": "SCHEMA.TABLE_NAME",
            "source_table_category": "DATAMART|SOURCE DATA|STAGING|OTHER",
            "schema_name": "SCHEMA",
            "table_name": "TABLE_NAME",
            "JobName": "Job Name",
            "PICJob": ["developer_id, developer_id,..."],
            "FinalTable": [4, 6, 8, 10],  # List of target table IDs
            "job_id": 49
        },
        ...
    ]
    
    The function will:
    1. Create/retrieve JobDetail
    2. Create/retrieve tables for all sources
    3. Extract target table information from FinalTable (list of table IDs)
    4. Create relationships from sources to targets
    """
    try:
        # Parse JSON body
        try:
            request_data = json.loads(request.body)
            
            # Ensure we have a list
            if not isinstance(request_data, list):
                return JsonResponse({'error': 'Request body must be a JSON array'}, status=400)
            
            if len(request_data) == 0:
                return JsonResponse({'error': 'No data provided in request'}, status=400)
                
        except json.JSONDecodeError as e:
            return JsonResponse({'error': f'Invalid JSON: {str(e)}'}, status=400)
        
        # Extract common fields from first item (should be same for all rows)
        first_item = request_data[0]
        job_name = first_item.get('JobName', '').strip()
        job_id = first_item.get('job_id')
        pic_job = first_item.get('PICJob', '-')
        
        # Validate required fields
        if not job_name:
            return JsonResponse({'error': 'JobName is required in request data'}, status=400)
        
        created_relationships = []
        errors = []
        created_tables = []
        assigned_developers = []  # ✅ Track assigned developers
        skipped_self_relationships = 0
        
        # Step 1: Create or get JobDetail
        job_created = False
        try:
            job_obj, job_created = JobDetail.objects.get_or_create(
                job_name=job_name,
                defaults={'pic_job': str(pic_job) if pic_job and pic_job != '-' else None}
            )
            
            if job_created:
                logger.info(f'✅ Created new JobDetail: "{job_name}"')
                
        except Exception as e:
            return JsonResponse({
                'error': f'Error creating/retrieving JobDetail: {str(e)}',
                'success': False
            }, status=500)
        
        # Step 1.5: Assign Developers to JobDetail
        if job_obj and pic_job:
            try:
                # Parse PICJob - bisa berupa list of ints atau list of strings
                developer_ids = []
                if isinstance(pic_job, list):
                    # pic_job is already a list: [8] or ["8"]
                    developer_ids = [int(dev_id) for dev_id in pic_job]
                elif isinstance(pic_job, str):
                    # pic_job is string: "8" or "[8]"
                    # Remove brackets if present
                    cleaned = pic_job.strip('[]').strip()
                    if cleaned and cleaned != '-':
                        # Split by comma if multiple IDs
                        developer_ids = [int(dev_id.strip()) for dev_id in cleaned.split(',') if dev_id.strip()]
                
                if developer_ids:
                    # Get JobDeveloper objects
                    developers = JobDeveloper.objects.filter(developer_id__in=developer_ids)
                    
                    if developers.exists():
                        # Clear existing and set new developers
                        job_obj.developers.set(developers)
                        
                        # Track assigned developers
                        assigned_developers = [
                            {
                                'developer_id': dev.developer_id,
                                'developer_name': dev.developer_name,
                                'department': dev.department
                            }
                            for dev in developers
                        ]
                        
                        logger.info(f'Assigned {developers.count()} developer(s) to job "{job_name}"')
                    else:
                        errors.append(f'No developers found with IDs: {developer_ids}')
                        
            except (ValueError, TypeError) as e:
                errors.append(f'Error processing PICJob field: {str(e)}')
       
        # Step 2: Process lineage data
        source_tables = {}  # {source_table_name: table_obj}
        target_tables = {}  # {target_table_name: table_obj}
        relationships_to_create = []  # [(source_obj, target_obj, target_table_name)]
        
        for row_num, row in enumerate(request_data, start=1):
            source_table_name = row.get('source_table_name', '').strip()
            source_table_category = row.get('source_table_category', 'OTHER').strip()
            
            if not source_table_name:
                errors.append(f'Row {row_num}: source_table_name is required')
                continue
            
            # Normalize category
            if source_table_category not in dict(Table.CATEGORY_CHOICES):
                source_table_category = 'OTHER'
            
            # Create or get source table
            if source_table_name not in source_tables:
                try:
                    source_obj, source_created = Table.objects.get_or_create(
                        table_name=source_table_name,
                        defaults={
                            'table_category': source_table_category,
                            'table_desc': f"Auto-created from n8n lineage for job '{job_name}'"
                        }
                    )
                    
                    # Update category if table exists but category is different
                    if not source_created and source_obj.table_category != source_table_category:
                        source_obj.table_category = source_table_category
                        source_obj.save()
                    
                    source_tables[source_table_name] = source_obj
                    
                    if source_created:
                        created_tables.append({
                            'table_name': source_table_name,
                            'table_category': source_table_category,
                            'type': 'source'
                        })
                        
                except Exception as e:
                    errors.append(f'Row {row_num}: Error creating/retrieving source table "{source_table_name}" - {str(e)}')
                    continue
            else:
                source_obj = source_tables[source_table_name]
            
            # Process FinalTable to extract target tables
            final_table_data = row.get('FinalTable', [])
            
            if not final_table_data:
                errors.append(f'Row {row_num}: FinalTable is empty for source "{source_table_name}"')
                continue
            
            # Loop through all target table IDs
            for target_table_id in final_table_data:
                try:
                    # Get target table by ID
                    target_table_obj = Table.objects.get(table_id=target_table_id)
                    
                    # Store target table
                    if target_table_obj.table_name not in target_tables:
                        target_tables[target_table_obj.table_name] = target_table_obj
                    
                    # Add to relationships list
                    relationships_to_create.append((
                        source_obj, 
                        target_table_obj, 
                        target_table_obj.table_name
                    ))
                    
                except Table.DoesNotExist:
                    errors.append(f'Row {row_num}: Target table with ID {target_table_id} does not exist')
                except Exception as e:
                    errors.append(f'Row {row_num}: Error processing target table ID {target_table_id} - {str(e)}')
        
        # Step 3: Create relationships
        # ✅ CRITICAL: Ensure job_obj exists before creating relationships
        if not job_obj:
            return JsonResponse({
                'error': f'JobDetail with job_name "{job_name}" could not be created or retrieved',
                'success': False,
                'details': 'Relationships require a valid JobDetail. Please check if JobDetail was created.'
            }, status=500)
        
        for source_obj, target_table_obj, target_table_name in relationships_to_create:
            try:
                if (
                    source_obj.table_id == target_table_obj.table_id
                    or source_obj.table_name.strip().upper() == target_table_obj.table_name.strip().upper()
                ):
                    skipped_self_relationships += 1
                    continue

                # Check if relationship already exists
                existing = Relationship.objects.filter(
                    job_name=job_name,
                    table1=source_obj,
                    table2=target_table_obj
                ).exists()
                
                if existing:
                    errors.append(f'Relationship from "{source_obj.table_name}" to "{target_table_obj.table_name}" already exists for job "{job_name}"')
                    continue
                
                # Create the relationship
                relationship = Relationship.objects.create(
                    job_name=job_name,
                    job=job_obj,
                    table1=source_obj,  # source
                    table2=target_table_obj   # target
                )
                
                created_relationships.append({
                    'job_name': job_name,
                    'source_table': source_obj.table_name,
                    'target_table': target_table_obj.table_name,
                    'status': 'created'
                })
                
            except Exception as e:
                errors.append(f'Error creating relationship from "{source_obj.table_name}" to "{target_table_obj.table_name}": {str(e)}')
        
        # Step 4: Build response
        response_data = {
            'success': len(errors) == 0,
            'message': f'Processed: {len(source_tables)} sources, {len(created_relationships)} relationships, {len(assigned_developers)} developers assigned' + (f', {skipped_self_relationships} self-relationships skipped' if skipped_self_relationships else '') + (', JobDetail created' if job_created else ''),
            'job_name': job_name,
            'job_id': job_id,
            'job_created': job_created,  # ✅ NEW
            'sources_processed': len(source_tables),
            'relationships_created': len([r for r in created_relationships if r.get('status') == 'created']),
            'new_tables_created': len(created_tables),
            'developers_assigned': len(assigned_developers),
            'self_relationships_skipped': skipped_self_relationships,
            'created_tables': created_tables,
            'created_relationships': created_relationships,
            'assigned_developers': assigned_developers,
            'error_count': len(errors),
            'errors': errors if errors else []
        }
        
        return JsonResponse(response_data, status=200 if response_data['success'] else 207)
        
    except Exception as e:
        logger.exception(f'Error in receive_n8n_lineage: {str(e)}')
        return JsonResponse({
            'error': f'Error processing request: {str(e)}',
            'success': False
        }, status=500)



def relationship_list(request):
    """
    Display all relationships with search functionality.
    """
    # 1. Ambil kata kunci pencarian dari URL (name="q" di HTML)
    search_query = request.GET.get('q', '')

    # 2. Query dasar (dengan select_related agar performa cepat)
    relationships = Relationship.objects.select_related('table1', 'table2').all()

    # 3. Logika Filter Search
    if search_query:
        relationships = relationships.filter(
            Q(job_name__icontains=search_query) |               # Cari di Nama Job
            Q(table1__table_name__icontains=search_query) |     # Cari di Nama Table Source
            Q(table2__table_name__icontains=search_query)       # Cari di Nama Table Target
        )

    # 4. Ordering (Urutkan hasil)
    relationships = relationships.order_by('job_name', 'table1__table_name')
    
    context = {
        'relationships': relationships,
        'search_query': search_query  # Kirim balik agar input text tidak hilang setelah reload
    }
    
    return render(request, 'relationship_list.html', context)

def job_list(request):
    """
    Menampilkan daftar Job beserta statistik otomatisnya dengan fitur Search.
    """
    # 1. Ambil kata kunci dari URL (name="q" di HTML)
    search_query = request.GET.get('q', '')

    # 2. Query dasar (Ambil semua)
    jobs = JobDetail.objects.all().order_by('job_name')
    
    
    # 3. Logika Filter
    if search_query:
        jobs = jobs.filter(
            Q(job_name__icontains=search_query) |       # Cari berdasarkan Nama Job
            Q(job_id__icontains=search_query)   |       # Cari berdasarkan ID Job (Opsional, jika ada field ini)
            Q(relationships__table2__table_name__icontains=search_query)   # Cari berdasarkan Nama Table Target di Relationship 
        ).distinct()
    context = {
        'jobs': jobs,
        'search_query': search_query  # Dikirim balik ke HTML agar input box tidak kosong setelah reload
    }
    
    return render(request, 'job_list.html', context)

def view_job(request, job_id):
    """
    Display detailed view of a job with its relationships.
    """
    try:
        job = JobDetail.objects.get(job_id=job_id)
    except JobDetail.DoesNotExist:
        messages.error(request, 'Job not found')
        return redirect('job_list')
    
    relationships = Relationship.objects.filter(job=job).select_related('table1', 'table2')
    target_tables = set(rel.table2 for rel in relationships if rel.table2)
    source_tables = set(rel.table1 for rel in relationships if rel.table1)
    source_tables = sorted(source_tables, key=lambda x: x.table_category if x.table_category else "zzzz")
    
    context = {
        'job': job,
        'target_tables': target_tables,
        'source_tables': source_tables,
    }
    return render(request, 'view_job.html', context)

def view_job_based_on_name(request, job_name):
    """
    Display detailed view of a job with its relationships.
    """
    try:
        job = JobDetail.objects.get(job_name=job_name)
    except JobDetail.DoesNotExist:
        messages.error(request, 'Job not found')
        return redirect('job_list')
    
    relationships = Relationship.objects.filter(job=job).select_related('table1', 'table2')
    target_tables = set(rel.table2 for rel in relationships if rel.table2)
    source_tables = set(rel.table1 for rel in relationships if rel.table1)
    source_tables = sorted(source_tables, key=lambda x: x.table_category if x.table_category else "zzzz")

    context = {
        'job': job,
        'target_tables': target_tables,
        'source_tables': source_tables,
    }
    return render(request, 'view_job.html', context)

def download_job_detail_to_excel(request, job_id):
    """
    Download job details and relationships as an Excel file.
    """
    try:
        job = JobDetail.objects.get(job_id=job_id)
    except JobDetail.DoesNotExist:
        messages.error(request, 'Job not found')
        return redirect('job_list')
    
    relationships = Relationship.objects.filter(job=job).select_related('table1', 'table2')
    
    # Create an in-memory Excel file
    output = io.BytesIO()
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = f'Job_{job.job_name}_Details'
    
    # Write header
    headers = ['Job Name', 'Target Table', 'Source Table', 'Source Table Category']
    sheet.append(headers)
    
    # Write data rows
    for rel in relationships:
        row = [
            job.job_name,
            rel.table2.table_name if rel.table2 else '',
            rel.table1.table_name if rel.table1 else '',
            rel.table1.table_category if rel.table1 and rel.table1.table_category else ''
        ]
        sheet.append(row)
    
    workbook.save(output)
    output.seek(0)
    
    filename = f'Job_{job.job_name}_Details.xlsx'
    
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename={filename}'
    
    return response


def edit_job(request, job_id):
    """
    Handle editing of an existing job.
    """
    developers = JobDeveloper.objects.all().order_by('developer_name')
    job = get_object_or_404(JobDetail, job_id=job_id)

    if request.method == 'POST':
        try:
            # Get form data
            new_job_name = request.POST.get('job_name', '').strip()
            new_pic_job = request.POST.get('pic_job', '').strip()
            new_developers = request.POST.getlist('developer')

            # Validate required fields
            if not new_job_name:
                return JsonResponse({'error': 'Job name is required'}, status=400)
            
            # Check if new job name already exists (excluding current job)
            if JobDetail.objects.filter(job_name=new_job_name).exclude(job_id=job_id).exists():
                return JsonResponse({'error': 'Job name already exists'}, status=400)
            
            # Update the job
            job.job_name = new_job_name
            job.pic_job = new_pic_job if new_pic_job else None
            job.updated_at = timezone.now()
            job.save()

            if new_developers:
                developer_ids = [int(dev_id) for dev_id in new_developers]
                job.developers.set(developer_ids)
            else:
                job.developers.clear()
            
            return JsonResponse({
                'success': True, 
                'message': f'Job "{new_job_name}" updated successfully'
            })
            
        except ValueError as e:
            return JsonResponse({'error': 'Invalid developer ID format'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'Error updating job: {str(e)}'}, status=500)
    
    # GET request - render the edit form
    relationships = (
        Relationship.objects
        .filter(job=job)
        .select_related('table1', 'table2')
        .order_by('table2__table_name', 'table1__table_name')
    )
    # All tables for the "add source" picker (exclude target tables of this job)
    all_tables = list(
        Table.objects
        .order_by('table_name')
        .values('table_id', 'table_name', 'table_category')
    )
    target_tables = list(set(r.table2 for r in relationships if r.table2))

    context = {
        'job': job,
        'developers': developers,
        'relationships': relationships,
        'target_tables': target_tables,
        'all_tables_json': json.dumps(all_tables),
    }
    return render(request, 'edit_job.html', context)


@csrf_exempt
def api_add_relationship(request, job_id):
    """
    AJAX POST: Add a new source table → target table relationship for a job.
    Expected JSON body: {source_table_id, target_table_id}
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    job = get_object_or_404(JobDetail, job_id=job_id)
    try:
        data = json.loads(request.body)
        src_id = int(data.get('source_table_id', 0))
        tgt_id = int(data.get('target_table_id', 0))
    except (ValueError, KeyError):
        return JsonResponse({'error': 'Invalid request body'}, status=400)

    if not src_id or not tgt_id:
        return JsonResponse({'error': 'source_table_id and target_table_id are required'}, status=400)
    if src_id == tgt_id:
        return JsonResponse({'error': 'Source and target table cannot be the same'}, status=400)

    try:
        source = Table.objects.get(table_id=src_id)
        target = Table.objects.get(table_id=tgt_id)
    except Table.DoesNotExist:
        return JsonResponse({'error': 'Table not found'}, status=404)

    rel, created = Relationship.objects.get_or_create(
        table1=source,
        table2=target,
        job_name=job.job_name,
        defaults={'job': job},
    )
    if not created:
        # Ensure job FK is set if it was missing
        if not rel.job:
            rel.job = job
            rel.save()
        return JsonResponse({'warning': 'Relationship already exists', 'relationship_id': rel.relationship_id})

    return JsonResponse({
        'success': True,
        'relationship_id': rel.relationship_id,
        'source_table': {'id': source.table_id, 'name': source.table_name, 'category': source.table_category or 'OTHER'},
        'target_table': {'id': target.table_id, 'name': target.table_name, 'category': target.table_category or 'OTHER'},
    })


@csrf_exempt
def api_delete_relationship(request, relationship_id):
    """
    AJAX DELETE/POST: Remove a specific relationship row.
    """
    if request.method not in ('POST', 'DELETE'):
        return JsonResponse({'error': 'POST or DELETE required'}, status=405)

    rel = get_object_or_404(Relationship, relationship_id=relationship_id)
    rel.delete()
    return JsonResponse({'success': True, 'deleted_id': relationship_id})

def delete_job(request, job_id):
    """
    Handle deletion of a job.
    Jika tabel yang terkait dengan job ini tidak memiliki relasi lain, 
    maka tabel tersebut akan ikut dihapus.
    """
    try:
        job = JobDetail.objects.get(job_id=job_id)
    except JobDetail.DoesNotExist:
        messages.error(request, 'Job not found')
        return redirect('job_list')
    
    if request.method == 'POST':
        job_name = job.job_name

        # 1. Deteksi table terkait yang hanya punya relasi dengan job ini
        related_rels = Relationship.objects.filter(job=job)
        candidate_table_ids = set()
        for rel in related_rels:
            if rel.table1:
                candidate_table_ids.add(rel.table1.table_id)
            if rel.table2:
                candidate_table_ids.add(rel.table2.table_id)

        # 2. Hapus Job
        job.delete()

        # 3. Hapus tabel yang tidak memiliki relasi lain
        tables_deleted_count = 0
        
        for t_id in candidate_table_ids:
            # Cek apakah tabel ini MASIH ada di relationship lain?
            # Kita cari di kolom table1 ATAU table2
            is_used_elsewhere = Relationship.objects.filter(
                Q(table1_id=t_id) | Q(table2_id=t_id)
            ).exists()
            
            # Jika TIDAK ada di relationship manapun, hapus tabelnya
            if not is_used_elsewhere:
                Table.objects.filter(table_id=t_id).delete()
                tables_deleted_count += 1
        
        # 4. Reset Auto Increment (Sequence)
        with connection.cursor() as cursor:
            # A. Reset Sequence Job
            cursor.execute("""
                SELECT setval(
                    pg_get_serial_sequence('main_jobdetail', 'job_id'), 
                    COALESCE((SELECT MAX(job_id) FROM main_jobdetail), 1)
                );
            """)
            # B. Reset Sequence Table jika ada yang dihapus
            if tables_deleted_count > 0:
                cursor.execute("""
                    SELECT setval(
                        pg_get_serial_sequence('main_table', 'table_id'), 
                        COALESCE((SELECT MAX(table_id) FROM main_table), 1)
                    );
                """)

        msg = f'Job "{job_name}" deleted successfully.'
        if tables_deleted_count > 0:
            msg += f' {tables_deleted_count} unused tables were also cleaned up.'
            
        messages.success(request, msg)
        return redirect('job_list')
    
    # If GET request, redirect to job list
    return redirect('job_list')


def upload_job(request):
    developers = JobDeveloper.objects.all().order_by('developer_name')

    if request.method == 'POST':
        job_name = request.POST.get('job_name', '').strip()
        job_path = request.POST.get('job_path', '').strip()
        target_table_raw = request.POST.getlist('target_table', '')
        developer_list = request.POST.getlist('developer', '')        
        errors = []

        # VALIDATION
        if not job_name:
            errors.append('Job name tidak boleh kosong.')
        else:
            existing_job = JobUploadSessions.objects.using('bot_eda').filter(
                job_name__iexact=job_name
            ).first()
            
            if existing_job:
                # 🔥 Refresh status dari log terbaru sebelum dicek
                existing_job.refresh_current_status()
                if existing_job.current_status not in ['Upload Failed', 'Error', None]:
                    errors.append('Job name sudah terdaftar dan berhasil diupload.')
            
            # if JobDetail.objects.filter(job_name__iexact=job_name).exists():
            #     errors.append('Job name sudah terdaftar di sistem.')

        if not job_path:
            errors.append('Job path tidak boleh kosong.')
        elif not job_path.lower().endswith('.zip'):
            errors.append('Job path harus diakhiri dengan .zip.')
        elif not job_path.startswith('/'):
            errors.append('Job path harus diawali dengan karakter "/".')

        if not target_table_raw:
            errors.append('Target table tidak boleh kosong.')

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, 'upload_job.html', {
                'developers': developers,
                'form_data': request.POST
            })

        mapping_dict = defaultdict(list)
        for category, schema in SchemaCategoryMapping.objects.values_list('category', 'schema_name'):
            mapping_dict[category].append(schema)

        try:
            with transaction.atomic():
                table_ids = get_or_create_table_ids(target_table_raw, mapping_dict)
                developer_list_int = [int(dev_id) for dev_id in developer_list if dev_id.isdigit()]
                
                existing_session = JobUploadSessions.objects.using('bot_eda').filter(
                    job_name__iexact=job_name
                ).first()
                
                if existing_session:
                    # UPDATE
                    existing_session.job_path = job_path
                    existing_session.pic_job = developer_list_int
                    existing_session.output_table = table_ids
                    existing_session.upload_time = timezone.now()
                    existing_session.retry_count = (existing_session.retry_count or 0) + 1
                    existing_session.save(using='bot_eda')
                    
                    session = existing_session
                    log_message = f'Job di-upload ulang (Retry #{existing_session.retry_count}). Sedang memproses lineage...'
                else:
                    # INSERT
                    jakarta_tz = ZoneInfo('Asia/Jakarta')
                    current_time = timezone.now().astimezone(jakarta_tz)

                    session = JobUploadSessions.objects.using('bot_eda').create(
                        job_name=job_name,
                        job_path=job_path,
                        pic_job=developer_list_int,
                        output_table=table_ids,
                        upload_time=current_time,
                        original_upload_time=current_time,
                    )
                    log_message = 'Job berhasil ditambahkan! Sedang memproses lineage...'

                # ✅ GUNAKAN HELPER FUNCTION
                update_job_status(session, 'On Progress', log_message)

            messages.success(request, 'Job berhasil ditambahkan.' if not existing_session else 'Job berhasil di-upload ulang.')
            return redirect('/upload_logs/?tab=on-progress-panel')

        except Exception as e:
            messages.error(request, f'Terjadi kesalahan database: {str(e)}')
            return render(request, 'upload_job.html', {'developers': developers})

    return render(request, 'upload_job.html', {'developers': developers})

@require_GET
def get_tables(request):
    q = request.GET.get('q', '').strip()

    if len(q) < 2:
        return JsonResponse({"results": []})

    tables = (
        Table.objects
        .filter(
            Q(table_name__icontains=q)
        )
        .values_list('table_name', flat=True)
        .order_by('table_name')[:20]
    )

    return JsonResponse({
        "results": list(tables)
    })

def upload_logs(request):
    # --- HANDLE POST REQUEST (UPDATE CATEGORIES) ---
    if request.method == 'POST':
        updated_count = 0
        job_name = request.POST.get('job_name', '')
        active_tab = request.POST.get('active_tab', 'done-panel')
        
        try:
            # Get session object
            session = JobUploadSessions.objects.using('bot_eda').get(job_name=job_name)
            
            # Loop semua item yang dikirim form
            for key, value in request.POST.items():
                # Cek apakah input ini adalah input kategori (prefix 'category_')
                if key.startswith('category_') and value:
                    # Ambil ID table dari nama input (contoh: category_55 -> id=55)
                    table_id = key.split('_')[1]
                    new_category = value
                    
                    # Update data
                    StagingDetectedTables.objects.using('bot_eda').filter(
                        table_id=table_id
                    ).update(table_category=new_category)
                    updated_count += 1
            
            if updated_count > 0:
                # Update job status to Done
                session.current_status = 'Done'
                session.save(using='bot_eda', update_fields=['current_status'])
                
                # Create log entry
                JobUploadLogs.objects.using('bot_eda').create(
                    job=session,
                    status='Done',
                    log_message=f'Categories updated successfully for {updated_count} tables. Job completed.',
                    update_time=timezone.now()
                )
                
                messages.success(request, f"Successfully updated {updated_count} tables for job: {job_name}")
            else:
                messages.warning(request, "No changes were made.")
                
        except JobUploadSessions.DoesNotExist:
            messages.error(request, f"Job not found: {job_name}")
        except Exception as e:
            messages.error(request, f"Error updating tables: {e}")
        
        return redirect(f"{request.path}?tab={active_tab}")

    # --- HANDLE GET REQUEST ---
    search_query = request.GET.get('q', '').strip()
    active_tab = request.GET.get('tab', 'done-panel')
    is_ajax = request.GET.get('ajax') == '1'  # 🔥 Detect AJAX request

    # 🔥 last update time per job (MAX dari logs)
    last_update_time = JobUploadLogs.objects.using('bot_eda') \
        .filter(job_id=OuterRef('job_id')) \
        .values('job_id') \
        .annotate(max_time=Max('update_time')) \
        .values('max_time')[:1]

    # 🔥 last error message (optional)
    last_error = JobUploadLogs.objects.using('bot_eda') \
        .filter(job_id=OuterRef('job_id'), status='Upload Failed') \
        .order_by('-update_time') \
        .values('log_message')[:1]

    latest_log_message = JobUploadLogs.objects.using('bot_eda') \
        .filter(job_id=OuterRef('job_id')) \
        .order_by('-update_time') \
        .values('log_message')[:1]
    
    sessions = JobUploadSessions.objects.using('bot_eda') \
        .annotate(
            last_update_time=Subquery(last_update_time),
            last_error=Subquery(last_error),
            latest_log_message=Subquery(latest_log_message),
        ) \
        .prefetch_related('stagingdetectedtables_set') \
        .order_by('-last_update_time', '-upload_time')
    
    if search_query:
        sessions = sessions.filter(
            Q(job_name__icontains=search_query) |
            Q(pic_job__icontains=search_query)
        )

    # 🔥 Refresh current_status untuk semua sessions dari log terbaru
    for session in sessions:
        session.refresh_current_status()

    context = {
        'sessions': sessions,
        'search_query': search_query,
        'active_tab': active_tab,
    }
    
    # 🔥 Return partial template for AJAX requests
    # if is_ajax:
    #     return render(request, 'upload_logs_ajax.html', context)
    
    if is_ajax:
        response = render(request, 'upload_logs_ajax.html', context)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
    
    # Normal full page render
    return render(request, 'upload_logs.html', context)

# def upload_logs(request):
#     # --- HANDLE POST REQUEST (UPDATE CATEGORIES) ---
#     if request.method == 'POST':
#         updated_count = 0
#         job_name = request.POST.get('job_name', '')
#         active_tab = request.POST.get('active_tab', 'done-panel')
        
#         try:
#             # Get session object
#             session = JobUploadSessions.objects.using('bot_eda').get(job_name=job_name)
            
#             # Loop semua item yang dikirim form
#             for key, value in request.POST.items():
#                 # Cek apakah input ini adalah input kategori (prefix 'category_')
#                 if key.startswith('category_') and value:
#                     # Ambil ID table dari nama input (contoh: category_55 -> id=55)
#                     table_id = key.split('_')[1]
#                     new_category = value
                    
#                     # Update data
#                     StagingDetectedTables.objects.using('bot_eda').filter(
#                         table_id=table_id
#                     ).update(table_category=new_category)
#                     updated_count += 1
            
#             if updated_count > 0:
#                 # Update job status to Done
#                 session.current_status = 'Done'
#                 session.save(using='bot_eda', update_fields=['current_status'])
                
#                 # Create log entry
#                 JobUploadLogs.objects.using('bot_eda').create(
#                     job=session,
#                     status='Done',
#                     log_message=f'Categories updated successfully for {updated_count} tables. Job completed.',
#                     update_time=timezone.now()
#                 )
                
#                 messages.success(request, f"Successfully updated {updated_count} tables for job: {job_name}")
#             else:
#                 messages.warning(request, "No changes were made.")
                
#         except JobUploadSessions.DoesNotExist:
#             messages.error(request, f"Job not found: {job_name}")
#         except Exception as e:
#             messages.error(request, f"Error updating tables: {e}")
        
#         return redirect(f"{request.path}?tab={active_tab}")

#     # --- HANDLE GET REQUEST ---
#     search_query = request.GET.get('q', '').strip()
#     active_tab = request.GET.get('tab', 'done-panel')

#     # 🔥 last update time per job (MAX dari logs)
#     last_update_time = JobUploadLogs.objects.using('bot_eda') \
#         .filter(job_id=OuterRef('job_id')) \
#         .values('job_id') \
#         .annotate(max_time=Max('update_time')) \
#         .values('max_time')[:1]

#     # 🔥 last error message (optional)
#     last_error = JobUploadLogs.objects.using('bot_eda') \
#         .filter(job_id=OuterRef('job_id'), status='Upload Failed') \
#         .order_by('-update_time') \
#         .values('log_message')[:1]

#     latest_log_message = JobUploadLogs.objects.using('bot_eda') \
#     .filter(job_id=OuterRef('job_id')) \
#     .order_by('-update_time') \
#     .values('log_message')[:1]
    

#     sessions = JobUploadSessions.objects.using('bot_eda') \
#         .annotate(
#             last_update_time=Subquery(last_update_time),
#             last_error=Subquery(last_error),
#             latest_log_message=Subquery(latest_log_message),
#         ) \
#         .prefetch_related('stagingdetectedtables_set') \
#         .order_by('-last_update_time', '-upload_time')
    

#     if search_query:
#         sessions = sessions.filter(
#             Q(job_name__icontains=search_query) |
#             Q(pic_job__icontains=search_query)
#         )

#     # 🔥 Refresh current_status untuk semua sessions dari log terbaru
#     for session in sessions:
#         session.refresh_current_status()

#     context = {
#         'sessions': sessions,
#         'search_query': search_query,
#         'active_tab': active_tab,
#     }
#     return render(request, 'upload_logs.html', context)


# def upload_logs(request):
#     # --- 1. HANDLE POST REQUEST (BULK UPDATE) ---
#     if request.method == 'POST':
#         # Kita meloop semua item yang dikirim form
#         # Form akan mengirim data dengan name pattern: "category_<table_id>"
#         updated_count = 0
#         job_name = request.POST.get('job_name', '')
#         active_tab = request.POST.get('active_tab', 'done-panel')
        
#         try:
#             for key, value in request.POST.items():
#                 # Cek apakah input ini adalah input kategori (prefix 'category_')
#                 if key.startswith('category_') and value:
#                     # Ambil ID table dari nama input (contoh: category_55 -> id=55)
#                     table_id = key.split('_')[1]
#                     new_category = value
                    
#                     # Update data
#                     StagingDetectedTables.objects.using('bot_eda').filter(table_id=table_id).update(table_category=new_category)
#                     updated_count += 1
            
#             if updated_count > 0:
#                 messages.success(request, f"Successfully updated {updated_count} tables.")
#             else:
#                 messages.warning(request, "No changes were made.")
                
#         except Exception as e:
#             messages.error(request, f"Error updating tables: {e}")
        
#         return redirect(f"{request.path}?tab={active_tab}")

#     # --- 2. HANDLE GET REQUEST ---

#     search_query = request.GET.get('q', '').strip()
#     active_tab = request.GET.get('tab', 'done-panel')
#     logs = JobUploadLogs.objects.using('bot_eda')\
#         .select_related('job')\
#         .prefetch_related('job__stagingdetectedtables_set')\
#         .order_by('-update_time')

#     if search_query:
#         logs = logs.filter(
#             Q(job__job_name__icontains=search_query) |
#             Q(log_message__icontains=search_query)
#         )


#     context = {
#         'logs': logs, 
#         'search_query': search_query,
#         'active_tab': active_tab,
#     }
#     return render(request, 'upload_logs.html', context)

# def upload_logs(request):
#     # --- 1. HANDLE POST REQUEST (BULK UPDATE CATEGORY) ---
#     if request.method == 'POST':
#         updated_count = 0
#         job_name = request.POST.get('job_name', '')
#         active_tab = request.POST.get('active_tab', 'done-panel')
        
#         try:
#             # ✅ Get session object
#             session = JobUploadSessions.objects.using('bot_eda').get(job_name=job_name)
            
#             # Loop semua item yang dikirim form
#             for key, value in request.POST.items():
#                 # Cek apakah input ini adalah input kategori (prefix 'category_')
#                 if key.startswith('category_') and value:
#                     # Ambil ID table dari nama input (contoh: category_55 -> id=55)
#                     table_id = key.split('_')[1]
#                     new_category = value
                    
#                     # Update data
#                     StagingDetectedTables.objects.using('bot_eda').filter(
#                         table_id=table_id
#                     ).update(table_category=new_category)
#                     updated_count += 1
            
#             if updated_count > 0:
#                 # ✅ Update job status to Done using helper function
#                 from .utils import update_job_status
#                 session_updated = JobUploadSessions.objects.using('bot_eda').get(job_name=job_name)
                
#                 # Update status
#                 session_updated.current_status = 'Done'
#                 session_updated.save(using='bot_eda', update_fields=['current_status'])
                
#                 # Create log entry
#                 JobUploadLogs.objects.using('bot_eda').create(
#                     job=session_updated,
#                     status='Done',
#                     log_message=f'Categories updated successfully for {updated_count} tables. Job completed.',
#                     update_time=timezone.now()
#                 )
                
#                 messages.success(request, f"Successfully updated {updated_count} tables for job: {job_name}")
#             else:
#                 messages.warning(request, "No changes were made.")
                
#         except JobUploadSessions.DoesNotExist:
#             messages.error(request, f"Job not found: {job_name}")
#         except Exception as e:
#             messages.error(request, f"Error updating tables: {e}")
        
#         return redirect(f"{request.path}?tab={active_tab}")

#     # --- 2. HANDLE GET REQUEST (DISPLAY LOGS) ---
#     search_query = request.GET.get('q', '').strip()
#     active_tab = request.GET.get('tab', 'done-panel')
    
#     # ✅ Query sessions dengan current_status filter
#     sessions = JobUploadSessions.objects.using('bot_eda')\
#         .select_related()\
#         .prefetch_related('stagingdetectedtables_set')\
#         .order_by('-upload_time')
    
#     # Search filter
#     if search_query:
#         sessions = sessions.filter(job_name__icontains=search_query)
    
#     # ✅ Filter by current_status based on active tab
#     status_mapping = {
#         'done-panel': 'Done',
#         'on-progress-panel': 'On Progress',
#         'need-confirmation-panel': 'Need Confirmation',
#         'upload-failed-panel': 'Upload Failed'
#     }
    
#     if active_tab in status_mapping:
#         sessions = sessions.filter(current_status=status_mapping[active_tab])
    
#     # ✅ Build sessions_data with latest log for each session
#     sessions_data = []
#     for session in sessions:
#         latest_log = JobUploadLogs.objects.using('bot_eda').filter(
#             job=session
#         ).order_by('-update_time').first()
        
#         sessions_data.append({
#             'session': session,
#             'latest_log': latest_log
#         })

#     context = {
#         'sessions_data': sessions_data,  # ✅ Changed from 'logs'
#         'search_query': search_query,
#         'active_tab': active_tab,
#     }
#     return render(request, 'upload_logs.html', context)

def trigger_n8n_webhook(request):
    # 1. Tentukan URL Webhook n8n (dari n8n Editor -> Webhook Node)
    n8n_webhook_url = 'https://subnotational-tricrotic-breanne.ngrok-free.dev/webhook-test/input-job-path'

    # 2. Siapkan data (Payload) yang ingin dikirim
    payload = {
        "ftp_path": "/CDP_DMT_WHL_EALCO_DLY_H0.zip",
        "JobName": "TEST_JOB_DJANGO",
        "TargetTable": "TEST_TABLE",
        "PICJob": "Halo dari Django!"
    }

    try:
        # 3. Kirim POST request
        response = requests.post(
            n8n_webhook_url, 
            json=payload,
            headers={'Content-Type': 'application/json'} # Optional: Tambah auth header jika perlu
        )
        
        # Cek status code dari n8n
        if response.status_code == 200:
            return JsonResponse({"status": "success", "n8n_response": response.json()})
        else:
            return JsonResponse({"status": "error", "code": response.status_code})

    except requests.exceptions.RequestException as e:
        return JsonResponse({"status": "failed", "error": str(e)})



# ------------------------- Developer -----------------------------------------------------

def developer_list(request):
    search_query = request.GET.get('q', '')

    if search_query:
        developers = JobDeveloper.objects.filter(
            Q(developer_name__icontains=search_query) |
            Q(developer_id__icontains=search_query) |
            Q(department__icontains=search_query) |
            Q(team__icontains=search_query)
        ).order_by('developer_name')
    else:
        developers = JobDeveloper.objects.all().order_by('developer_name')

    context = {
        'developers': developers,
        'search_query': search_query,
    }
    return render(request, 'developer_list.html', context)

def view_developer(request, developer_id):
    # Get developer atau 404
    developer = get_object_or_404(JobDeveloper, developer_id=developer_id)

    # Get search query
    search_query = request.GET.get('q', '').strip()

    # 🔥 PERBAIKAN: Gunakan filter dengan ManyToMany relationship
    jobs = JobDetail.objects.filter(developers__developer_id=developer_id)

    # Apply search filter jika ada
    if search_query:
        jobs = jobs.filter(
            Q(job_name__icontains=search_query) |
            Q(job_id__icontains=search_query) |
            Q(relationships__table2__table_name__icontains=search_query)
        ).distinct()

    # Order by job name
    jobs = jobs.order_by('job_name').distinct()

    context = {
        'developer': developer,
        'jobs': jobs,
        'search_query': search_query,
        'jobs_count': jobs.count(),  # Bonus: hitung jumlah jobs
    }
    return render(request, 'view_developer.html', context)

def create_developer(request):
    if request.method == 'POST':
        try:
            developer_name = request.POST.get('developer_name', '').strip().upper()
            department = request.POST.get('department', '').strip()
            team = request.POST.get('team', '').strip()
            
            if not developer_name:
                return JsonResponse({'error': 'Developer name is required'}, status=400)
            
            if not department :
                return JsonResponse({'error': 'Department is required'}, status=400)
            
            if JobDeveloper.objects.filter(developer_name=developer_name).exists():
                return JsonResponse({'error': 'Developer name already exists'}, status=400)
            
            new_developer = JobDeveloper.objects.create(
                developer_name=developer_name,
                department = department,
                team = team
            )
            
            return JsonResponse({
                'success': True, 
                'message': f'Developer "{developer_name}" created successfully',
                'developer_id': new_developer.developer_id
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Error creating developer: {str(e)}'}, status=500)
    
    return render(request, 'create_developer.html')

def edit_developer(request, developer_id):
    developer = get_object_or_404(JobDeveloper, developer_id=developer_id)

    if request.method == 'POST':
        form = DeveloperForm(request.POST, instance=developer)

        if form.is_valid():
            form.save()
            messages.success(request, 'Developer updated successfully')
            return redirect('view_developer', developer_id=developer_id)

    else:
        form = DeveloperForm(instance=developer)

    return render(request, 'edit_developer.html', {
        'form': form,
        'developer': developer
    })


def delete_developer(request, developer_id):
    try:
        developer = JobDeveloper.objects.get(developer_id=developer_id)
    except JobDeveloper.DoesNotExist:
        messages.error(request, 'Developer not found')
        return redirect('developer_list')
    
    if request.method == 'POST':
        developer_name = developer.developer_name
        developer.delete()
        messages.success(request, f'Developer "{developer_name}" has been deleted successfully')
        return redirect('developer_list')
    
    return redirect('developer_list')

# ------------------------- End Developer -------------------------------------------------
