import sqlite3

# Veritabanına bağlan (yoksa otomatik oluşturur)
baglanti = sqlite3.connect("kelimeler.db")
imlec = baglanti.cursor()

# Kelimeler tablosunu oluştur
imlec.execute("""
CREATE TABLE IF NOT EXISTS kelimeler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seviye TEXT,
    kelime TEXT,
    yasakli_1 TEXT,
    yasakli_2 TEXT,
    yasakli_3 TEXT,
    yasakli_4 TEXT
)
""")

# A1/A2 seviyesinden birkaç örnek Almanca kelime ekleyelim
ornek_kelimeler = [
    ("A1", "DER APFEL", "Obst", "Rot", "Essen", "Baum"),
    ("A1", "DAS AUTO", "Fahren", "Straße", "BMW", "Reifen"),
    ("A2", "DER URLAUB", "Reisen", "Sommer", "Meer", "Flugzeug"),
    ("A1", "DER HUND", "Tier", "Katze", "Bellen", "Spielen")
]

imlec.executemany("""
INSERT INTO kelimeler (seviye, kelime, yasakli_1, yasakli_2, yasakli_3, yasakli_4) 
VALUES (?, ?, ?, ?, ?, ?)
""", ornek_kelimeler)

baglanti.commit()
baglanti.close()

print("Veritabanı kuruldu ve örnek kelimeler eklendi!")