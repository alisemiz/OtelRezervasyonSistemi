import sqlite3
from datetime import datetime

# Veritabanı dosya adı
DB_NAME = 'otel_rezervasyon.db'

# --- Bağlantı ve Kurulum ---

def baglanti_olustur():
    """Veritabanına bağlantı kurar, foreign key desteğini açar ve bağlantı nesnesini döndürür."""
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.execute("PRAGMA foreign_keys = 1") 
        return conn
    except sqlite3.Error as e:
        print(f"Veritabanı bağlantı hatası: {e}")
        raise  # Hatayı yukarıya bildir

def _veritabani_gecislerini_yonet(conn):
    """Veritabanı şemasını kontrol eder ve eksik sütunları ekler (varsa)."""
    cursor = conn.cursor()
    try:
        # Rezervasyonlar tablosunu kontrol et
        cursor.execute("PRAGMA table_info(rezervasyonlar)")
        rez_sutunlar = [row[1] for row in cursor.fetchall()]
        if 'toplam_fiyat' not in rez_sutunlar:
            cursor.execute("ALTER TABLE rezervasyonlar ADD COLUMN toplam_fiyat REAL DEFAULT 0")
            print("Veritabanı geçirildi: 'toplam_fiyat' sütunu eklendi.")
        if 'odeme_durumu' not in rez_sutunlar:
            cursor.execute("ALTER TABLE rezervasyonlar ADD COLUMN odeme_durumu TEXT NOT NULL DEFAULT 'Ödenmedi'")
            print("Veritabanı geçirildi: 'odeme_durumu' sütunu eklendi.")
            
        # Odalar tablosunu kontrol et
        cursor.execute("PRAGMA table_info(odalar)")
        oda_sutunlar = [row[1] for row in cursor.fetchall()]
        if 'oda_durumu' not in oda_sutunlar:
            cursor.execute("ALTER TABLE odalar ADD COLUMN oda_durumu TEXT NOT NULL DEFAULT 'Temiz'")
            print("Veritabanı geçirildi: 'oda_durumu' sütunu eklendi.")
            
        conn.commit()
    except sqlite3.Error as e:
        print(f"Veritabanı geçişi sırasında hata: {e}")
        conn.rollback() # Hata olursa yapılan değişiklikleri geri al

def veritabani_baslat():
    """Tüm tabloları oluşturur (varsa atlar) ve varsayılan odaları ekler (sadece ilk kurulumda)."""
    conn = None # Bağlantıyı başta None olarak ayarla
    try:
        conn = baglanti_olustur()
        cursor = conn.cursor()
        
        # 1. odalar tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS odalar (
                oda_numarasi TEXT PRIMARY KEY,
                oda_tipi TEXT NOT NULL,
                gunluk_fiyat REAL NOT NULL CHECK(gunluk_fiyat > 0), -- Fiyat pozitif olmalı
                oda_durumu TEXT NOT NULL DEFAULT 'Temiz' CHECK(oda_durumu IN ('Temiz', 'Kirli', 'Tadilatta')) -- Geçerli durumlar
            )
        """)
        
        # 2. rezervasyonlar tablosu (müşteri adı ile)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rezervasyonlar (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                musteri_adi TEXT NOT NULL, 
                oda_no TEXT NOT NULL, 
                giris_tarihi TEXT NOT NULL, -- YYYY-MM-DD formatında saklanacak
                cikis_tarihi TEXT NOT NULL, -- YYYY-MM-DD formatında saklanacak
                toplam_fiyat REAL DEFAULT 0,
                odeme_durumu TEXT NOT NULL DEFAULT 'Ödenmedi' CHECK(odeme_durumu IN ('Ödenmedi', 'Kapora Alındı', 'Tamamı Ödendi')), -- Geçerli durumlar
                FOREIGN KEY (oda_no) REFERENCES odalar (oda_numarasi) ON DELETE CASCADE -- Oda silinirse ilgili rezervasyonlar da silinir
            )
        """)
        
        _veritabani_gecislerini_yonet(conn) # Sütunları kontrol et/ekle
        
        # 3. Odaları Yalnızca Tablo Boşsa Ekle
        cursor.execute("SELECT COUNT(*) FROM odalar")
        if cursor.fetchone()[0] == 0:
            otel_odalari = [
                ('101', 'Tek Kişilik', 1500, 'Temiz'), ('102', 'Tek Kişilik', 1500, 'Temiz'), 
                ('103', 'Tek Kişilik', 1500, 'Kirli'), 
                ('201', 'Çift Kişilik', 2500, 'Temiz'), ('202', 'Çift Kişilik', 2500, 'Temiz'), 
                ('203', 'Çift Kişilik', 2500, 'Temiz'), ('204', 'Çift Kişilik', 2500, 'Tadilatta'), 
                ('301', 'Suit', 4000, 'Temiz'), ('302', 'Suit', 4000, 'Temiz')
            ]
            cursor.executemany("INSERT INTO odalar VALUES (?,?,?,?)", otel_odalari)
            print("Veritabanı ilk kez kuruldu, varsayılan odalar eklendi.")
        
        conn.commit()
    except sqlite3.Error as e:
        print(f"Veritabanı başlatılırken hata oluştu: {e}")
        if conn: conn.rollback() # Hata olursa geri al
    finally:
        if conn: conn.close() # Bağlantıyı her durumda kapat

