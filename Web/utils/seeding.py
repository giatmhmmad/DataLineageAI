import os
import sys
import django

# Setting and import django settings
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "data_lineage.settings")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "data_lineage.settings")
django.setup()

from main.models import Table, ParentChildRelationship, ColumnUsedInRelationship

# Create Tables
raw_sales = Table.objects.create(
    table_name="raw_sales",
    description="Raw sales data from POS system",
    table_columns={
        "columns": [
            {"name": "sale_id", "type": "integer"},
            {"name": "product_id", "type": "integer"},
            {"name": "amount", "type": "decimal"},
            {"name": "sale_date", "type": "date"}
        ]
    }
)

processed_sales = Table.objects.create(
    table_name="processed_sales",
    description="Processed sales data with cleaned and aggregated values",
    table_columns={
        "columns": [
            {"name": "sale_id", "type": "integer"},
            {"name": "product_id", "type": "integer"},
            {"name": "total_amount", "type": "decimal"},
            {"name": "sale_date", "type": "date"}
        ]
    }
)

sales_dashboard = Table.objects.create(
    table_name="sales_dashboard",
    description="Sales dashboard table for reporting",
    table_columns={
        "columns": [
            {"name": "product_id", "type": "integer"},
            {"name": "total_sales", "type": "decimal"},
            {"name": "report_month", "type": "date"}
        ]
    }
)

# Create Relationships
# raw_sales -> processed_sales
rel1 = ParentChildRelationship.objects.create(
    parent_table=raw_sales,
    child_table=processed_sales,
    description="Raw sales are cleaned and aggregated into processed_sales."
)

# processed_sales -> sales_dashboard
rel2 = ParentChildRelationship.objects.create(
    parent_table=processed_sales,
    child_table=sales_dashboard,
    description="Processed sales feed the sales dashboard for reporting."
)

# Define which columns are used in each relationship
# For raw_sales -> processed_sales
ColumnUsedInRelationship.objects.create(
    parent_table=raw_sales,
    column_used_in_relationship={
        str(raw_sales.table_id): ["sale_id", "product_id", "amount", "sale_date"]
    }
)

# For processed_sales -> sales_dashboard
ColumnUsedInRelationship.objects.create(
    parent_table=processed_sales,
    column_used_in_relationship={
        str(processed_sales.table_id): ["product_id", "total_amount", "sale_date"]
    }
)
