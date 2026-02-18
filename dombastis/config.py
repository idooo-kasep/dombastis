import os

# =========================================================
# KONFIGURASI DATABASE
# Gunakan environment variables di Railway (production)
# atau nilai default untuk development lokal
# =========================================================

MYSQL_HOST     = os.environ.get('MYSQL_HOST',     'localhost')
MYSQL_USER     = os.environ.get('MYSQL_USER',     'root')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
MYSQL_DB       = os.environ.get('MYSQL_DB',       'dombastis')