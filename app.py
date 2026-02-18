from flask import Flask, render_template, request, redirect, url_for, flash, make_response, session
from flask_mysqldb import MySQL
from fpdf import FPDF
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from functools import wraps
from datetime import date

import config

app = Flask(__name__)
app.secret_key = 'kunci_rahasia_dombastis'

# =========================================================
# KONFIGURASI DATABASE
# =========================================================
app.config['MYSQL_HOST'] = config.MYSQL_HOST
app.config['MYSQL_USER'] = config.MYSQL_USER
app.config['MYSQL_PASSWORD'] = config.MYSQL_PASSWORD
app.config['MYSQL_DB'] = config.MYSQL_DB

mysql = MySQL(app)

# =========================================================
# KONFIGURASI UPLOAD FOTO
# =========================================================
UPLOAD_FOLDER = 'static/uploads/kematian'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================================================
# MIDDLEWARE: PROTEKSI AKSES
# =========================================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Akses ditolak! Fitur ini khusus untuk Superadmin.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# =========================================================
# 0. ROUTE KHUSUS: SETUP AWAL
# =========================================================
@app.route('/setup_admin')
def setup_admin():
    cur = mysql.connection.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE,
            password VARCHAR(255),
            role ENUM('admin','karyawan') DEFAULT 'karyawan'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS domba (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nama_domba VARCHAR(100),
            jenis_kelamin ENUM('Jantan','Betina'),
            berat_kg DECIMAL(10,2),
            ear_tag_id VARCHAR(50),
            jenis_domba VARCHAR(100),
            lokasi_kandang ENUM('Barat','Timur'),
            nomor_kamar INT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS rekam_medis (
            id_medis INT AUTO_INCREMENT PRIMARY KEY,
            id_domba INT,
            tanggal_periksa DATE,
            diagnosa VARCHAR(255),
            obat VARCHAR(255),
            catatan TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sop (
            id INT AUTO_INCREMENT PRIMARY KEY,
            kegiatan VARCHAR(255),
            waktu VARCHAR(50),
            takaran VARCHAR(255),
            instruksi TEXT,
            penanggung_jawab VARCHAR(100)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS obat (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nama_obat VARCHAR(100),
            brand VARCHAR(100),
            fungsi TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS keuangan (
            id_transaksi INT AUTO_INCREMENT PRIMARY KEY,
            no_invoice VARCHAR(50) UNIQUE,
            pelanggan VARCHAR(100),
            produk TEXT,
            jumlah INT,
            total_harga DECIMAL(15,2),
            terbayar DECIMAL(15,2),
            sisa_tagihan DECIMAL(15,2),
            tanggal DATE,
            keterangan TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS keuangan_kas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            deskripsi VARCHAR(255),
            tipe ENUM('Masuk','Keluar'),
            kategori VARCHAR(100),
            tanggal DATE,
            nominal DECIMAL(15,2)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS laporan_harian (
            id INT AUTO_INCREMENT PRIMARY KEY,
            sop_id INT,
            nama_karyawan VARCHAR(50),
            tanggal DATE,
            jam_selesai TIME,
            status ENUM('Selesai', 'Pending') DEFAULT 'Selesai'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS referensi_medis (
            id INT AUTO_INCREMENT PRIMARY KEY,
            gejala TEXT,
            diagnosa_prediksi VARCHAR(100),
            kategori_obat VARCHAR(100),
            nama_obat_rekomendasi VARCHAR(100)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS stok_pakan (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nama_bahan VARCHAR(100),
            jenis_mutasi ENUM('Masuk', 'Keluar'),
            jumlah DECIMAL(10,2),
            tanggal DATE,
            keterangan TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS log_populasi (
            id INT AUTO_INCREMENT PRIMARY KEY,
            id_domba INT,
            tipe_mutasi ENUM('Masuk', 'Keluar'),
            alasan VARCHAR(50),
            tanggal DATE,
            keterangan TEXT,
            foto_bukti VARCHAR(255)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS log_kerja (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            tanggal DATE,
            lokasi_kandang ENUM('Barat','Timur'),
            buat_pakan TINYINT(1) DEFAULT 0,
            beri_pakan TINYINT(1) DEFAULT 0,
            sapu_kandang TINYINT(1) DEFAULT 0,
            cukur_domba INT DEFAULT 0,
            disinfektan TINYINT(1) DEFAULT 0,
            bersih_tandon TINYINT(1) DEFAULT 0,
            cek_garam TINYINT(1) DEFAULT 0,
            catatan TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS penjualan (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            no_struk    VARCHAR(50) UNIQUE,
            nama_pembeli VARCHAR(100),
            keterangan_domba TEXT,
            jumlah      INT,
            total_harga DECIMAL(15,2),
            terbayar    DECIMAL(15,2),
            sisa_tagihan DECIMAL(15,2),
            tanggal     DATE,
            no_hp       VARCHAR(20),
            catatan     TEXT,
            harga_per_ekor DECIMAL(15,2)
        )
    """)

    # ── AUTO MIGRASI: tambah kolom baru jika belum ada ──
    migrasi = [
        "ALTER TABLE penjualan ADD COLUMN IF NOT EXISTS no_struk VARCHAR(50)",
        "ALTER TABLE penjualan ADD COLUMN IF NOT EXISTS no_hp VARCHAR(20)",
        "ALTER TABLE penjualan ADD COLUMN IF NOT EXISTS catatan TEXT",
        "ALTER TABLE penjualan ADD COLUMN IF NOT EXISTS harga_per_ekor DECIMAL(15,2)",
        "ALTER TABLE penjualan ADD COLUMN IF NOT EXISTS sisa_tagihan DECIMAL(15,2) DEFAULT 0",
        "ALTER TABLE penjualan ADD COLUMN IF NOT EXISTS keterangan_domba TEXT",
    ]
    for sql in migrasi:
        try:
            cur.execute(sql)
            mysql.connection.commit()
        except Exception:
            pass

    cur.execute("SELECT COUNT(*) FROM referensi_medis")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO referensi_medis (gejala, diagnosa_prediksi, kategori_obat, nama_obat_rekomendasi) VALUES
            ('Lemas, kurang tenaga, lesu setelah melahirkan', 'Pemulihan Energi', 'ATP', 'BIO ENERGY'),
            ('Luka terbuka, infeksi bakteri, radang', 'Infeksi', 'ANTIBIOTIK', 'NOVA TETRA'),
            ('Perut kiri membesar, dipukul bunyi dung, sesak napas', 'Bloat (Kembung)', 'OBAT KEMBUNG', 'PLANTACID'),
            ('Kaki pincang, terkilir, salah urat, bengkak ringan', 'Cedera Otot', 'KECEKLUK', 'SALON PAS'),
            ('Daya tahan tubuh rendah, pucat, kurang vitamin', 'Defisiensi Vitamin', 'AD3E', 'MULTIVITAMINS'),
            ('Gangguan syaraf, pertumbuhan terhambat, kaku', 'Nutrisi Saraf', 'B KOMPLEK', 'B PLEX'),
            ('Kulit gatal, bulu rontok/gudig, cacingan, kurus', 'Parasit', 'OBAT CACING', 'INVERMECTIN'),
            ('Mencret, kotoran cair, infeksi usus', 'Diare / Scours', 'PENCERNAAN', 'COLIBACT'),
            ('Mata merah, berair, bengkak, katarak ringan', 'Infeksi Mata', 'OBAT MATA', 'ERLAMECTIN'),
            ('Pencernaan tidak stabil setelah pergantian pakan', 'Optimasi Lambung', 'PREBIOTIK', 'PREBIOTIK')
        """)
        mysql.connection.commit()

    cur.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cur.fetchone():
        pw_hash = generate_password_hash('admin123')
        cur.execute("INSERT INTO users (username, password, role) VALUES ('admin', %s, 'admin')", (pw_hash,))
        mysql.connection.commit()
        cur.close()
        return "Setup Berhasil! Akun: admin | Pass: admin123. Seluruh tabel lengkap berhasil dibuat!"

    cur.close()
    return "Setup sudah pernah dilakukan. Semua tabel berhasil dicek/ditambahkan."




# =========================================================
# ROUTE MIGRASI DATABASE - Jalankan SEKALI jika ada error kolom
# =========================================================
@app.route('/migrasi_db')
def migrasi_db():
    """Tambahkan kolom yang mungkin belum ada di tabel penjualan lama"""
    cur = mysql.connection.cursor()
    pesan = []

    kolom_baru = [
        ("no_struk",       "ALTER TABLE penjualan ADD COLUMN no_struk VARCHAR(50) UNIQUE"),
        ("no_hp",          "ALTER TABLE penjualan ADD COLUMN no_hp VARCHAR(20)"),
        ("catatan",        "ALTER TABLE penjualan ADD COLUMN catatan TEXT"),
        ("harga_per_ekor", "ALTER TABLE penjualan ADD COLUMN harga_per_ekor DECIMAL(15,2)"),
        ("sisa_tagihan",   "ALTER TABLE penjualan ADD COLUMN sisa_tagihan DECIMAL(15,2) DEFAULT 0"),
        ("terbayar",       "ALTER TABLE penjualan ADD COLUMN terbayar DECIMAL(15,2) DEFAULT 0"),
        ("keterangan_domba","ALTER TABLE penjualan ADD COLUMN keterangan_domba TEXT"),
    ]

    for nama_kolom, sql_alter in kolom_baru:
        try:
            cur.execute(sql_alter)
            mysql.connection.commit()
            pesan.append(f"✅ Kolom '{nama_kolom}' berhasil ditambahkan")
        except Exception as e:
            if "Duplicate column" in str(e):
                pesan.append(f"⏭️  Kolom '{nama_kolom}' sudah ada (skip)")
            else:
                pesan.append(f"❌ Kolom '{nama_kolom}' error: {str(e)}")

    cur.close()
    return "<br>".join([
        "<h2>Hasil Migrasi Database</h2>",
        *pesan,
        "<br><b>Selesai! Sekarang kunjungi <a href='/penjualan'>/penjualan</a></b>"
    ])


# =========================================================
# 1. SISTEM LOGIN & LOGOUT
# =========================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[2], password):
            session['loggedin'] = True
            session['id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[3]
            return redirect(url_for('dashboard'))

        flash('Username atau Password salah!', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# =========================================================
# 2. DASHBOARD UTAMA
# =========================================================
@app.route('/')
@login_required
def dashboard():
    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM domba ORDER BY lokasi_kandang ASC, nomor_kamar ASC")
    data_domba = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM domba")
    total_domba = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM domba WHERE jenis_kelamin = 'Jantan'")
    total_jantan = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM domba WHERE jenis_kelamin = 'Betina'")
    total_betina = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM domba WHERE lokasi_kandang = 'Barat'")
    total_barat = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM domba WHERE lokasi_kandang = 'Timur'")
    total_timur = cur.fetchone()[0]

    cur.execute("SELECT AVG(berat_kg) FROM domba")
    avg_berat_val = cur.fetchone()[0]
    avg_berat = avg_berat_val if avg_berat_val else 0

    labels = ["Minggu 1", "Minggu 2", "Minggu 3", "Minggu 4"]
    weights = [
        float(avg_berat) * 0.85,
        float(avg_berat) * 0.90,
        float(avg_berat) * 0.95,
        float(avg_berat)
    ]

    cur.close()

    return render_template(
        'index.html',
        domba_list=data_domba,
        total=total_domba,
        jantan=total_jantan,
        betina=total_betina,
        barat=total_barat,
        timur=total_timur,
        rata_rata=round(avg_berat, 2),
        chart_labels=labels,
        chart_data=weights
    )


# =========================================================
# 3. MANAJEMEN USER
# =========================================================
@app.route('/users')
@login_required
@admin_only
def list_users():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, username, role FROM users ORDER BY id DESC")
    all_users = cur.fetchall()
    cur.close()
    return render_template('users.html', users=all_users)


# FIX: register -> redirect ke list_users bukan 'index'
@app.route('/register', methods=['GET', 'POST'])
@login_required
@admin_only
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']

        cur = mysql.connection.cursor()
        try:
            cur.execute(
                "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                (username, password, role)
            )
            mysql.connection.commit()
            flash(f'User {username} berhasil didaftarkan!', 'success')
            return redirect(url_for('list_users'))
        except:
            flash('Username sudah digunakan!', 'danger')
        finally:
            cur.close()

    return render_template('register.html')


@app.route('/hapus_user/<int:id>')
@login_required
@admin_only
def hapus_user(id):
    if id == session['id']:
        flash('Gagal! Kamu tidak bisa menghapus akunmu sendiri.', 'danger')
    else:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM users WHERE id = %s", (id,))
        mysql.connection.commit()
        cur.close()
        flash('Akun karyawan berhasil dihapus.', 'warning')
    return redirect(url_for('list_users'))


# =========================================================
# 4. LOG KERJA KARYAWAN
# =========================================================
@app.route('/tugas', methods=['GET', 'POST'])
@login_required
def tugas():
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        lokasi = request.form.get('lokasi_tugas')

        buat = 1 if 'buat_pakan' in request.form else 0
        beri = 1 if 'beri_pakan' in request.form else 0
        sapu = 1 if 'sapu_kandang' in request.form else 0
        disin = 1 if 'disinfektan' in request.form else 0
        tandon = 1 if 'bersih_tandon' in request.form else 0
        garam = 1 if 'cek_garam' in request.form else 0

        cukur = request.form.get('cukur_domba', 0)
        catatan = request.form.get('catatan', '')

        if not lokasi:
            flash('Gagal! Harap pilih lokasi kandang (Barat/Timur).', 'danger')
            return redirect(url_for('tugas'))

        try:
            cur.execute("""
                INSERT INTO log_kerja (
                    user_id, tanggal, lokasi_kandang, buat_pakan, beri_pakan, sapu_kandang, 
                    cukur_domba, disinfektan, bersih_tandon, cek_garam, catatan
                )
                VALUES (%s, CURDATE(), %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (session['id'], lokasi, buat, beri, sapu, cukur, disin, tandon, garam, catatan))
            mysql.connection.commit()
            flash(f'Laporan tugas untuk Kandang {lokasi} berhasil dikirim!', 'success')
        except Exception as e:
            flash(f'Terjadi kesalahan saat menyimpan: {str(e)}', 'danger')

        return redirect(url_for('tugas'))

    if session['role'] == 'admin':
        cur.execute("""
            SELECT l.*, u.username FROM log_kerja l 
            JOIN users u ON l.user_id = u.id 
            ORDER BY l.tanggal DESC, l.id DESC
        """)
    else:
        cur.execute("""
            SELECT * FROM log_kerja 
            WHERE user_id = %s 
            ORDER BY tanggal DESC, id DESC
        """, (session['id'],))

    logs = cur.fetchall()
    cur.close()
    return render_template('tugas.html', logs=logs)


# =========================================================
# LAPORAN TUGAS
# =========================================================
@app.route('/laporan_tugas')
@login_required
def laporan_tugas():
    cur = mysql.connection.cursor()

    if session['role'] == 'admin':
        cur.execute("""
            SELECT l.id, u.username, l.lokasi_kandang, l.tanggal,
                   l.buat_pakan, l.beri_pakan, l.sapu_kandang, l.cukur_domba,
                   l.disinfektan, l.bersih_tandon, l.cek_garam, l.catatan
            FROM log_kerja l
            JOIN users u ON l.user_id = u.id
            ORDER BY l.tanggal DESC, l.id DESC
        """)
    else:
        cur.execute("""
            SELECT l.id, u.username, l.lokasi_kandang, l.tanggal,
                   l.buat_pakan, l.beri_pakan, l.sapu_kandang, l.cukur_domba,
                   l.disinfektan, l.bersih_tandon, l.cek_garam, l.catatan
            FROM log_kerja l
            JOIN users u ON l.user_id = u.id
            WHERE l.user_id = %s
            ORDER BY l.tanggal DESC, l.id DESC
        """, (session['id'],))

    logs = cur.fetchall()
    cur.close()
    return render_template('laporan_tugas.html', logs=logs)


# =========================================================
# 5. HALAMAN KANDANG DETAIL
# =========================================================
@app.route('/kandang/barat')
@login_required
def kandang_barat():
    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM domba WHERE lokasi_kandang = 'Barat' ORDER BY nomor_kamar ASC")
    data_domba = cur.fetchall()

    cur.execute("""
        SELECT l.*, u.username FROM log_kerja l 
        JOIN users u ON l.user_id = u.id 
        WHERE l.lokasi_kandang = 'Barat' ORDER BY l.tanggal DESC LIMIT 5
    """)
    logs_kandang = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM domba WHERE lokasi_kandang = 'Barat'")
    total = cur.fetchone()[0]

    cur.execute("""
        SELECT nomor_kamar, AVG(berat_kg) 
        FROM domba 
        WHERE lokasi_kandang = 'Barat' 
        GROUP BY nomor_kamar
    """)
    stats = cur.fetchall()
    cur.close()

    return render_template(
        'kandang_detail.html',
        domba_list=data_domba,
        logs_kandang=logs_kandang,
        lokasi="Barat",
        total=total,
        kamar_labels=[str(s[0]) for s in stats],
        kamar_weights=[float(s[1]) for s in stats]
    )


@app.route('/kandang/timur')
@login_required
def kandang_timur():
    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM domba WHERE lokasi_kandang = 'Timur' ORDER BY nomor_kamar ASC")
    data_domba = cur.fetchall()

    cur.execute("""
        SELECT l.*, u.username FROM log_kerja l 
        JOIN users u ON l.user_id = u.id 
        WHERE l.lokasi_kandang = 'Timur' ORDER BY l.tanggal DESC LIMIT 5
    """)
    logs_kandang = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM domba WHERE lokasi_kandang = 'Timur'")
    total = cur.fetchone()[0]

    cur.execute("""
        SELECT nomor_kamar, AVG(berat_kg) 
        FROM domba 
        WHERE lokasi_kandang = 'Timur' 
        GROUP BY nomor_kamar
    """)
    stats = cur.fetchall()
    cur.close()

    return render_template(
        'kandang_detail.html',
        domba_list=data_domba,
        logs_kandang=logs_kandang,
        lokasi="Timur",
        total=total,
        kamar_labels=[str(s[0]) for s in stats],
        kamar_weights=[float(s[1]) for s in stats]
    )


# =========================================================
# 6. CRUD DOMBA
# =========================================================
@app.route('/tambah', methods=['GET', 'POST'])
@login_required
@admin_only
def tambah_ternak():
    if request.method == 'POST':
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO domba (nama_domba, jenis_kelamin, berat_kg, ear_tag_id, jenis_domba, lokasi_kandang, nomor_kamar) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            request.form['nama'],
            request.form['jk'],
            request.form['berat'],
            request.form.get('ear_tag', '-'),
            request.form.get('jenis', 'Lokal'),
            request.form['lokasi'],
            request.form['kamar']
        ))

        new_id = cur.lastrowid
        cur.execute("""
            INSERT INTO log_populasi (id_domba, tipe_mutasi, alasan, tanggal) 
            VALUES (%s, 'Masuk', 'Pembelian/Kelahiran', CURDATE())
        """, (new_id,))

        mysql.connection.commit()
        cur.close()
        flash('Data Domba berhasil ditambahkan!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('tambah.html')


@app.route('/tambah_domba', methods=['GET', 'POST'])
@login_required
@admin_only
def tambah():
    return redirect(url_for('tambah_ternak'))


@app.route('/domba/<int:id>')
@login_required
def detail_domba(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM domba WHERE id = %s", (id,))
    domba = cur.fetchone()

    cur.execute("""
        SELECT tanggal_periksa, diagnosa, obat, catatan 
        FROM rekam_medis 
        WHERE id_domba = %s 
        ORDER BY tanggal_periksa DESC
    """, (id,))
    riwayat = cur.fetchall()

    cur.close()
    return render_template('detail_domba.html', domba=domba, riwayat=riwayat)


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_only
def edit(id):
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        nama = request.form.get('nama')
        jk = request.form.get('jk')
        berat = request.form.get('berat')
        ear_tag = request.form.get('ear_tag')
        jenis = request.form.get('jenis')
        lokasi = request.form.get('lokasi')
        kamar = request.form.get('kamar')

        try:
            cur.execute("""
                UPDATE domba 
                SET nama_domba=%s, jenis_kelamin=%s, berat_kg=%s, 
                    ear_tag_id=%s, jenis_domba=%s, lokasi_kandang=%s, nomor_kamar=%s 
                WHERE id=%s
            """, (nama, jk, berat, ear_tag, jenis, lokasi, kamar, id))

            mysql.connection.commit()
            flash('Perubahan data berhasil disimpan!', 'success')
            return redirect(url_for('detail_domba', id=id))

        except Exception as e:
            flash(f'Gagal menyimpan data: {str(e)}', 'danger')

        finally:
            cur.close()

    cur.execute("SELECT * FROM domba WHERE id = %s", (id,))
    domba = cur.fetchone()
    cur.close()

    return render_template('edit_domba.html', domba=domba)


@app.route('/hapus/<int:id>')
@login_required
@admin_only
def hapus(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM domba WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash('Data Domba telah dihapus!', 'danger')
    return redirect(url_for('dashboard'))


# =========================================================
# 7. INVENTARIS + MUTASI POPULASI
# =========================================================
@app.route('/inventaris', methods=['GET', 'POST'])
@login_required
def inventaris():
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        nama = request.form.get('nama_bahan')
        jenis = request.form.get('jenis_mutasi')
        jumlah = request.form.get('jumlah')
        tgl = request.form.get('tanggal')
        ket = request.form.get('keterangan')

        cur.execute("""
            INSERT INTO stok_pakan (nama_bahan, jenis_mutasi, jumlah, tanggal, keterangan) 
            VALUES (%s, %s, %s, %s, %s)
        """, (nama, jenis, jumlah, tgl, ket))

        mysql.connection.commit()
        flash('Data stok pakan berhasil diperbarui!', 'success')
        return redirect(url_for('inventaris'))

    cur.execute("SELECT * FROM stok_pakan ORDER BY tanggal DESC")
    pakan = cur.fetchall()

    cur.execute("SELECT id, nama_domba, ear_tag_id FROM domba")
    domba_list = cur.fetchall()

    cur.execute("""
        SELECT lp.*, d.nama_domba 
        FROM log_populasi lp 
        LEFT JOIN domba d ON lp.id_domba = d.id 
        ORDER BY lp.tanggal DESC
    """)
    mutasi_domba = cur.fetchall()

    cur.close()

    return render_template('inventaris.html', pakan=pakan, domba_list=domba_list, mutasi_domba=mutasi_domba)


@app.route('/lapor_kematian', methods=['POST'])
@login_required
def lapor_kematian():
    id_domba = request.form.get('id_domba')
    tgl = request.form.get('tanggal')
    ket = request.form.get('keterangan')
    file = request.files.get('foto')

    filename = None
    if file and file.filename:
        filename = secure_filename(f"mati_{id_domba}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    cur = mysql.connection.cursor()

    cur.execute("""
        INSERT INTO log_populasi (id_domba, tipe_mutasi, alasan, tanggal, keterangan, foto_bukti) 
        VALUES (%s, 'Keluar', 'Kematian', %s, %s, %s)
    """, (id_domba, tgl, ket, filename))

    cur.execute("DELETE FROM domba WHERE id = %s", (id_domba,))

    mysql.connection.commit()
    cur.close()

    flash('Laporan kematian tersimpan. Data domba telah dihapus dari daftar aktif.', 'warning')
    return redirect(url_for('inventaris'))


# =========================================================
# 8. REKAM MEDIS
# =========================================================
@app.route('/rekam_medis', methods=['GET'])
@login_required
def list_rekam_medis():
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT rm.id_medis, d.nama_domba, rm.tanggal_periksa, rm.diagnosa, rm.obat, rm.catatan 
        FROM rekam_medis rm 
        JOIN domba d ON rm.id_domba = d.id 
        ORDER BY rm.tanggal_periksa DESC
    """)
    data_medis = cur.fetchall()

    cur.execute("SELECT id, nama_domba FROM domba")
    daftar_domba = cur.fetchall()

    cur.close()

    return render_template('rekam_medis.html', medis_list=data_medis, domba_list=daftar_domba)


@app.route('/tambah_medis', methods=['POST'])
@login_required
def tambah_medis():
    cur = mysql.connection.cursor()

    cur.execute("""
        INSERT INTO rekam_medis (id_domba, tanggal_periksa, diagnosa, obat, catatan) 
        VALUES (%s, %s, %s, %s, %s)
    """, (
        request.form['id_domba'],
        request.form['tanggal'],
        request.form['diagnosa'],
        request.form['obat'],
        request.form['catatan']
    ))

    mysql.connection.commit()
    cur.close()

    flash('Catatan medis berhasil ditambahkan.', 'success')
    return redirect(url_for('list_rekam_medis'))


@app.route('/cetak_pdf/<int:id>')
@login_required
def cetak_pdf(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM domba WHERE id = %s", (id,))
    domba = cur.fetchone()

    cur.execute("""
        SELECT tanggal_periksa, diagnosa, obat, catatan 
        FROM rekam_medis 
        WHERE id_domba = %s
        ORDER BY tanggal_periksa DESC
    """, (id,))
    riwayat = cur.fetchall()

    cur.close()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, f"LAPORAN KESEHATAN: {domba[1]}", ln=True, align='C')

    pdf.set_fill_color(15, 76, 58)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(40, 10, "Tanggal", 1, 0, 'C', True)
    pdf.cell(50, 10, "Diagnosa", 1, 0, 'C', True)
    pdf.cell(50, 10, "Obat", 1, 0, 'C', True)
    pdf.cell(50, 10, "Catatan", 1, 1, 'C', True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 9)

    for r in riwayat:
        pdf.cell(40, 10, str(r[0]), 1)
        pdf.cell(50, 10, str(r[1]), 1)
        pdf.cell(50, 10, str(r[2]), 1)
        pdf.cell(50, 10, str(r[3]), 1, 1)

    response = make_response(pdf.output(dest='S').encode('latin-1'))
    response.headers.set('Content-Disposition', 'attachment', filename=f'Laporan_{domba[1]}.pdf')
    response.headers.set('Content-Type', 'application/pdf')
    return response


# =========================================================
# 9. SOP + REKAP TUGAS
# =========================================================
@app.route('/sop')
@login_required
def list_sop():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, kegiatan, waktu, takaran, penanggung_jawab, instruksi FROM sop ORDER BY waktu ASC")
    sops = cur.fetchall()
    cur.close()
    return render_template('list_sop.html', sops=sops)


@app.route('/tambah_sop', methods=['GET', 'POST'])
@login_required
@admin_only
def tambah_sop():
    if request.method == 'POST':
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO sop (kegiatan, waktu, takaran, instruksi, penanggung_jawab) 
            VALUES (%s, %s, %s, %s, %s)
        """, (
            request.form['kegiatan'],
            request.form.get('waktu', '-'),
            request.form['takaran'],
            request.form['instruksi'],
            request.form['penanggung_jawab']
        ))
        mysql.connection.commit()
        cur.close()
        flash('Jadwal SOP baru berhasil ditambahkan!', 'success')
        return redirect(url_for('list_sop'))

    return render_template('tambah_sop.html')


@app.route('/edit_sop/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_only
def edit_sop(id):
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        cur.execute("""
            UPDATE sop 
            SET kegiatan=%s, waktu=%s, takaran=%s, instruksi=%s, penanggung_jawab=%s 
            WHERE id=%s
        """, (
            request.form['kegiatan'],
            request.form.get('waktu', '-'),
            request.form['takaran'],
            request.form['instruksi'],
            request.form['penanggung_jawab'],
            id
        ))
        mysql.connection.commit()
        cur.close()
        flash('SOP berhasil diperbarui!', 'success')
        return redirect(url_for('list_sop'))

    cur.execute("SELECT * FROM sop WHERE id = %s", (id,))
    sop_item = cur.fetchone()
    cur.close()

    return render_template('edit_sop.html', sop=sop_item)


@app.route('/hapus_sop/<int:id>')
@login_required
@admin_only
def hapus_sop(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM sop WHERE id = %s", [id])
    mysql.connection.commit()
    cur.close()
    flash("SOP berhasil dihapus.", "warning")
    return redirect(url_for('list_sop'))


@app.route('/lapor_tugas', methods=['POST'])
@login_required
def lapor_tugas():
    sop_id = request.form.get('sop_id')
    nama_karyawan = session.get('username')

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO laporan_harian (sop_id, nama_karyawan, tanggal, jam_selesai)
        VALUES (%s, %s, CURDATE(), CURTIME())
    """, (sop_id, nama_karyawan))
    mysql.connection.commit()
    cur.close()

    flash('Tugas berhasil ditandai sebagai Selesai!', 'success')
    return redirect(url_for('list_sop'))


@app.route('/rekap_tugas')
@login_required
@admin_only
def rekap_tugas():
    dari = request.args.get('dari')
    sampai = request.args.get('sampai')

    cur = mysql.connection.cursor()

    query = """
        SELECT lh.tanggal, lh.jam_selesai, lh.nama_karyawan, s.kegiatan, s.penanggung_jawab
        FROM laporan_harian lh
        JOIN sop s ON lh.sop_id = s.id
    """
    params = []

    if dari and sampai:
        query += " WHERE lh.tanggal BETWEEN %s AND %s"
        params.extend([dari, sampai])

    query += " ORDER BY lh.tanggal DESC, lh.jam_selesai DESC"

    cur.execute(query, params)
    rekap = cur.fetchall()
    cur.close()

    return render_template('rekap_tugas.html', rekap=rekap, dari=dari, sampai=sampai)


# =========================================================
# 10. KATALOG OBAT + REFERENSI MEDIS
# =========================================================
@app.route('/obat')
@login_required
def list_obat():
    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM obat ORDER BY nama_obat ASC")
    data_obat = cur.fetchall()

    cur.execute("SELECT * FROM referensi_medis")
    panduan_medis = cur.fetchall()

    cur.close()

    return render_template('obat.html', obat_list=data_obat, panduan=panduan_medis)


@app.route('/katalog_obat')
@login_required
def katalog_obat():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM obat ORDER BY nama_obat ASC")
    data_obat = cur.fetchall()
    cur.close()
    return render_template('katalog_obat.html', obat_list=data_obat)


@app.route('/tambah_obat', methods=['GET', 'POST'])
@login_required
@admin_only
def tambah_obat():
    if request.method == 'POST':
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO obat (nama_obat, brand, fungsi) 
            VALUES (%s, %s, %s)
        """, (
            request.form['nama'],
            request.form['brand'],
            request.form['fungsi']
        ))
        mysql.connection.commit()
        cur.close()

        flash('Obat berhasil ditambahkan ke katalog!', 'success')
        return redirect(url_for('katalog_obat'))

    return render_template('tambah_obat.html')


@app.route('/hapus_obat/<int:id>')
@login_required
@admin_only
def hapus_obat(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM obat WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()

    flash('Obat berhasil dihapus dari katalog.', 'warning')
    return redirect(url_for('katalog_obat'))


# =========================================================
# 11. KEUANGAN INVOICE
# =========================================================
@app.route('/keuangan')
@login_required
@admin_only
def list_keuangan_invoice():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM keuangan ORDER BY tanggal DESC")
    transaksi = cur.fetchall()
    cur.close()
    return render_template('keuangan.html', transaksi=transaksi)


@app.route('/tambah_transaksi', methods=['POST'])
@login_required
@admin_only
def tambah_transaksi():
    no_inv = request.form['no_invoice']
    pelanggan = request.form['pelanggan']
    produk = request.form['produk']
    qty = int(request.form['jumlah'])
    total = float(request.form['total_harga'])
    bayar = float(request.form['terbayar'])
    sisa = total - bayar
    tgl = request.form['tanggal']

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO keuangan (no_invoice, pelanggan, produk, jumlah, total_harga, terbayar, sisa_tagihan, tanggal)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (no_inv, pelanggan, produk, qty, total, bayar, sisa, tgl))
    mysql.connection.commit()
    cur.close()

    flash('Transaksi Berhasil Dicatat!', 'success')
    return redirect(url_for('list_keuangan_invoice'))


@app.route('/hapus_transaksi/<int:id>', methods=['POST'])
@login_required
@admin_only
def hapus_transaksi(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM keuangan WHERE id_transaksi = %s", (id,))
    mysql.connection.commit()
    cur.close()

    flash('Transaksi berhasil dihapus!', 'warning')
    return redirect(url_for('list_keuangan_invoice'))


@app.route('/struk_invoice/<int:id>')
@login_required
@admin_only
def struk_invoice(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM keuangan WHERE id_transaksi = %s", (id,))
    t = cur.fetchone()
    cur.close()
    return render_template('struk_invoice.html', transaksi=t)


@app.route('/cetak_invoice/<int:id>')
@login_required
@admin_only
def cetak_invoice(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM keuangan WHERE id_transaksi = %s", (id,))
    t = cur.fetchone()
    cur.close()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(15, 76, 58)
    pdf.cell(190, 10, "DOMBASTIS - HOUSE OF SHEEP", ln=True, align='L')
    pdf.set_font("Arial", '', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(190, 5, "Jl. Nglerep-Trayang, Kec Ngronggot, Nganjuk", ln=True)
    pdf.cell(190, 5, "Telp: 0877-8750-2950", ln=True)
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, "INVOICE PEMBELIAN", ln=True, align='C')
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 10)
    pdf.cell(40, 7, f"No Invoice: {t[1]}", ln=True)
    pdf.cell(40, 7, f"Dikirim kepada: {t[2]}", ln=True)
    pdf.cell(40, 7, f"Tanggal: {t[8]}", ln=True)
    pdf.ln(5)

    pdf.set_fill_color(15, 76, 58)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(10, 10, "No", 1, 0, 'C', True)
    pdf.cell(80, 10, "Produk", 1, 0, 'C', True)
    pdf.cell(30, 10, "Jumlah", 1, 0, 'C', True)
    pdf.cell(70, 10, "Total Harga", 1, 1, 'C', True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 10)
    pdf.cell(10, 10, "1", 1, 0, 'C')
    pdf.cell(80, 10, str(t[3]), 1)
    pdf.cell(30, 10, str(t[4]), 1, 0, 'C')
    pdf.cell(70, 10, f"Rp {t[5]:,.0f}", 1, 1, 'R')
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 10)
    pdf.cell(120, 7, "PEMBAYARAN MELALUI", 0, 0)
    pdf.cell(30, 7, "Total", 0, 0)
    pdf.cell(40, 7, f"Rp {t[5]:,.0f}", 0, 1, 'R')

    pdf.set_font("Arial", '', 10)
    pdf.cell(120, 7, "Bank Mandiri 1710006188174", 0, 0)

    pdf.set_font("Arial", 'B', 10)
    pdf.cell(30, 7, "Dibayar", 0, 0)

    pdf.set_text_color(15, 76, 58)
    pdf.cell(40, 7, f"Rp {t[6]:,.0f}", 0, 1, 'R')

    pdf.set_text_color(255, 0, 0)
    pdf.cell(120, 7, "A/N FARAH FAWZYAH HUSNANIATI", 0, 0)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(30, 7, "Sisa Tagihan", 0, 0)
    pdf.cell(40, 7, f"Rp {t[7]:,.0f}", 0, 1, 'R')

    response = make_response(pdf.output(dest='S').encode('latin-1'))
    response.headers.set('Content-Disposition', 'attachment', filename=f'Invoice_{t[1]}.pdf')
    response.headers.set('Content-Type', 'application/pdf')
    return response


# =========================================================
# 12. KEUANGAN KAS
# =========================================================
@app.route('/keuangan_kas')
@login_required
@admin_only
def list_keuangan_kas():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, deskripsi, tipe, kategori, tanggal, nominal
        FROM keuangan_kas
        ORDER BY tanggal DESC, id DESC
    """)
    data_transaksi = cur.fetchall()

    cur.execute("SELECT SUM(nominal) FROM keuangan_kas WHERE tipe = 'Masuk'")
    total_masuk = cur.fetchone()[0] or 0

    cur.execute("SELECT SUM(nominal) FROM keuangan_kas WHERE tipe = 'Keluar'")
    total_keluar = cur.fetchone()[0] or 0

    saldo_akhir = total_masuk - total_keluar
    cur.close()

    return render_template(
        'list_keuangan.html',
        transaksi=data_transaksi,
        saldo=saldo_akhir,
        masuk=total_masuk,
        keluar=total_keluar
    )


@app.route('/tambah_keuangan', methods=['GET', 'POST'])
@login_required
@admin_only
def tambah_keuangan():
    if request.method == 'POST':
        deskripsi = request.form['deskripsi']
        tipe = request.form['tipe']
        kategori = request.form['kategori']
        nominal = request.form['nominal']
        tanggal = request.form['tanggal']

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO keuangan_kas (deskripsi, tipe, kategori, nominal, tanggal) 
            VALUES (%s, %s, %s, %s, %s)
        """, (deskripsi, tipe, kategori, nominal, tanggal))

        mysql.connection.commit()
        cur.close()

        flash('Transaksi kas berhasil dicatat!', 'success')
        return redirect(url_for('list_keuangan_kas'))

    return render_template('tambah_keuangan.html')


@app.route('/keuangan_kas/detail/<int:id>')
@login_required
@admin_only
def detail_keuangan(id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, deskripsi, tipe, kategori, tanggal, nominal
        FROM keuangan_kas
        WHERE id = %s
    """, (id,))
    transaksi = cur.fetchone()
    cur.close()

    if not transaksi:
        flash("Data transaksi tidak ditemukan!", "danger")
        return redirect(url_for('list_keuangan_kas'))

    return render_template("detail_keuangan.html", transaksi=transaksi)


@app.route('/keuangan_kas/hapus/<int:id>')
@login_required
@admin_only
def hapus_keuangan(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM keuangan_kas WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()

    flash("Transaksi kas berhasil dihapus!", "warning")
    return redirect(url_for('list_keuangan_kas'))


# =========================================================
# ALIAS ROUTES - Mencegah BuildError dari template lama
# =========================================================
@app.route('/keuangan_list')
@login_required
@admin_only
def list_keuangan():
    return redirect(url_for('list_keuangan_kas'))


# =========================================================
# 13. PENJUALAN DOMBA
# =========================================================

def generate_no_struk(cur):
    """Generate nomor struk otomatis format: JL-YYYYMMDD-XXX"""
    try:
        hari_ini = date.today().strftime('%Y%m%d')
        prefix = f"JL-{hari_ini}-"
        cur.execute("SELECT COUNT(*) FROM penjualan WHERE no_struk LIKE %s", (prefix + '%',))
        urutan = cur.fetchone()[0] + 1
        return f"{prefix}{urutan:03d}"
    except Exception:
        # Fallback jika kolom no_struk belum ada
        cur.execute("SELECT COUNT(*) FROM penjualan")
        urutan = cur.fetchone()[0] + 1
        hari_ini = date.today().strftime('%Y%m%d')
        return f"JL-{hari_ini}-{urutan:03d}"


@app.route('/penjualan')
@login_required
@admin_only
def list_penjualan():
    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM penjualan ORDER BY tanggal DESC, id DESC")
    penjualan_list = cur.fetchall()

    cur.execute("SELECT COALESCE(SUM(total_harga), 0) FROM penjualan")
    total_pendapatan = float(cur.fetchone()[0])

    cur.execute("SELECT COALESCE(SUM(jumlah), 0) FROM penjualan")
    total_terjual = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM penjualan WHERE sisa_tagihan > 0")
    belum_lunas = cur.fetchone()[0]

    cur.execute("""
        SELECT id, nama_domba, jenis_kelamin, berat_kg, ear_tag_id, jenis_domba
        FROM domba ORDER BY nama_domba ASC
    """)
    domba_tersedia = cur.fetchall()

    no_struk_auto = generate_no_struk(cur)

    from datetime import datetime
    now = datetime.today()

    cur.close()

    return render_template(
        'penjualan.html',
        penjualan_list=penjualan_list,
        total_pendapatan=total_pendapatan,
        total_terjual=total_terjual,
        belum_lunas=belum_lunas,
        domba_tersedia=domba_tersedia,
        no_struk_auto=no_struk_auto,
        now=now
    )


@app.route('/tambah_penjualan', methods=['POST'])
@login_required
@admin_only
def tambah_penjualan():
    nama_pembeli     = request.form.get('nama_pembeli', '').strip()
    no_hp            = request.form.get('no_hp', '').strip()
    keterangan_domba = request.form.get('keterangan_domba', '').strip()
    jumlah           = int(request.form.get('jumlah', 1))
    harga_per_ekor   = float(request.form.get('harga_per_ekor', 0))
    terbayar         = float(request.form.get('terbayar', 0))
    tanggal          = request.form.get('tanggal') or date.today().isoformat()
    catatan          = request.form.get('catatan', '').strip()

    total_harga  = jumlah * harga_per_ekor
    sisa_tagihan = max(0, total_harga - terbayar)

    cur = mysql.connection.cursor()
    try:
        # Auto-generate no_struk dari form atau buat baru jika kosong
        no_struk = request.form.get('no_struk', '').strip()
        if not no_struk:
            no_struk = generate_no_struk(cur)

        cur.execute("""
            INSERT INTO penjualan
                (no_struk, nama_pembeli, keterangan_domba, jumlah,
                 total_harga, terbayar, sisa_tagihan, tanggal,
                 no_hp, catatan, harga_per_ekor)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (no_struk, nama_pembeli, keterangan_domba, jumlah,
              total_harga, terbayar, sisa_tagihan, tanggal,
              no_hp, catatan, harga_per_ekor))
        mysql.connection.commit()

        # Ambil ID transaksi yang baru disimpan untuk redirect ke struk
        new_id = cur.lastrowid
        flash('Penjualan berhasil dicatat! Struk siap dicetak.', 'success')
        cur.close()
        return redirect(url_for('struk_penjualan', id=new_id))

    except Exception as e:
        mysql.connection.rollback()
        flash(f'Gagal menyimpan transaksi: {str(e)}', 'danger')
    finally:
        try:
            cur.close()
        except Exception:
            pass

    return redirect(url_for('list_penjualan'))


@app.route('/hapus_penjualan/<int:id>')
@login_required
@admin_only
def hapus_penjualan(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM penjualan WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash('Transaksi penjualan berhasil dihapus.', 'warning')
    return redirect(url_for('list_penjualan'))


@app.route('/struk_penjualan/<int:id>')
@login_required
@admin_only
def struk_penjualan(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM penjualan WHERE id = %s", (id,))
    transaksi = cur.fetchone()
    cur.close()

    if not transaksi:
        flash('Data penjualan tidak ditemukan!', 'danger')
        return redirect(url_for('list_penjualan'))

    return render_template('struk_penjualan.html', transaksi=transaksi)


@app.route('/cetak_struk_pdf/<int:id>')
@login_required
@admin_only
def cetak_struk_pdf(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM penjualan WHERE id = %s", (id,))
    t = cur.fetchone()
    cur.close()

    if not t:
        flash('Data tidak ditemukan!', 'danger')
        return redirect(url_for('list_penjualan'))

    # t index: 0=id, 1=no_struk, 2=nama_pembeli, 3=keterangan_domba,
    #          4=jumlah, 5=total_harga, 6=terbayar, 7=sisa_tagihan,
    #          8=tanggal, 9=no_hp, 10=catatan, 11=harga_per_ekor

    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)

    pdf.set_fill_color(45, 90, 39)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(0, 12, "DOMBASTIS - HOUSE OF SHEEP", ln=True, align='C', fill=True)

    pdf.set_font("Arial", '', 9)
    pdf.set_fill_color(255, 193, 7)
    pdf.set_text_color(26, 58, 24)
    pdf.cell(0, 7, "Jl. Nglerep-Trayang, Kec Ngronggot, Nganjuk  |  Telp: 0877-8750-2950", ln=True, align='C', fill=True)
    pdf.ln(5)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 13)
    pdf.cell(0, 8, "STRUK PENJUALAN DOMBA", ln=True, align='C')
    pdf.set_font("Arial", '', 9)
    pdf.cell(0, 6, f"No. Struk: {t[1]}", ln=True, align='C')
    pdf.ln(4)

    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(240, 247, 240)
    pdf.cell(0, 7, " Informasi Pembeli", ln=True, fill=True)
    pdf.set_font("Arial", '', 9)
    pdf.cell(50, 6, "Nama Pembeli")
    pdf.cell(0, 6, f": {t[2]}", ln=True)
    if t[9]:
        pdf.cell(50, 6, "No. HP")
        pdf.cell(0, 6, f": {t[9]}", ln=True)
    pdf.cell(50, 6, "Tanggal")
    pdf.cell(0, 6, f": {t[8]}", ln=True)
    pdf.ln(3)

    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(240, 247, 240)
    pdf.cell(0, 7, " Detail Domba", ln=True, fill=True)
    pdf.set_font("Arial", '', 9)

    pdf.set_fill_color(45, 90, 39)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(80, 7, "Keterangan", 1, 0, 'C', True)
    pdf.cell(25, 7, "Jumlah", 1, 0, 'C', True)
    pdf.cell(40, 7, "Harga/Ekor", 1, 0, 'C', True)
    pdf.cell(35, 7, "Subtotal", 1, 1, 'C', True)

    pdf.set_text_color(0, 0, 0)
    harga_ekor = float(t[11]) if t[11] else (float(t[5]) / int(t[4]) if t[4] else 0)
    pdf.cell(80, 7, str(t[3])[:40], 1)
    pdf.cell(25, 7, f"{t[4]} Ekor", 1, 0, 'C')
    pdf.cell(40, 7, f"Rp {harga_ekor:,.0f}", 1, 0, 'R')
    pdf.cell(35, 7, f"Rp {float(t[5]):,.0f}", 1, 1, 'R')
    pdf.ln(3)

    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(240, 247, 240)
    pdf.cell(0, 7, " Rincian Pembayaran", ln=True, fill=True)
    pdf.set_font("Arial", '', 9)

    pdf.cell(120, 6, "Total Harga")
    pdf.cell(0, 6, f"Rp {float(t[5]):,.0f}", ln=True, align='R')

    pdf.cell(120, 6, "Jumlah Dibayar")
    pdf.set_text_color(0, 128, 0)
    pdf.cell(0, 6, f"Rp {float(t[6]):,.0f}", ln=True, align='R')
    pdf.set_text_color(0, 0, 0)

    if float(t[7]) > 0:
        pdf.set_text_color(200, 0, 0)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(120, 7, "SISA TAGIHAN")
        pdf.cell(0, 7, f"Rp {float(t[7]):,.0f}", ln=True, align='R')
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", '', 9)
    else:
        pdf.set_text_color(0, 128, 0)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 7, "STATUS: LUNAS", ln=True, align='R')
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", '', 9)

    pdf.ln(3)

    if t[10]:
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(0, 6, "Catatan:", ln=True)
        pdf.set_font("Arial", 'I', 9)
        pdf.multi_cell(0, 5, str(t[10]))
        pdf.ln(2)

    pdf.set_font("Arial", '', 8)
    pdf.set_fill_color(248, 248, 248)
    pdf.cell(0, 5, "Pembayaran melalui: Bank Mandiri 1710006188174  A/N FARAH FAWZYAH HUSNANIATI", ln=True, fill=True)
    pdf.ln(8)

    pdf.set_font("Arial", '', 9)
    pdf.cell(120, 5, "")
    pdf.cell(0, 5, "Petugas,", ln=True)
    pdf.ln(14)
    pdf.cell(120, 5, "")
    pdf.cell(0, 5, "( ________________________ )", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", 'I', 7)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, "Terima kasih telah berbelanja di Dombastis Farm — Barang yang sudah dibeli tidak dapat ditukar/dikembalikan.", ln=True, align='C')

    response = make_response(pdf.output(dest='S').encode('latin-1'))
    response.headers.set('Content-Disposition', 'attachment', filename=f'Struk_{t[1]}.pdf')
    response.headers.set('Content-Type', 'application/pdf')
    return response


# =========================================================
# RUN APP
# =========================================================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)