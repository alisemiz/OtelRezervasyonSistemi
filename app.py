import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
import sqlite3 

# Gerekli tüm fonksiyonları import et
try:
    from veritabani import (rezervasyon_ekle, rezervasyonlari_cek, rezervasyon_sil, 
                            rezervasyon_ara, rezervasyon_guncelle,
                            oda_tiplerini_cek, fiyat_getir, 
                            musait_oda_bul, oda_musait_mi,
                            get_anlik_oda_durumu,
                            odalari_cek, oda_ekle, oda_guncelle, oda_sil,
                            check_out_yap) 
except ImportError:
    # Kullanıcıya veritabani.py'nin eksik olduğunu bildir
    root = tk.Tk(); root.withdraw() # Ana pencereyi gösterme
    messagebox.showerror("Kritik Hata", "veritabani.py dosyası bulunamadı.\nLütfen program dosyalarının eksiksiz olduğundan emin olun.")
    exit() # Programdan çık
except Exception as e:
     # Veritabanı başlatılırken hata olursa yakala
    root = tk.Tk(); root.withdraw() 
    messagebox.showerror("Veritabanı Başlatma Hatası", f"Veritabanı başlatılırken hata oluştu:\n{e}\n\nProgram kapatılacak.")
    exit()

# --- YARDIMCI FONKSİYON ---
def tarihi_cevir(tarih_str, gelen_format=None, hedef_format="%Y-%m-%d"):
    """
    Tarih formatını bir formattan diğerine çevirir. Gelen formatı otomatik algılar.
    Hata durumunda boş metin ("") döndürür.
    """
    if not tarih_str or tarih_str == "None": return ""
    if gelen_format is None: # Otomatik algılama
        if len(tarih_str) == 10 and tarih_str.count('-') == 2: gelen_format = "%Y-%m-%d" 
        elif len(tarih_str) == 10 and tarih_str.count('.') == 2: gelen_format = "%d.%m.%Y"
        elif len(tarih_str) == 10 and tarih_str.count('/') == 2: gelen_format = "%d/%m/%Y"
        else: return "" # Bilinmeyen format
    try:
        dt_obj = datetime.strptime(tarih_str, gelen_format)
        return dt_obj.strftime(hedef_format)
    except ValueError:
        return "" # Hata durumunda boş metin

# --- ODA DURUM PANELİ SINIFI ---
class OdaDurumPaneli(tk.Toplevel):
    """Anlık oda durumunu (rezervasyon ve fiziksel) gösteren pencere."""
    def __init__(self, master):
        super().__init__(master)
        self.title("Anlık Oda Durum Paneli")
        self.geometry("800x550")
        self.transient(master); self.grab_set() # Ana pencerenin üzerinde ve odaklı
        
        self._arayuzu_olustur()
        # İlk veriyi yükle (başlangıçta bugünün tarihiyle)
        bugun_sql = datetime.now().strftime("%Y-%m-%d")
        bugun_gosterim = datetime.now().strftime("%d.%m.%Y")
        self.verileri_yukle(bugun_sql, bugun_gosterim) 
        
    def _arayuzu_olustur(self):
        """Panelin görsel bileşenlerini oluşturur."""
         # Tarih Seçim Alanı
        kontrol_frame = tk.Frame(self, pady=5); kontrol_frame.pack()
        bugun_gosterim = datetime.now().strftime("%d/%m/%Y")
        tk.Label(kontrol_frame, text="Tarih Seç (GG/AA/YYYY):", font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        self.tarih_var = tk.StringVar(value=bugun_gosterim)
        tk.Entry(kontrol_frame, textvariable=self.tarih_var, width=12, font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        tk.Button(kontrol_frame, text="Tarihi Kontrol Et", command=self.tarihi_guncelle, font=('Arial', 9, 'bold'), bg="#007bff", fg="white").pack(side=tk.LEFT, padx=5)
        
        # Başlık (verileri_yukle içinde güncellenecek)
        self.baslik_label = tk.Label(self, text="Oda Durumu", font=('Arial', 14, 'bold'))
        self.baslik_label.pack(pady=5)
        
        # Liste Alanı
        tree_frame = tk.Frame(self); tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.sutunlar = ("Oda No", "Oda Tipi", "Rezervasyon Durumu", "Fiziksel Durum", "Müşteri", "Çıkış Tarihi")
        self.tree = ttk.Treeview(tree_frame, columns=self.sutunlar, show="headings")
        self._treeview_kolon_ayarla() # Kolonları ayarla
        self._treeview_renk_ayarla() # Renkleri ayarla
        
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview); vsb.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)

    def _treeview_kolon_ayarla(self):
        """Bu paneldeki Treeview kolonlarını ayarlar."""
        for col in self.sutunlar: 
            self.tree.heading(col, text=col)
            width = 180 if col == "Müşteri" else 130 if col=="Rezervasyon Durumu" else 100
            anchor = tk.W if col == "Müşteri" else tk.CENTER
            self.tree.column(col, width=width, anchor=anchor)
            
    def _treeview_renk_ayarla(self):
        """Treeview satır renklerini tanımlar."""
        self.tree.tag_configure('bos_temiz', background='#c8e6c9') # Yeşil
        self.tree.tag_configure('dolu', background='#ffcdd2') # Kırmızı
        self.tree.tag_configure('bos_diger', background='#fff9c4') # Sarı (Kirli, Tadilatta)

    def tarihi_guncelle(self):
        """Girilen tarihe göre oda durumlarını yeniden yükler."""
        tarih_sql = tarihi_cevir(self.tarih_var.get(), hedef_format="%Y-%m-%d")
        if not tarih_sql:
            messagebox.showerror("Hata", "Geçersiz tarih formatı.\nLütfen GG/AA/YYYY formatında giriniz.", parent=self)
            return
        tarih_gosterim = tarihi_cevir(tarih_sql, hedef_format="%d.%m.%Y")
        self.verileri_yukle(tarih_sql, tarih_gosterim)

    def verileri_yukle(self, tarih_sql, tarih_gosterim):
        """Belirtilen tarihe göre veritabanından verileri çeker ve listeyi günceller."""
        self.baslik_label.config(text=f"Oda Durumu ({tarih_gosterim})")
        self.tree.delete(*self.tree.get_children()) # Listeyi temizle
        try: 
            durum_listesi = get_anlik_oda_durumu(tarih_sql)
        except Exception as e:
            messagebox.showerror("Veritabanı Hatası", f"Oda durumları çekilirken hata oluştu:\n{e}", parent=self)
            return
            
        for oda in durum_listesi:
            # (oda_no, oda_tipi, fiziksel_durum, musteri_adi, cikis_tarihi)
            try:
                oda_no, tip, fiziksel_durum, musteri, cikis_sql = oda[0], oda[1], oda[2], oda[3], oda[4]
                if musteri is None: # Rezervasyon yok (BOŞ)
                    rez_durumu, musteri_goster, cikis_goster = "BOŞ", "---", "---"
                    tag = 'bos_temiz' if fiziksel_durum == "Temiz" else 'bos_diger'
                else: # Rezervasyon var (DOLU)
                    rez_durumu, musteri_goster, tag = "DOLU", musteri, 'dolu'
                    cikis_goster = tarihi_cevir(cikis_sql, hedef_format="%d.%m.%Y")
                
                degerler = (oda_no, tip, rez_durumu, fiziksel_durum, musteri_goster, cikis_goster)
                self.tree.insert("", tk.END, values=degerler, tags=(tag,))
            except IndexError:
                 print(f"Hatalı oda durum verisi (IndexError): {oda}") # Hata ayıklama


