import os

# Konfigurasi otomatis baca dari Environment Variables (Railway)
# atau fallback ke nilai lokal (XAMPP)

MYSQL_HOST = os.environ.get('MYSQLHOST', 'localhost')
MYSQL_USER = os.environ.get('MYSQLUSER', 'root')
MYSQL_PASSWORD = os.environ.get('MYSQLPASSWORD', '')
MYSQL_DB = os.environ.get('MYSQLDATABASE', 'dombastis')