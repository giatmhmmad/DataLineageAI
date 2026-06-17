@echo off
call D:\venv_lineage\env\Scripts\activate.bat
cd D:\data_lineage\Web
python manage.py runserver
pause