# --- ODA YÖNETİMİ FONKSİYONLARI ---

def odalari_cek():
    """Yönetim panelinde listelemek için TÜM odaları çeker."""
    conn = None
    try:
        conn = baglanti_olustur()
        cursor = conn.cursor()
        cursor.execute("SELECT oda_numarasi, oda_tipi, gunluk_fiyat, oda_durumu FROM odalar ORDER BY oda_numarasi") 
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Odalar çekilirken hata: {e}")
        return [] # Hata durumunda boş liste döndür
    finally:
        if conn: conn.close()

def oda_ekle(oda_no, oda_tipi, fiyat, durum):
    """Yeni bir odayı 'odalar' tablosuna ekler."""
    conn = None
    try:
        conn = baglanti_olustur()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO odalar (oda_numarasi, oda_tipi, gunluk_fiyat, oda_durumu) VALUES (?, ?, ?, ?)", (oda_no, oda_tipi, fiyat, durum))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Oda eklenirken hata: {e}")
        if conn: conn.rollback()
        raise # Hatayı tekrar fırlat ki arayüz yakalasın (örn. IntegrityError)
    finally:
        if conn: conn.close()

def oda_guncelle(oda_no, oda_tipi, fiyat, durum):
    """Mevcut bir odanın bilgilerini günceller."""
    conn = None
    try:
        conn = baglanti_olustur()
        cursor = conn.cursor()
        cursor.execute("UPDATE odalar SET oda_tipi = ?, gunluk_fiyat = ?, oda_durumu = ? WHERE oda_numarasi = ?", (oda_tipi, fiyat, durum, oda_no))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Oda güncellenirken hata: {e}")
        if conn: conn.rollback()
        raise
    finally:
        if conn: conn.close()

def _get_gelecek_rezervasyon_sayisi(cursor, oda_no):
    """Yardımcı: Bir odanın aktif/gelecek rezervasyon sayısını döndürür."""
    try:
        bugun_sql = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT COUNT(*) FROM rezervasyonlar WHERE oda_no = ? AND cikis_tarihi > ?", (oda_no, bugun_sql))
        return cursor.fetchone()[0]
    except sqlite3.Error as e:
        print(f"Rezervasyon sayısı alınırken hata: {e}")
        return 0 # Hata durumunda 0 döndür

def oda_sil(oda_no):
    """Bir odayı siler. Aktif/gelecek rezervasyonu varsa, ValueError fırlatır."""
    conn = None
    try:
        conn = baglanti_olustur()
        cursor = conn.cursor()
        rez_sayisi = _get_gelecek_rezervasyon_sayisi(cursor, oda_no)
        if rez_sayisi > 0:
            raise ValueError(f"Oda {oda_no} için {rez_sayisi} adet aktif/gelecek rezervasyon var. Silinemez.")
        # Rezervasyon yoksa, önce (varsa) GEÇMİŞ rezervasyonlarını sil 
        # (ON DELETE CASCADE bunu otomatik yapmalı ama garantiye alalım)
        cursor.execute("DELETE FROM rezervasyonlar WHERE oda_no = ?", (oda_no,)) 
        # Sonra odayı sil
        cursor.execute("DELETE FROM odalar WHERE oda_numarasi = ?", (oda_no,))
        conn.commit()
    except sqlite3.Error as e:
         print(f"Oda silinirken hata: {e}")
         if conn: conn.rollback()
         raise # ValueError dışındaki hataları da fırlat
    finally:
        if conn: conn.close()

