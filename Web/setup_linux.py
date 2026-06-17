#!/usr/bin/env python3
"""
Linux deployment setup script
Run this on your Linux server to set up directories and permissions
"""

import os
import stat
from pathlib import Path

def setup_linux_deployment():
    """Set up directories and permissions for Linux deployment"""
    
    base_dir = Path(__file__).resolve().parent
    
    # Create directories
    directories = [
        base_dir / 'media',
        base_dir / 'staticfiles',
        base_dir / 'logs',
    ]
    
    for directory in directories:
        directory.mkdir(exist_ok=True, parents=True)
        print(f"Created directory: {directory}")
        
        # Set permissions (read/write for owner, read for group/others)
        os.chmod(directory, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    
    # Create log file
    log_file = base_dir / 'django_errors.log'
    if not log_file.exists():
        log_file.touch()
        print(f"Created log file: {log_file}")
    
    # Set permissions for log file
    os.chmod(log_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
    
    # Create environment variables template
    env_template = base_dir / '.env.example'
    with open(env_template, 'w') as f:
        f.write("""# Environment variables for production
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=your-secret-key-here
DATABASE_NAME=data-lineage-eda
DATABASE_USER=postgres
DATABASE_PASSWORD=your-password
DATABASE_HOST=localhost
DATABASE_PORT=5432
ALLOWED_HOSTS=172.20.10.2,localhost,127.0.0.1
""")
    
    print("Setup complete!")
    print("\nNext steps for Linux server:")
    print("1. Copy .env.example to .env and fill in your values")
    print("2. Install requirements: pip install -r requirements.txt")
    print("3. Run migrations: python manage.py migrate")
    print("4. Collect static files: python manage.py collectstatic")
    print("5. Set up your web server (nginx/apache) configuration")

if __name__ == "__main__":
    setup_linux_deployment()
