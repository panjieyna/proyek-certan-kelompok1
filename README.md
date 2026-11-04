# CASE UNKNOWN: The Last Clue

Game detektif 2D (Python + Pygame) berdasarkan laporan progres Kelompok 1 (IT Del, Kecerdasan Buatan).

## Menjalankan
    pip install -r requirements.txt
    python game.py              # jalankan game
    python -m unittest -v       # uji algoritma Bayes (skenario uji laporan bagian VII)
    python buat_dataset.py      # (opsional) buat dataset_kasus.xlsx dari folder data/ untuk dibuka di Excel

## Kontrol
WASD / panah = gerak | E = periksa objek / bicara | H = petunjuk ARIA | G = ARIA menemani jalan |
J = Evidence Journal | K = buat kesimpulan | R = replay (di layar hasil)

Tombol menu, aksi, pilihan bukti, dan pilihan tersangka juga dapat diklik dengan mouse.
Scroll mouse pada panel ARIA atau detail jurnal untuk membaca teks panjang; PgUp / PgDn juga tersedia.
Di layar kesimpulan, tekan 1–3 untuk memilih tersangka, panah atas/bawah untuk menyorot bukti,
Spasi untuk mencentang bukti, dan Enter untuk mengirim kesimpulan. Esc untuk kembali.

## Tampilan dan font
UI memakai tema investigasi gelap dengan aksen emas dan cyan, papan kasus pada menu utama,
panel probabilitas, jurnal bukti, dan laporan akhir. Jendela dapat diubah ukurannya dengan
kanvas logis 1280 × 800; Pygame menyesuaikan skala tampilannya.

Font **Rajdhani SemiBold** digunakan untuk judul, sedangkan **Barlow Regular / SemiBold** untuk
teks dan kontrol. File font disertakan di `assets/fonts/` sehingga tidak membutuhkan internet
saat bermain. Keduanya berlisensi SIL Open Font License; salinan lisensi ada di folder yang sama.
Warna, font, dan tata letak antarmuka dapat disesuaikan melalui `ui.py`.

Pratinjau: [menu utama](artifacts/ui-preview/menu.png),
[investigasi](artifacts/ui-preview/investigation.png), dan [jurnal](artifacts/ui-preview/journal.png).

## File
- data/Kasus.csv, Tersangka.csv, Bukti.csv, Lokasi.csv, Saksi_Dialog.csv, Skenario_Uji.csv, Parameter.csv : dataset kasus (dibaca langsung oleh game)
- bayes_net.py       : jaringan Bayes (node, CPT, inferensi eksak dengan enumerasi)
- bayes_engine.py    : membangun jaringan Bayes untuk kasus + asisten AI ARIA + pemuat CSV (tanpa GUI, bisa diuji mandiri)
- game.py            : antarmuka Pygame, karakter bergerak, peta, jurnal, skor
- ui.py              : tema visual, font, layar UI, tombol mouse, dan scroll
- assets/fonts/      : font lokal beserta lisensi
- test_bayes.py      : unittest
- test_ui.py         : uji UI tanpa jendela (navigasi, dialog, scroll, kesimpulan)
- buat_dataset.py    : opsional, membuat dataset_kasus.xlsx dari folder data/ (tidak dibutuhkan game)

Ubah angka di file CSV dalam folder data/ (mis. keandalan atau P(E|H)) dan game langsung memakainya.
