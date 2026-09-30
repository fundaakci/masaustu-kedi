# 🐱 Masaüstü Kedi

Mac ekranında dolaşan, zıplayıp yere düşen, tıklayınca sevinen/kızan ve
miyavlayan sanal kedi. Sadece Python'un kendi standart kütüphanesi
(`tkinter`) ile yazıldı — ekstra paket kurmana gerek yok.

## Dosya yapısı

```
masaustu_kedi/
├── main.py     # Programı başlatan dosya
├── cat.py      # Kedinin tüm mantığı, fiziği ve çizimi
└── README.md   # Bu dosya
```

## Kurulum (VS Code, macOS)

1. **Klasörü oluştur ve VS Code'da aç**
   - Finder'da istediğin yere `masaustu_kedi` adında bir klasör oluştur
     (veya bu sohbetten indirdiğin klasörü kullan).
   - VS Code'u aç → `File > Open Folder...` → `masaustu_kedi` klasörünü seç.

2. **`main.py` ve `cat.py` dosyalarını klasöre koy**
   - Bu sohbette sana verdiğim iki dosyayı klasörün içine kaydet
     (isimleri birebir `main.py` ve `cat.py` olmalı, ikisi de aynı klasörde).

3. **Python'un ve tkinter'ın kurulu olduğunu doğrula**
   VS Code içinde `Terminal > New Terminal` ile terminal aç, şunu yaz:
   ```bash
   python3 -m tkinter
   ```
   Küçük bir test penceresi açılırsa tkinter kurulu demektir, pencereyi kapatabilirsin.

   **Eğer hata alırsan** (özellikle Homebrew Python kullanıyorsan tkinter
   çoğu zaman eksik gelir):
   ```bash
   brew install python-tk
   ``` 
   veya en garanti çözüm: [python.org](https://www.python.org/downloads/macos/)
   üzerinden resmi Python yükleyicisini indirip kurmak (tkinter'ı hazır getirir).

4. **VS Code'da doğru Python yorumlayıcısını seç**
   - `Cmd+Shift+P` → `Python: Select Interpreter` → sistemindeki Python 3'ü seç.

5. **Programı çalıştır**
   Terminalde:
   ```bash
   python3 main.py
   ```
   Ekranın alt kısmında küçük gri bir kedi belirip dolaşmaya başlayacak.

6. **Kapatmak için**
   - Kedinin üzerine **sağ tıkla** (programı kapatır), veya
   - VS Code terminalinde `Ctrl+C`.

## Kedi ne yapıyor?

| Davranış | Açıklama |
|---|---|
| **Yürüme** | Rastgele sağa/sola yürür, ekran kenarına gelince döner. |
| **Zıplama/Düşme** | Arada bir zıplar, yerçekimiyle geri düşer. |
| **Yere iniş tepkisi** | Düşüp yere değince şaşkın (`!`) ifade takınır ve "pop" sesi çıkar. |
| **Tek tıklama** | Mutlu olur (kalp + mutlu gözler), "miyav miyav" der. |
| **Hızlı art arda tıklama (3+)** | Kızar (öfkeli kaşlar), "hsss" sesi çıkarır. |

Sesler için ekstra dosya gerekmiyor: macOS'un yerleşik `say` komutu ve
sistem sesleri (`afplay`) kullanılıyor.

## Ayarları değiştirmek istersen

`cat.py` dosyasının en üstündeki **AYARLAR** bölümünden şunları değiştirebilirsin:

- `WALK_SPEED` → yürüme hızı
- `JUMP_SPEED` / `GRAVITY` → zıplama yüksekliği ve düşüş hızı
- `GROUND_OFFSET` → kedinin ekranın altından ne kadar yukarıda yürüyeceği
  (Dock'un üstüne binmesin diye varsayılan 60 piksel yukarıda tutuyoruz;
  Dock'un yerine/boyutuna göre bu sayıyı artırıp azaltabilirsin)
- `WINDOW_W`, `WINDOW_H` → kedinin boyutu

## Bilinen sınırlamalar

- Kedi, altındaki pencerelere **tıklamaları geçirmiyor** (click-through değil);
  yani kedi tam üzerine geldiği yerde bir tık ona gider. Bu basit tkinter
  penceresiyle tam click-through yapmak macOS'ta ekstra native (PyObjC/Cocoa)
  kod gerektirir — istersen bir sonraki adım olarak bunu da ekleyebiliriz.
- Şeffaflık `tkinter`'ın macOS'a özel `-transparent` özelliğini kullanıyor;
  bazı macOS/Tcl-Tk sürüm kombinasyonlarında pencere tam şeffaf değil,
  hafif gri bir kutu olarak görünebilir. Böyle olursa terminalde
  `python3 -c "import tkinter; print(tkinter.TkVersion)"` ile Tk sürümünü
  kontrol et; 8.6.10+ öneriyoruz (python.org yükleyicisi genelde güncel gelir).
