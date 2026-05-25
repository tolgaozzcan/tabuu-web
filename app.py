import sqlite3
import random
import string
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_socketio import SocketIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cok_gizli_tabuu_sifresi_2026'
# CORS izni eklendi: Telefondan veya başka ağdan gelen bağlantıları engellemez
socketio = SocketIO(app, cors_allowed_origins="*")

ADMIN_SIFRESI = "Almanca123!" 
aktif_oda_id = None 

oyun_durumu = {'takim_a_skor': 0, 'takim_b_skor': 0, 'aktif_takim': 'A'}
oyuncular = {'bekleme': [], 'takim_a': [], 'takim_b': []}
baglantilar = {} 

def veritabanindan_kelimeleri_al():
    baglanti = sqlite3.connect("kelimeler.db")
    imlec = baglanti.cursor()
    imlec.execute("SELECT * FROM kelimeler")
    kelimeler = imlec.fetchall()
    baglanti.close()
    return kelimeler

def kelimeleri_hocaya_yolla():
    tum_kelimeler = veritabanindan_kelimeleri_al()
    paket = []
    for k in tum_kelimeler:
        paket.append({'seviye': k[1], 'kelime': k[2], 'yasaklilar': [k[3], k[4], k[5], k[6]]})
    socketio.emit('kelime_havuzu', paket)

@app.route('/')
def ana_sayfa(): 
    return render_template('index.html')