# --- REZERVASYON YARDIMCI FONKSİYONLARI ---

def oda_tiplerini_cek():
    """ComboBox'ı doldurmak için veritabanındaki TİPLERİ çeker."""
    conn = None
    try:
        conn = baglanti_olustur()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT oda_tipi FROM odalar ORDER BY gunluk_fiyat")
        return [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Oda tipleri çekilirken hata: {e}")
        return []
    finally:
        if conn: conn.close()

def fiyat_getir(oda_tipi):
    """Hesaplama için bir oda tipinin günlük fiyatını getirir."""
    conn = None
    try:
        conn = baglanti_olustur()
        cursor = conn.cursor()
        cursor.execute("SELECT gunluk_fiyat FROM odalar WHERE oda_tipi = ? LIMIT 1", (oda_tipi,))
        sonuc = cursor.fetchone()
        return sonuc[0] if sonuc else 0
    except sqlite3.Error as e:
        print(f"Fiyat getirilirken hata: {e}")
        return 0
    finally:
        if conn: conn.close()

def musait_oda_bul(oda_tipi, giris, cikis):
    """Belirli bir tipteki odalardan, 'Temiz' durumda olan ve müsait İLK odanın numarasını bulur."""
    conn = None
    try:
        conn = baglanti_olustur()
        cursor = conn.cursor()
        cursor.execute("SELECT oda_numarasi FROM odalar WHERE oda_tipi = ? AND oda_durumu = 'Temiz'", (oda_tipi,))
        tum_temiz_odalar = {row[0] for row in cursor.fetchall()}
        
        # O tarihlerde çakışan rezervasyonlardaki oda numaralarını bul
        cursor.execute("""
            SELECT oda_no FROM rezervasyonlar
            WHERE oda_no IN (SELECT oda_numarasi FROM odalar WHERE oda_tipi = ?) 
            AND giris_tarihi < ? AND cikis_tarihi > ?
        """, (oda_tipi, cikis, giris))
        dolu_odalar = {row[0] for row in cursor.fetchall()}
        
        bos_ve_temiz_odalar = tum_temiz_odalar - dolu_odalar
        return bos_ve_temiz_odalar.pop() if bos_ve_temiz_odalar else None
    except sqlite3.Error as e:
        print(f"Müsait oda bulunurken hata: {e}")
        return None
    finally:
        if conn: conn.close()

def oda_musait_mi(oda_no, giris, cikis, hariç_tutulacak_id=None):
    """Belirli bir ODA NUMARASININ o tarihlerde müsait olup olmadığını kontrol eder (Güncelleme için)."""
    conn = None
    try:
        conn = baglanti_olustur()
        cursor = conn.cursor()
        sql_query = "SELECT COUNT(*) FROM rezervasyonlar WHERE oda_no = ? AND giris_tarihi < ? AND cikis_tarihi > ?"
        params = [oda_no, cikis, giris] 
        if hariç_tutulacak_id is not None:
            sql_query += " AND id != ?" 
            params.append(hariç_tutulacak_id)
        cursor.execute(sql_query, tuple(params))
        cakisma_sayisi = cursor.fetchone()[0]
        return cakisma_sayisi == 0
    except sqlite3.Error as e:
        print(f"Oda müsaitliği kontrol edilirken hata: {e}")
        return False # Hata durumunda müsait değil varsay
    finally:
        if conn: conn.close()

def get_anlik_oda_durumu(bugun_sql):
    """Bugünün tarihine göre tüm odaların durumunu (BOŞ/DOLU/Fiziksel) çeker."""
    conn = None
    try:
        conn = baglanti_olustur()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.oda_numarasi, o.oda_tipi, o.oda_durumu, r.musteri_adi, r.cikis_tarihi 
            FROM odalar o 
            LEFT JOIN rezervasyonlar r ON o.oda_numarasi = r.oda_no AND ? >= r.giris_tarihi AND ? < r.cikis_tarihi 
            ORDER BY o.oda_numarasi
        """, (bugun_sql, bugun_sql))
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Anlık oda durumu alınırken hata: {e}")
        return []
    finally:
        if conn: conn.close()

# --- REZERVASYON CRUD ---

def rezervasyon_ekle(ad, atanan_oda_no, giris, cikis, fiyat, odeme_durumu):
    """Veritabanına yeni bir rezervasyon kaydı ekler."""
    conn = None
    try:
        conn = baglanti_olustur()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO rezervasyonlar (musteri_adi, oda_no, giris_tarihi, cikis_tarihi, toplam_fiyat, odeme_durumu) VALUES (?, ?, ?, ?, ?, ?)", (ad, atanan_oda_no, giris, cikis, fiyat, odeme_durumu))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Rezervasyon eklenirken hata: {e}")
        if conn: conn.rollback()
        raise
    finally:
        if conn: conn.close()

def rezervasyon_guncelle(rezervasyon_id, ad, atanan_oda_no, giris, cikis, fiyat, odeme_durumu):
    """Belirtilen ID'ye sahip rezervasyon kaydını günceller."""
    conn = None
    try:
        conn = baglanti_olustur()
        cursor = conn.cursor()
        cursor.execute("UPDATE rezervasyonlar SET musteri_adi = ?, oda_no = ?, giris_tarihi = ?, cikis_tarihi = ?, toplam_fiyat = ?, odeme_durumu = ? WHERE id = ?", (ad, atanan_oda_no, giris, cikis, fiyat, odeme_durumu, rezervasyon_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Rezervasyon güncellenirken hata: {e}")
        if conn: conn.rollback()
        raise
    finally:
        if conn: conn.close()

def rezervasyonlari_cek():
    """Tüm rezervasyonları listelemek için çeker."""
    conn = None
    try:
        conn = baglanti_olustur()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.id, r.musteri_adi, o.oda_tipi, r.oda_no, r.giris_tarihi, r.cikis_tarihi, 
                   r.toplam_fiyat, r.odeme_durumu 
            FROM rezervasyonlar r 
            JOIN odalar o ON r.oda_no = o.oda_numarasi 
            ORDER BY r.giris_tarihi
        """)
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Rezervasyonlar çekilirken hata: {e}")
        return []
    finally:
        if conn: conn.close()

def rezervasyon_sil(rezervasyon_id):
    """Veritabanından belirli bir ID'ye sahip kaydı siler."""
    conn = None
    try:
        conn = baglanti_olustur()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM rezervasyonlar WHERE id=?", (rezervasyon_id,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Rezervasyon silinirken hata: {e}")
        if conn: conn.rollback()
        raise
    finally:
        if conn: conn.close()

def rezervasyon_ara(arama_metni):
    """Müşteri adı, oda tipi, oda no veya ödeme durumuna göre arar."""
    conn = None
    try:
        conn = baglanti_olustur()
        cursor = conn.cursor()
        arama_kosulu = f'%{arama_metni}%'
        cursor.execute("""
            SELECT r.id, r.musteri_adi, o.oda_tipi, r.oda_no, r.giris_tarihi, r.cikis_tarihi, 
                   r.toplam_fiyat, r.odeme_durumu 
            FROM rezervasyonlar r 
            JOIN odalar o ON r.oda_no = o.oda_numarasi 
            WHERE r.musteri_adi LIKE ? OR o.oda_tipi LIKE ? OR r.oda_no LIKE ? OR r.odeme_durumu LIKE ?
            ORDER BY r.giris_tarihi
        """, (arama_kosulu, arama_kosulu, arama_kosulu, arama_kosulu))
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Rezervasyon aranırken hata: {e}")
        return []
    finally:
        if conn: conn.close()

# --- CHECK-OUT ---

def check_out_yap(rezervasyon_id, oda_no):
    """Check-out işlemini otomatize eder (Transaction)."""
    conn = None
    try:
        conn = baglanti_olustur()
        cursor = conn.cursor()
        # Önce odanın var olup olmadığını kontrol etmek iyi olabilir ama şimdilik geçelim
        cursor.execute("UPDATE rezervasyonlar SET odeme_durumu = 'Tamamı Ödendi' WHERE id = ?", (rezervasyon_id,))
        cursor.execute("UPDATE odalar SET oda_durumu = 'Kirli' WHERE oda_numarasi = ?", (oda_no,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Check-out sırasında hata: {e}")
        if conn: conn.rollback()
        raise
    finally:
        if conn: conn.close()

# --- BAŞLANGIÇ ---
# Bu script import edildiğinde veritabanının hazır olmasını sağla
veritabani_baslat()
print("Veritabanı modülü yüklendi ve veritabanı hazır.")
