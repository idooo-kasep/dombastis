import sqlite3

def buat_database():
    # Menghubungkan ke file database (akan dibuat otomatis jika belum ada)
    conn = sqlite3.connect('peternakan.db')
    cursor = conn.cursor()

    # Query untuk membuat tabel domba
    # Pastikan nama kolom sama persis dengan yang dipanggil di app.py
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS domba (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_domba TEXT NOT NULL,
            id_tag TEXT,
            jenis_kelamin TEXT,
            berat REAL,
            jenis_ras TEXT,
            lokasi_kandang TEXT,
            no_kamar TEXT,
            induk_jantan TEXT,
            induk_betina TEXT,
            umur INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Aktif',
            tanggal_input TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print("Database 'peternakan.db' dan tabel 'domba' berhasil dibuat!")

if __name__ == '__main__':
    buat_database()