@app.route('/ogrenci')
def ogrenci_girisi(): 
    return render_template('ogrenci.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin_giris():
    hata_mesaji = None
    if request.method == 'POST':
        if request.form.get('sifre') == ADMIN_SIFRESI:
            session['hoca_mi'] = True
            return redirect(url_for('admin_panel'))
        else:
            hata_mesaji = "Şifre hatalı, lütfen tekrar deneyin!"
    return render_template('admin.html', hata=hata_mesaji)

@app.route('/panel', methods=['GET', 'POST'])
def admin_panel():
    global aktif_oda_id, oyun_durumu, oyuncular, baglantilar
    if not session.get('hoca_mi'): return redirect(url_for('admin_giris'))
    
    if request.method == 'POST':
        rastgele = ''.join(random.choices(string.digits, k=4))
        aktif_oda_id = f"TABUU-{rastgele}"
        oyun_durumu = {'takim_a_skor': 0, 'takim_b_skor': 0, 'aktif_takim': 'A'}
        oyuncular = {'bekleme': [], 'takim_a': [], 'takim_b': []}
        baglantilar = {}
        socketio.emit('oyun_sifirlandi')
        return redirect(url_for('hoca_paneli'))
        
    return render_template('panel.html', oda_id=aktif_oda_id)

@app.route('/oda_kontrol', methods=['POST'])
def oda_kontrol():
    gelen_id = request.json.get('oda_id', '').strip().upper()
    if aktif_oda_id and gelen_id == aktif_oda_id:
        return jsonify({'basarili': True})
    return jsonify({'basarili': False})

@app.route('/hoca')
def hoca_paneli():
    if not session.get('hoca_mi'): return redirect(url_for('admin_giris'))
    if not aktif_oda_id: return redirect(url_for('admin_panel'))
    return render_template('hoca.html', oda_id=aktif_oda_id)

@app.route('/tahta')
def ortak_tahta():
    if not aktif_oda_id: return "Oyun henüz hocanız tarafından başlatılmadı!"
    return render_template('tahta.html')

@app.route('/oyun')
def oyun_sayfasi():
    if not aktif_oda_id: return redirect(url_for('ana_sayfa'))
    return render_template('oyun.html')

@socketio.on('oyuna_katil')
def handle_katil(data):
    gelen_isim = data['isim']
    for liste in oyuncular.values():
        if gelen_isim in liste: liste.remove(gelen_isim)
    oyuncular['bekleme'].append(gelen_isim)
    baglantilar[request.sid] = gelen_isim
    socketio.emit('oyuncular_guncellendi', oyuncular)
    socketio.emit('skor_guncellendi', oyun_durumu)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in baglantilar:
        dusen_kisi = baglantilar[request.sid]
        for liste in oyuncular.values():
            if dusen_kisi in liste: liste.remove(dusen_kisi) 
        del baglantilar[request.sid]
        socketio.emit('oyuncular_guncellendi', oyuncular)

@socketio.on('takima_ata')
def takima_ata(data):
    isim = data['isim']
    hedef_takim = data['takim'] 
    for liste in oyuncular.values():
        if isim in liste: liste.remove(isim)
    if hedef_takim in oyuncular: oyuncular[hedef_takim].append(isim)
    socketio.emit('oyuncular_guncellendi', oyuncular)

@socketio.on('sirayi_ilerlet')
def sirayi_kaydir(data):
    takim = data['takim']
    if len(oyuncular[takim]) > 1:
        ilk_kisi = oyuncular[takim].pop(0)
        oyuncular[takim].append(ilk_kisi)
        socketio.emit('oyuncular_guncellendi', oyuncular)

@socketio.on('oyuncuyu_basa_al')
def oyuncu_basa_al(data):
    isim = data['isim']
    takim = data['takim']
    if isim in oyuncular[takim]:
        oyuncular[takim].remove(isim)
        oyuncular[takim].insert(0, isim)
        if takim == 'takim_a': oyun_durumu['aktif_takim'] = 'A'
        elif takim == 'takim_b': oyun_durumu['aktif_takim'] = 'B'
        socketio.emit('skor_guncellendi', oyun_durumu)
        socketio.emit('oyuncular_guncellendi', oyuncular)

@socketio.on('hoca_baglandi')
def hoca_verilerini_gonder():
    kelimeleri_hocaya_yolla()
    socketio.emit('oyuncular_guncellendi', oyuncular)

@socketio.on('tahta_baglandi')
def tahta_baglanti():
    socketio.emit('oyuncular_guncellendi', oyuncular)
    socketio.emit('skor_guncellendi', oyun_durumu)

@socketio.on('yeni_kelime_ekle')
def veritabanina_ekle(data):
    artikel = data['artikel'].strip()
    kelime = data['kelime'].strip().upper()
    if artikel != "-": tam_kelime = f"{artikel} {kelime}"
    else: tam_kelime = kelime
    yasaklilar = data['yasaklilar']
    baglanti = sqlite3.connect("kelimeler.db")
    imlec = baglanti.cursor()
    imlec.execute("INSERT INTO kelimeler (seviye, kelime, yasakli_1, yasakli_2, yasakli_3, yasakli_4) VALUES (?, ?, ?, ?, ?, ?)", (data['seviye'], tam_kelime, yasaklilar[0], yasaklilar[1], yasaklilar[2], yasaklilar[3]))
    baglanti.commit()
    baglanti.close()
    kelimeleri_hocaya_yolla()

@socketio.on('hocadan_kelime_gonder')
def manuel_kelime_yolla(data):
    aktif_takim_anahtari = 'takim_a' if oyun_durumu['aktif_takim'] == 'A' else 'takim_b'
    aktif_oyuncu = "Bilinmiyor"
    if len(oyuncular[aktif_takim_anahtari]) > 0:
        aktif_oyuncu = oyuncular[aktif_takim_anahtari][0]
    socketio.emit('yeni_kelime_geldi', {'kelime_verisi': data, 'anlatici': aktif_oyuncu})

@socketio.on('sureyi_baslat')
def sure_baslat(): 
    socketio.emit('sayac_basladi', {'sure': 90})

@socketio.on('sureyi_beklet')
def sureyi_beklet(): 
    socketio.emit('sayac_beklemede')

@socketio.on('sureyi_devam_ettir')
def sureyi_devam_ettir(data): 
    # SENKRONİZASYON ÇÖZÜMÜ: Devam et denildiğinde sanki baştan başlıyormuş gibi sinyal yolla
    socketio.emit('sayac_basladi', data)

@socketio.on('dogru_bildi')
def dogru_islem():
    aktif = oyun_durumu['aktif_takim']
    aktif_anahtar = 'takim_a' if aktif == 'A' else 'takim_b'
    rakip = 'B' if aktif == 'A' else 'A'

    if aktif == 'A': oyun_durumu['takim_a_skor'] += 1
    else: oyun_durumu['takim_b_skor'] += 1

    anlatici = oyuncular[aktif_anahtar][0] if len(oyuncular[aktif_anahtar]) > 0 else "Bilinmiyor"

    if len(oyuncular[aktif_anahtar]) > 1:
        kisi = oyuncular[aktif_anahtar].pop(0)
        oyuncular[aktif_anahtar].append(kisi)

    oyun_durumu['aktif_takim'] = rakip
    socketio.emit('skor_guncellendi', oyun_durumu)
    socketio.emit('oyuncular_guncellendi', oyuncular)
    socketio.emit('sayac_durdu')
    socketio.emit('dogru_bildi_animasyonu', {'anlatici': anlatici})

@socketio.on('tabuu_yapti')
def tabuu_islem():
    aktif = oyun_durumu['aktif_takim']
    aktif_anahtar = 'takim_a' if aktif == 'A' else 'takim_b'
    rakip = 'B' if aktif == 'A' else 'A'

    if aktif == 'A': oyun_durumu['takim_b_skor'] += 1
    else: oyun_durumu['takim_a_skor'] += 1

    anlatici = oyuncular[aktif_anahtar][0] if len(oyuncular[aktif_anahtar]) > 0 else "Bilinmiyor"

    if len(oyuncular[aktif_anahtar]) > 1:
        kisi = oyuncular[aktif_anahtar].pop(0)
        oyuncular[aktif_anahtar].append(kisi)

    oyun_durumu['aktif_takim'] = rakip
    socketio.emit('skor_guncellendi', oyun_durumu)
    socketio.emit('oyuncular_guncellendi', oyuncular)
    socketio.emit('sayac_durdu')
    socketio.emit('tabuu_animasyonu', {'anlatici': anlatici})

@socketio.on('takim_degistir')
def takim_degis(data):
    oyun_durumu['aktif_takim'] = data['yeni_takim']
    socketio.emit('skor_guncellendi', oyun_durumu)

if __name__ == '__main__':
    socketio.run(app, debug=True)