# --- ODA YÖNETİM PANELİ SINIFI ---
class OdaYonetimPaneli(tk.Toplevel):
    """Odaları ekleme, güncelleme, silme ve durumunu değiştirme paneli."""
    def __init__(self, master, ana_uygulama):
        super().__init__(master)
        self.title("Yönetici: Oda Yönetimi")
        self.geometry("850x500")
        self.transient(master); self.grab_set(); self.ana_uygulama = ana_uygulama
        self.FIZIKSEL_DURUMLAR = ["Temiz", "Kirli", "Tadilatta"]
        
        self._arayuzu_olustur()
        self.odalari_listele() # Odaları listele

    def _arayuzu_olustur(self):
        """Panelin görsel bileşenlerini oluşturur."""
         # --- Sol Taraf: Form ---
        form_cerceve = tk.Frame(self, padx=10, pady=10); form_cerceve.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        tk.Label(form_cerceve, text="Oda Yönetim Formu", font=('Arial', 14, 'bold')).pack(pady=10)
        self.form_entry_vars = {}; self.form_entry_widgets = {}
        form_etiketler = ["Oda Numarası:", "Oda Tipi:", "Günlük Fiyat:", "Oda Durumu:"]
        for etiket_text in form_etiketler:
            cerceve = tk.Frame(form_cerceve); cerceve.pack(fill=tk.X, pady=5)
            tk.Label(cerceve, text=etiket_text, width=12, anchor='w').pack(side=tk.LEFT)
            var = tk.StringVar(); widget = None
            if etiket_text == "Oda Durumu:": widget = ttk.Combobox(cerceve, textvariable=var, width=18, state="readonly"); widget['values'] = self.FIZIKSEL_DURUMLAR; widget.set("Temiz")
            else: widget = tk.Entry(cerceve, textvariable=var, width=20)
            widget.pack(side=tk.LEFT, padx=5); self.form_entry_vars[etiket_text] = var; self.form_entry_widgets[etiket_text] = widget
        self.oda_no_entry_widget = self.form_entry_widgets["Oda Numarası:"] # Oda No Entry'sine erişim
        buton_cerceve = tk.Frame(form_cerceve); buton_cerceve.pack(pady=20)
        tk.Button(buton_cerceve, text="Ekle", command=self.oda_ekle, bg="#4CAF50", fg="white", width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(buton_cerceve, text="Güncelle", command=self.oda_guncelle, bg="#FFA500", fg="white", width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(buton_cerceve, text="Sil", command=self.oda_sil, bg="#D32F2F", fg="white", width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(form_cerceve, text="Formu Temizle", command=self.formu_temizle).pack(pady=5)
        
        # --- Sağ Taraf: Liste ---
        list_cerceve = tk.Frame(self); list_cerceve.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        tk.Label(list_cerceve, text="Mevcut Odalar", font=('Arial', 14, 'bold')).pack(pady=10)
        self.sutunlar = ("Oda Numarası", "Oda Tipi", "Günlük Fiyat", "Oda Durumu")
        self.tree = ttk.Treeview(list_cerceve, columns=self.sutunlar, show="headings")
        self._treeview_kolon_ayarla() # Kolonları ayarla
        vsb = ttk.Scrollbar(list_cerceve, orient="vertical", command=self.tree.yview); vsb.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=vsb.set); self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind('<ButtonRelease-1>', self.kaydi_forma_yukle)

    def _treeview_kolon_ayarla(self):
        """Bu paneldeki Treeview kolonlarını ayarlar."""
        for col in self.sutunlar: 
            self.tree.heading(col, text=col)
            self.tree.column(col, width=110, anchor=tk.CENTER)

    def odalari_listele(self):
        """Veritabanından odaları çeker ve listeyi günceller."""
        self.tree.delete(*self.tree.get_children())
        try:
            for oda in odalari_cek(): 
                # (oda_no, tip, fiyat, durum)
                try:
                    fiyat_gosterim = f"{oda[2]:,.2f} TL"
                    self.tree.insert("", tk.END, values=(oda[0], oda[1], fiyat_gosterim, oda[3]))
                except IndexError:
                    print(f"Hatalı oda verisi (IndexError): {oda}")
        except Exception as e:
            messagebox.showerror("Hata", f"Odalar listelenirken hata oluştu:\n{e}", parent=self)
            
    def formu_temizle(self):
        """Oda yönetim formunu temizler."""
        for etiket, var in self.form_entry_vars.items():
            var.set("Temiz" if etiket == "Oda Durumu:" else "")
        self.oda_no_entry_widget.config(state='normal') # Oda No'yu tekrar aktif yap

    def kaydi_forma_yukle(self, event):
        """Listeden seçilen odayı forma yükler."""
        secili_kayit = self.tree.selection()
        if not secili_kayit: return
        degerler = self.tree.item(secili_kayit[0], 'values')
        # (oda_no, tip, fiyat_str, durum)
        try: fiyat = float(degerler[2].replace(" TL", "").replace(",", "")) # Fiyatı sayıya çevir
        except: fiyat = 0.0
        self.form_entry_vars["Oda Numarası:"].set(degerler[0])
        self.form_entry_vars["Oda Tipi:"].set(degerler[1])
        self.form_entry_vars["Günlük Fiyat:"].set(f"{fiyat:.2f}") # Formatlı yükle
        self.form_entry_vars["Oda Durumu:"].set(degerler[3])
        self.oda_no_entry_widget.config(state='disabled') # Oda No güncellenirken değiştirilemez

    def _formdan_veri_al(self):
        """Formdaki verileri alır ve doğrular."""
        oda_no = self.form_entry_vars["Oda Numarası:"].get().strip()
        oda_tipi = self.form_entry_vars["Oda Tipi:"].get().strip()
        fiyat_str = self.form_entry_vars["Günlük Fiyat:"].get().strip()
        durum = self.form_entry_vars["Oda Durumu:"].get()
        
        if not all([oda_no, oda_tipi, fiyat_str, durum]):
            raise ValueError("Tüm alanlar doldurulmalıdır.")
        
        try:
            fiyat = float(fiyat_str.replace(",", ".")) # Virgülü noktaya çevir
            if fiyat <= 0: raise ValueError("Günlük Fiyat pozitif bir sayı olmalıdır.")
        except ValueError:
             raise ValueError("Lütfen 'Günlük Fiyat' alanı için geçerli bir sayı girin (örn: 1500.00 veya 1500,00).")
             
        return oda_no, oda_tipi, fiyat, durum

    def oda_ekle(self):
        """Formdaki verilerle yeni oda ekler."""
        try:
            oda_no, oda_tipi, fiyat, durum = self._formdan_veri_al()
            oda_ekle(oda_no, oda_tipi, fiyat, durum)
            messagebox.showinfo("Başarılı", f"Oda {oda_no} başarıyla eklendi.", parent=self)
            self.odalari_listele(); self.formu_temizle()
            self.ana_uygulama.refresh_oda_tipleri_combobox() # Ana formdaki listeyi yenile
        except sqlite3.IntegrityError:
            messagebox.showerror("Hata", f"Oda numarası '{oda_no}' zaten mevcut. Farklı bir numara girin.", parent=self)
        except ValueError as e: # Formdan_veri_al'dan gelen hata
            messagebox.showerror("Hata", str(e), parent=self)
        except Exception as e:
            messagebox.showerror("Hata", f"Oda eklenirken beklenmedik bir hata oluştu:\n{e}", parent=self)

    def oda_guncelle(self):
        """Formdaki verilerle seçili odayı günceller."""
        oda_no_form = self.form_entry_vars["Oda Numarası:"].get().strip() # Güncellenecek odanın no'su
        if not oda_no_form:
            messagebox.showwarning("Eksik Bilgi", "Lütfen listeden güncellenecek bir oda seçin.", parent=self)
            return
        try:
            # Oda No hariç diğer verileri al ve doğrula (Oda No güncellenemez)
            _, oda_tipi, fiyat, durum = self._formdan_veri_al() 
            
            oda_guncelle(oda_no_form, oda_tipi, fiyat, durum)
            messagebox.showinfo("Başarılı", f"Oda {oda_no_form} başarıyla güncellendi.", parent=self)
            self.odalari_listele(); self.formu_temizle()
            self.ana_uygulama.refresh_oda_tipleri_combobox() # Ana formdaki listeyi yenile
        except ValueError as e: # Formdan_veri_al'dan gelen hata
            messagebox.showerror("Hata", str(e), parent=self)
        except Exception as e:
            messagebox.showerror("Hata", f"Oda güncellenirken beklenmedik bir hata oluştu:\n{e}", parent=self)

    def oda_sil(self):
        """Listeden seçili odayı siler."""
        oda_no = self.form_entry_vars["Oda Numarası:"].get().strip()
        if not oda_no:
            messagebox.showwarning("Eksik Bilgi", "Lütfen listeden silinecek bir oda seçin.", parent=self)
            return
        if not messagebox.askyesno("Onay", f"Oda {oda_no}'ı silmek istediğinizden emin misiniz?\nBu işlem geri alınamaz.", parent=self):
            return
        try:
            oda_sil(oda_no) # Rezervasyon varsa ValueError fırlatır
            messagebox.showinfo("Başarılı", f"Oda {oda_no} başarıyla silindi.", parent=self)
            self.odalari_listele(); self.formu_temizle()
            self.ana_uygulama.refresh_oda_tipleri_combobox() # Ana formdaki listeyi yenile
        except ValueError as e: # Veritabanından gelen "rezervasyon var" hatası
            messagebox.showerror("Silinemedi", str(e), parent=self)
        except Exception as e:
            messagebox.showerror("Hata", f"Oda silinirken beklenmedik bir hata oluştu:\n{e}", parent=self)

# --- ANA UYGULAMA SINIFI ---
class OtelRezervasyonSistemi:
    """Ana Otel Rezervasyon Sistemi Uygulaması."""
    def __init__(self, master):
        self.master = master
        master.title("Otel Rezervasyon Sistemi (v2.7 - Check-Out) [Optimize Edilmiş]")
        master.geometry("1200x600")
        master.minsize(1200, 600)
        
        self.guncellenen_kayit_id = None 
        self.guncellenen_oda_no = None 
        self.ODEME_DURUMLARI = ["Ödenmedi", "Kapora Alındı", "Tamamı Ödendi"]
        self.entry_vars = {} 
        
        try:
            self._arayuzu_olustur() # Arayüzü oluştur
            self.rezervasyonlari_goster() # İlk açılışta listeyi doldur
        except Exception as e:
             # Arayüz veya ilk veri yükleme hatası
            messagebox.showerror("Başlatma Hatası", f"Arayüz oluşturulurken veya ilk veriler yüklenirken hata oluştu:\n{e}")
            master.destroy() # Pencereyi kapat

    def _arayuzu_olustur(self):
        """Ana pencerenin tüm görsel bileşenlerini oluşturur."""
        
        # --- Rezervasyon Formu ---
        self.form_frame = tk.Frame(self.master, padx=10, pady=10)
        self.form_frame.pack(padx=10, pady=10)
        self.etiketler = ["Müşteri Adı:", "Oda Tipi:", "Giriş Tarihi (GG/AA/YYYY):", 
                          "Çıkış Tarihi (GG/AA/YYYY):", "Ödeme Durumu:"]
        self.entry_dict = {} 
        for i, etiket_text in enumerate(self.etiketler):
            etiket = tk.Label(self.form_frame, text=etiket_text, font=('Arial', 10)); etiket.grid(row=i, column=0, sticky="w", pady=5, padx=5)
            var = tk.StringVar(); widget = None
            if etiket_text == "Oda Tipi:": 
                self.oda_tipi_combobox = ttk.Combobox(self.form_frame, width=28, font=('Arial', 10), textvariable=var, state="readonly"); widget = self.oda_tipi_combobox
            elif etiket_text == "Ödeme Durumu:": 
                widget = ttk.Combobox(self.form_frame, width=28, font=('Arial', 10), textvariable=var, state="readonly"); widget['values'] = self.ODEME_DURUMLARI; widget.set(self.ODEME_DURUMLARI[0])
            else: # Müşteri Adı (Entry) ve Tarihler (Entry)
                widget = tk.Entry(self.form_frame, width=30, font=('Arial', 10), textvariable=var)
            widget.grid(row=i, column=1, pady=5, padx=5); self.entry_dict[etiket_text] = widget; self.entry_vars[etiket_text] = var 
        self.refresh_oda_tipleri_combobox() # Oda tiplerini yükle
        
        # Form Butonları
        self.form_buton_frame = tk.Frame(self.form_frame); self.form_buton_frame.grid(row=len(self.etiketler), column=0, columnspan=2, pady=10)
        self.rez_buton = tk.Button(self.form_buton_frame, text="Rezervasyon Yap/Güncelle", command=self.rezervasyon_yap, bg="#4CAF50", fg="white", font=('Arial', 10, 'bold'), width=25); self.rez_buton.pack(side=tk.LEFT, padx=5)
        self.form_temizle_buton = tk.Button(self.form_buton_frame, text="Temizle", command=self.temizle_form, font=('Arial', 10), width=10); self.form_temizle_buton.pack(side=tk.LEFT, padx=5)
        
        # --- Arama Çubuğu ---
        self.arama_frame = tk.Frame(self.master, padx=10, pady=5); self.arama_frame.pack(padx=10, pady=5, fill=tk.X)
        tk.Label(self.arama_frame, text="Arama (Ad/Tip/Oda No/Ödeme):", font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        self.arama_entry = tk.Entry(self.arama_frame, width=25, font=('Arial', 10)); self.arama_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(self.arama_frame, text="Ara", command=self.arama_yap, font=('Arial', 10), bg="#007bff", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(self.arama_frame, text="Aramayı Temizle", command=self.temizle_arama, font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        
        # --- Rezervasyon Listesi (Treeview) ---
        self.list_frame = tk.Frame(self.master); self.list_frame.pack(padx=10, pady=10, fill="both", expand=True)
        self.sutunlar = ("ID", "Müşteri Adı", "Oda Tipi", "Oda No", "Giriş Tarihi", 
                         "Çıkış Tarihi", "Toplam Fiyat", "Ödeme Durumu")
        self.tree = ttk.Treeview(self.list_frame, columns=self.sutunlar, show="headings")
        self._treeview_kolon_ayarla() # Kolonları ayarla
        self._treeview_renk_ayarla() # Renkleri tanımla
        self.tree.pack(side="left", fill="both", expand=True)
        vsb = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.tree.yview); vsb.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.bind('<ButtonRelease-1>', self.kaydi_forma_yukle) # Seçince forma yükle
        
        # --- Alt Kontrol Butonları ---
        self.buton_frame = tk.Frame(self.master); self.buton_frame.pack(pady=10)
        tk.Button(self.buton_frame, text="Oda Yönetimi", command=self.oda_yonetim_panelini_ac, bg="#607D8B", fg="white", font=('Arial', 10, 'bold'), width=20).pack(side=tk.LEFT, padx=5)
        tk.Button(self.buton_frame, text="Oda Durum Paneli", command=self.oda_panelini_ac, bg="#1E90FF", fg="white", font=('Arial', 10, 'bold'), width=20).pack(side=tk.LEFT, padx=5)
        tk.Button(self.buton_frame, text="Seçili Kaydı Check-Out Yap", command=self.check_out_yap, bg="#FF9800", fg="white", font=('Arial', 10, 'bold'), width=25).pack(side=tk.LEFT, padx=5)
        tk.Button(self.buton_frame, text="Seçili Rezervasyonu SİL", command=self.sil_secili_rezervasyon, bg="#D32F2F", fg="white", font=('Arial', 10, 'bold'), width=25).pack(side=tk.LEFT, padx=5) 

    def _treeview_kolon_ayarla(self):
        """Ana Treeview kolon başlıklarını ve genişliklerini ayarlar."""
        for col in self.sutunlar: 
            self.tree.heading(col, text=col)
            width = 150 if col == "Müşteri Adı" else 40 if col=="ID" else 60 if col=="Oda No" else 100 if col in ["Toplam Fiyat","Oda Tipi"] else 110
            anchor = tk.W if col=="Müşteri Adı" else tk.E if col=="Toplam Fiyat" else tk.CENTER
            self.tree.column(col, width=width, anchor=anchor)

    def _treeview_renk_ayarla(self):
        """Ana Treeview satır renklerini tanımlar."""
        self.tree.tag_configure('odenmedi', background='#ffcdd2') # Kırmızı
        self.tree.tag_configure('kapora', background='#fff9c4')  # Sarı
        self.tree.tag_configure('odendi', background='#c8e6c9')   # Yeşil
        
    def _guncelle_rezervasyon_listesi(self, rezervasyon_listesi):
        """Treeview'ı verilen rezervasyon listesiyle günceller (DRY)."""
        self.tree.delete(*self.tree.get_children()) # Mevcut listeyi temizle
        if not rezervasyon_listesi: return # Boşsa çık
            
        for kayit in rezervasyon_listesi:
            # (id, musteri_adi, tip, oda_no, giris, cikis, fiyat, odeme_durumu)
            try:
                giris_gosterim = tarihi_cevir(kayit[4], hedef_format="%d.%m.%Y")
                cikis_gosterim = tarihi_cevir(kayit[5], hedef_format="%d.%m.%Y")
                fiyat_gosterim = f"{kayit[6]:,.2f} TL"
                odeme_durumu = kayit[7]
                
                # Sadece görünür sütunları al (veritabanından gelen sırayla eşleşmeli)
                gosterilecek_kayit = (kayit[0], kayit[1], kayit[2], kayit[3], 
                                      giris_gosterim, cikis_gosterim, 
                                      fiyat_gosterim, odeme_durumu)
                                      
                tag = self.odeme_durumu_tagi(odeme_durumu)
                self.tree.insert("", tk.END, values=gosterilecek_kayit, tags=(tag,))
            except IndexError:
                print(f"Hatalı rezervasyon verisi (IndexError): {kayit}") # Hata ayıklama
            except Exception as e:
                print(f"Liste güncellenirken hata: {e} - Kayıt: {kayit}") # Hata ayıklama

    # --- Panel Açma Fonksiyonları ---
    def oda_yonetim_panelini_ac(self): 
        try: OdaYonetimPaneli(self.master, self).wait_window() 
        except Exception as e: messagebox.showerror("Panel Hatası", f"Oda Yönetim Paneli açılamadı:\n{e}")
    def oda_panelini_ac(self): 
        try: OdaDurumPaneli(self.master).wait_window() 
        except Exception as e: messagebox.showerror("Panel Hatası", f"Oda Durum Paneli açılamadı:\n{e}")
        
    # --- ComboBox Yenileme ---
    def refresh_oda_tipleri_combobox(self):
        """Oda Tipi ComboBox'ını günceller."""
        try: 
            mevcut_deger = self.entry_vars.get("Oda Tipi:", tk.StringVar()).get() # Daha güvenli alma
            self.oda_tipi_combobox['values'] = oda_tiplerini_cek()
            if mevcut_deger in self.oda_tipi_combobox['values']: self.entry_vars["Oda Tipi:"].set(mevcut_deger)
            else: self.entry_vars["Oda Tipi:"].set("") # Eşleşmiyorsa temizle
        except Exception as e: messagebox.showerror("Hata", f"Oda tipleri yenilenemedi:\n{e}")

    # --- Yardımcı Fonksiyonlar ---
    def odeme_durumu_tagi(self, durum):
        """Ödeme durumuna göre renk tag'ı döndürür."""
        if durum == "Tamamı Ödendi": return 'odendi'
        elif durum == "Kapora Alındı": return 'kapora'
        else: return 'odenmedi'
        
    # --- Form İşlevleri ---
    def temizle_form(self):
        """Rezervasyon formunu temizler ve yeni kayıt moduna geçer."""
        for etiket, var in self.entry_vars.items(): 
            var.set(self.ODEME_DURUMLARI[0] if etiket == "Ödeme Durumu:" else "")
        self.guncellenen_kayit_id = None; self.guncellenen_oda_no = None
        self.rez_buton.config(text="Rezervasyon Yap", bg="#4CAF50") # Butonu yeşil yap

    def kaydi_forma_yukle(self, event):
        """Listeden seçilen rezervasyonu forma yükler (güncelleme modu)."""
        secili_kayit = self.tree.selection()
        if not secili_kayit: self.temizle_form(); return # Seçim yoksa formu temizle
        
        secili_kayit = secili_kayit[0]
        degerler = self.tree.item(secili_kayit, 'values')
        # (id, musteri_adi, tip, oda_no, giris_gosterim, cikis_gosterim, fiyat_gosterim, odeme_durumu)
        try:
            self.guncellenen_kayit_id = int(degerler[0])
            self.guncellenen_oda_no = degerler[3] 
        except (ValueError, IndexError):
            messagebox.showerror("Hata", "Kayıt verisi okunamadı. Lütfen listeyi yenileyin.")
            self.temizle_form(); return
            
        self.temizle_form() # Önce temizle
        
        # ID ve Oda No'yu tekrar ayarla
        self.guncellenen_kayit_id = int(degerler[0])
        self.guncellenen_oda_no = degerler[3]
        
        # Tarihleri forma uygun formata çevir (GG/AA/YYYY)
        giris_tarihi_form = tarihi_cevir(degerler[4], hedef_format="%d/%m/%Y")
        cikis_tarihi_form = tarihi_cevir(degerler[5], hedef_format="%d/%m/%Y")
        
        # Formu doldur
        self.entry_vars["Müşteri Adı:"].set(degerler[1])
        self.entry_vars["Oda Tipi:"].set(degerler[2]) 
        self.entry_vars["Giriş Tarihi (GG/AA/YYYY):"].set(giris_tarihi_form)
        self.entry_vars["Çıkış Tarihi (GG/AA/YYYY):"].set(cikis_tarihi_form)
        self.entry_vars["Ödeme Durumu:"].set(degerler[7]) 
        
        self.rez_buton.config(text="Rezervasyonu GÜNCELLE", bg="#FFA500") # Butonu turuncu yap

    # --- Ana İş Mantığı ---
    def rezervasyon_yap(self):
        """Yeni rezervasyon ekler veya mevcut olanı günceller."""
        # Formdan verileri al
        ad = self.entry_vars["Müşteri Adı:"].get().strip()
        oda_tipi = self.entry_vars["Oda Tipi:"].get()
        giris_str = self.entry_vars["Giriş Tarihi (GG/AA/YYYY):"].get()
        cikis_str = self.entry_vars["Çıkış Tarihi (GG/AA/YYYY):"].get()
        odeme_durumu = self.entry_vars["Ödeme Durumu:"].get()
        
        # Temel doğrulamalar
        if not all([ad, oda_tipi, giris_str, cikis_str, odeme_durumu]):
            messagebox.showerror("Hata", "Lütfen tüm alanları doldurun.")
            return
        
        # Tarihleri işle
        try:
            giris_dt = datetime.strptime(giris_str, "%d/%m/%Y")
            cikis_dt = datetime.strptime(cikis_str, "%d/%m/%Y")
        except ValueError:
            messagebox.showerror("Hata", "Lütfen tarihleri GG/AA/YYYY formatında doğru giriniz.")
            return
        giris_sql = giris_dt.strftime("%Y-%m-%d")
        cikis_sql = cikis_dt.strftime("%Y-%m-%d")
        if giris_dt >= cikis_dt:
            messagebox.showerror("Hata", "Çıkış tarihi, giriş tarihinden sonra olmalıdır.")
            return
            
        # Fiyatı hesapla
        try:
            gunluk_fiyat = fiyat_getir(oda_tipi)
            if gunluk_fiyat <= 0: raise ValueError # Fiyat alınamadı veya 0
        except Exception:
            messagebox.showerror("Hata", f"'{oda_tipi}' için fiyat bilgisi alınamadı.\nLütfen Oda Yönetimi panelinden kontrol edin.", parent=self.master)
            return
        gun_sayisi = (cikis_dt - giris_dt).days
        toplam_fiyat = gun_sayisi * gunluk_fiyat
        if toplam_fiyat <= 0:
             messagebox.showerror("Hata", f"Geçersiz gün sayısı veya fiyat nedeniyle tutar hesaplanamadı.")
             return
             
        # Veritabanı işlemi (Ekleme veya Güncelleme)
        try:
            if self.guncellenen_kayit_id is None: # Yeni Kayıt
                atanan_oda = musait_oda_bul(oda_tipi, giris_sql, cikis_sql)
                if atanan_oda is None:
                    messagebox.showerror("Dolu!", f"Maalesef '{oda_tipi}' tipinde, belirtilen tarihler arasında TEMİZ ve BOŞ oda bulunamadı.")
                    return
                rezervasyon_ekle(ad, atanan_oda, giris_sql, cikis_sql, toplam_fiyat, odeme_durumu)
                messagebox.showinfo("Başarılı", f"Rezervasyon yapıldı!\nOda No: {atanan_oda}\nTutar: {toplam_fiyat:,.2f} TL")
            else: # Güncelleme
                # Oda tipi değiştiyse yeni boş oda bulmaya çalış
                secili_kayit_values = self.tree.item(self.tree.selection()[0], 'values')
                mevcut_oda_tipi = secili_kayit_values[2]
                atanacak_oda_no = self.guncellenen_oda_no # Varsayılan olarak mevcut odayı koru
                
                if oda_tipi != mevcut_oda_tipi: # Oda tipi değiştiyse
                    yeni_atanan_oda = musait_oda_bul(oda_tipi, giris_sql, cikis_sql)
                    if yeni_atanan_oda is None:
                        messagebox.showerror("Dolu!", f"Maalesef yeni seçilen '{oda_tipi}' tipinde boş/temiz oda bulunamadı.")
                        return
                    atanacak_oda_no = yeni_atanan_oda # Yeni odayı ata
                else: # Oda tipi aynı, sadece tarihler değişmiş olabilir
                    # Mevcut odanın yeni tarihlerde (kendisi hariç) müsaitliğini kontrol et
                    if not oda_musait_mi(self.guncellenen_oda_no, giris_sql, cikis_sql, self.guncellenen_kayit_id):
                        messagebox.showerror("Çakışma!", f"Oda {self.guncellenen_oda_no} seçtiğiniz yeni tarihlerde başka bir rezervasyonla çakışıyor.")
                        return
                    # Oda numarası aynı kalacak (atanacak_oda_no)
                
                rezervasyon_guncelle(self.guncellenen_kayit_id, ad, atanacak_oda_no, giris_sql, cikis_sql, toplam_fiyat, odeme_durumu)
                messagebox.showinfo("Başarılı", f"Rezervasyon ID: {self.guncellenen_kayit_id} başarıyla güncellendi.\nAtanan Oda No: {atanacak_oda_no}")
            
            # İşlem başarılıysa formu temizle ve listeyi yenile
            self.temizle_form()
            self.rezervasyonlari_goster()
            
        except Exception as e:
            messagebox.showerror("Veritabanı Hatası", f"Rezervasyon kaydedilirken/güncellenirken bir hata oluştu:\n{e}")

    # --- Liste Güncelleme / Arama ---
    def rezervasyonlari_goster(self):
        """Tüm rezervasyonları veritabanından çeker ve listeler."""
        try: liste = rezervasyonlari_cek()
        except Exception as e: 
            messagebox.showerror("Hata", f"Rezervasyonlar çekilirken hata oluştu:\n{e}"); return
        self._guncelle_rezervasyon_listesi(liste)

    def arama_yap(self):
        """Genel arama kutusundaki metne göre arama yapar ve listeyi günceller."""
        arama_metni = self.arama_entry.get().strip()
        if not arama_metni: # Boşsa tümünü göster
            self.rezervasyonlari_goster(); return 
        try: liste = rezervasyon_ara(arama_metni)
        except Exception as e: 
            messagebox.showerror("Hata", f"Arama yapılırken hata oluştu:\n{e}"); return
        self._guncelle_rezervasyon_listesi(liste)
        if not liste: messagebox.showinfo("Sonuç Yok", f"'{arama_metni}' ile eşleşen kayıt bulunamadı.")

    def temizle_arama(self):
        """Arama kutusunu temizler ve tüm rezervasyonları gösterir."""
        self.arama_entry.delete(0, tk.END)
        self.rezervasyonlari_goster() # Tüm listeyi tekrar göster

    # --- Silme ve Check-Out ---
    def sil_secili_rezervasyon(self): 
        """Listeden seçili rezervasyonu siler."""
        secili_kayit = self.tree.selection()
        if not secili_kayit: messagebox.showwarning("Uyarı", "Silmek için listeden bir rezervasyon seçin."); return
        onay = messagebox.askyesno("Onay", "Seçili rezervasyonu silmek istediğinizden emin misiniz?")
        if onay: 
            try:
                secili_değerler = self.tree.item(secili_kayit[0])['values']
                rez_id = int(secili_değerler[0]) 
                rezervasyon_sil(rez_id)
                messagebox.showinfo("Başarılı", f"Rezervasyon ID: {rez_id} başarıyla silindi.")
                self.rezervasyonlari_goster(); self.temizle_form()
            except (ValueError, IndexError):
                 messagebox.showerror("Hata", "Kayıt ID'si okunamadı.")
            except Exception as e: 
                messagebox.showerror("Hata", f"Silme işlemi sırasında hata oluştu:\n{e}")

    def check_out_yap(self):
        """Seçili rezervasyon için check-out işlemini yapar."""
        secili_kayit = self.tree.selection(); 
        if not secili_kayit: messagebox.showwarning("Uyarı", "Check-out için listeden bir rezervasyon seçin."); return
        
        try:
            secili_kayit_id = secili_kayit[0]
            degerler = self.tree.item(secili_kayit_id, 'values')
            rez_id = int(degerler[0])
            musteri_adi = degerler[1]
            oda_no = degerler[3]
        except (ValueError, IndexError):
            messagebox.showerror("Hata", "Kayıt verisi okunamadı."); return
            
        onay = messagebox.askyesno("Check-Out Onayı", 
            f"Müşteri: {musteri_adi}\nOda No: {oda_no}\n\n"
            f"Check-out yapılacak:\n"
            f"  - Ödeme 'Tamamı Ödendi' olacak.\n"
            f"  - Oda '{oda_no}' durumu 'Kirli' olacak.\n\n"
            f"Onaylıyor musunuz?", parent=self.master)
        
        if not onay: return
        
        try: 
            check_out_yap(rez_id, oda_no) # Veritabanı işlemini yap
            messagebox.showinfo("Başarılı", f"Check-out tamamlandı.\nOda {oda_no} 'Kirli' olarak ayarlandı.", parent=self.master)
            self.rezervasyonlari_goster(); self.temizle_form() # Listeyi yenile
        except Exception as e: 
            messagebox.showerror("Hata", f"Check-out işlemi sırasında hata oluştu:\n{e}", parent=self.master)

# --- Uygulamayı Başlatma ---
if __name__ == "__main__":
    root = None # Hata durumunda destroy() için
    try:
        # Veritabanı başlatma işlemi zaten veritabani.py import edilirken yapılıyor.
        root = tk.Tk()
        uygulama = OtelRezervasyonSistemi(root)
        root.mainloop()
    except Exception as e:
        # Başlangıçta yakalanamayan kritik bir hata olursa
        print(f"KRİTİK BAŞLATMA HATASI: {e}") 
        # Mesaj kutusu için geçici root
        temp_root = tk.Tk(); temp_root.withdraw() 
        messagebox.showerror("Kritik Başlatma Hatası", f"Uygulama başlatılırken çok ciddi bir hata oluştu:\n{e}\n\nProgram kapatılacak.")
        temp_root.destroy()
        if root: # Eğer ana pencere oluşmuşsa onu da kapatmaya çalış
            try: root.destroy() 
            except: pass
