"""Mesin kecerdasan buatan (tanpa GUI): pembaruan Bayes + asisten ARIA.

Dipisahkan dari antarmuka supaya bisa diuji mandiri (lihat test_bayes.py).
"""
import csv
import math
import os
from dataclasses import dataclass, field

from bayes_net import JaringanBayes, Node

TOLERANSI_SERI = 0.005

# Folder berisi dataset kasus dalam format CSV (satu file per tabel).
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
FILE_TABEL = {
    "Kasus": "Kasus.csv",
    "Tersangka": "Tersangka.csv",
    "Bukti": "Bukti.csv",
    "Lokasi": "Lokasi.csv",
    "Saksi_Dialog": "Saksi_Dialog.csv",
    "Parameter": "Parameter.csv",
}


# ------------------------------------------------------------ data model
@dataclass
class Tersangka:
    id: str
    nama: str
    peran: str
    info: str
    prior: float
    akses: str
    alibi: str
    warna: tuple


@dataclass
class Bukti:
    id: str
    nama: str
    lokasi: str
    objek: str
    x: int
    y: int
    sumber: str
    deskripsi: str
    keandalan: float
    likelihood: dict          # id tersangka -> P(E|H)
    relevan: bool
    petunjuk: str


@dataclass
class Lokasi:
    nama: str
    x: int
    y: int
    w: int
    h: int
    warna: tuple
    deskripsi: str


@dataclass
class Saksi:
    nama: str
    tid: str
    lokasi: str
    x: int
    y: int
    dialog1: str
    dialog2: str


@dataclass
class Kasus:
    meta: dict
    tersangka: list
    bukti: list
    lokasi: list
    saksi: list
    param: dict = field(default_factory=dict)

    def bukti_by_id(self, bid):
        return next(b for b in self.bukti if b.id == bid)

    def tersangka_by_id(self, tid):
        return next(t for t in self.tersangka if t.id == tid)


# ------------------------------------------------------------ pemuat CSV
def _konversi(sel):
    """Angka dibaca sebagai int/float; sisanya tetap teks."""
    for tipe in (int, float):
        try:
            return tipe(sel)
        except ValueError:
            pass
    return sel


def _rows(data_dir, tabel):
    """Baris data satu tabel (tanpa header), dibaca dari folder data/."""
    path = os.path.join(data_dir, FILE_TABEL[tabel])
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)  # lewati header
        return [[_konversi(c) for c in r] for r in reader if r and r[0].strip()]


def muat_kasus(data_dir=DATA_DIR):
    """Membaca seluruh dataset dari folder berisi file CSV."""
    for tabel in FILE_TABEL:
        path = os.path.join(data_dir, FILE_TABEL[tabel])
        if not os.path.exists(path):
            raise FileNotFoundError(f"Dataset tidak ditemukan: {path}")
    meta = {k: v for k, v in _rows(data_dir, "Kasus")}

    tersangka = [Tersangka(r[0], r[1], r[2], r[3], float(r[4]), r[5], r[6], (int(r[7]), int(r[8]), int(r[9])))
                 for r in _rows(data_dir, "Tersangka") if r[1]]
    ids = [t.id for t in tersangka]

    bukti = []
    for r in _rows(data_dir, "Bukti"):
        L = {ids[i]: float(r[9 + i]) for i in range(len(ids))}
        bukti.append(Bukti(r[0], r[1], r[2], r[3], int(r[4]), int(r[5]), r[6], r[7], float(r[8]),
                           L, str(r[12]).lower() == "ya", r[13]))

    lokasi = [Lokasi(r[0], int(r[1]), int(r[2]), int(r[3]), int(r[4]), (int(r[5]), int(r[6]), int(r[7])), r[8])
              for r in _rows(data_dir, "Lokasi")]
    saksi = [Saksi(r[0], r[1], r[2], int(r[3]), int(r[4]), r[5], r[6]) for r in _rows(data_dir, "Saksi_Dialog")]
    param = {r[0]: r[1] for r in _rows(data_dir, "Parameter")}
    kasus = Kasus(meta, tersangka, bukti, lokasi, saksi, param)
    validasi(kasus)
    return kasus


def validasi(kasus):
    total = sum(t.prior for t in kasus.tersangka)
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"Total prior harus 1, sekarang {total}")
    for b in kasus.bukti:
        if not 0 <= b.keandalan <= 1:
            raise ValueError(f"Keandalan {b.id} di luar 0..1")
        for h, v in b.likelihood.items():
            if not 0 <= v <= 1:
                raise ValueError(f"Likelihood {b.id}/{h} di luar 0..1")


# ------------------------------------------------------------ algoritma Bayes
def likelihood_efektif(bukti, tid):
    """P(E|H) yang disesuaikan keandalan: bukti kurang andal ditarik ke 0.5 (netral)."""
    r = bukti.keandalan
    return r * bukti.likelihood[tid] + (1.0 - r) * 0.5


def normalisasi(nilai, cadangan):
    """Membuat total = 1. Jika semua nol, pakai mekanisme cadangan (prior)."""
    total = sum(nilai.values())
    if total <= 0:
        return dict(cadangan)
    return {k: v / total for k, v in nilai.items()}


def bangun_jaringan(kasus, ditemukan):
    """Jaringan Bayes untuk kasus ini.

    Node:
      H            : pelaku (state = id tersangka), prior dari data.
      V_<bukti>    : bukti andal atau tidak (P(V=True) = keandalan r).
      E_<bukti>    : bukti yang ditemukan; induk H dan V.
                     Jika V=True -> P(E|H) dari data, jika V=False -> 0.5 (netral).
    Hanya bukti yang sudah ditemukan yang dimasukkan sebagai node E.
    Mengembalikan (jaringan, bukti_teramati).
    """
    tids = [t.id for t in kasus.tersangka]
    nodes = [Node("H", [], tids, {(): {t.id: t.prior for t in kasus.tersangka}})]
    teramati = {}
    for b in kasus.bukti:
        if b.id not in ditemukan:
            continue
        v, e = f"V_{b.id}", f"E_{b.id}"
        nodes.append(Node(v, [], [True, False], {(): {True: b.keandalan, False: 1.0 - b.keandalan}}))
        cpt = {}
        for tid in tids:
            p = b.likelihood[tid]
            cpt[(tid, True)] = {True: p, False: 1.0 - p}
            cpt[(tid, False)] = {True: 0.5, False: 0.5}
        nodes.append(Node(e, ["H", v], [True, False], cpt))
        teramati[e] = True
    return JaringanBayes(nodes), teramati


def hitung_posterior(kasus, ditemukan):
    """P(H | semua bukti yang ditemukan) dihitung dengan jaringan Bayes.
    Bukti yang belum ditemukan diabaikan (bukan bukti negatif)."""
    prior = {t.id: t.prior for t in kasus.tersangka}
    jaringan, teramati = bangun_jaringan(kasus, ditemukan)
    post = jaringan.posterior("H", teramati)
    return post if post else dict(prior)


def peringkat(prob):
    """Daftar (rank, id, prob). Selisih <= toleransi dianggap seri (rank sama)."""
    urut = sorted(prob.items(), key=lambda kv: -kv[1])
    hasil, rank = [], 0
    for i, (tid, p) in enumerate(urut):
        if i == 0 or abs(urut[i - 1][1] - p) > TOLERANSI_SERI:
            rank = i + 1
        hasil.append((rank, tid, p))
    return hasil


def entropi(prob):
    return -sum(p * math.log2(p) for p in prob.values() if p > 0)


# ------------------------------------------------------------ asisten ARIA
class Aria:
    """Asisten AI: menjelaskan perubahan peringkat dan menyarankan bukti berikutnya."""

    def __init__(self, kasus):
        self.k = kasus

    def _p_bukti_muncul(self, bukti, post):
        # P(E) = sum_H P(E|H) P(H)   (penyebut Teorema Bayes)
        return sum(likelihood_efektif(bukti, t.id) * post[t.id] for t in self.k.tersangka)

    def nilai_informasi(self, bukti, ditemukan):
        """Expected information gain: seberapa banyak bukti ini diperkirakan
        mengurangi ketidakpastian (entropi) peringkat tersangka."""
        post = hitung_posterior(self.k, ditemukan)
        h0 = entropi(post)
        pe = self._p_bukti_muncul(bukti, post)
        ph_e = normalisasi({t.id: likelihood_efektif(bukti, t.id) * post[t.id] for t in self.k.tersangka}, post)
        ph_ne = normalisasi({t.id: (1 - likelihood_efektif(bukti, t.id)) * post[t.id] for t in self.k.tersangka}, post)
        h_exp = pe * entropi(ph_e) + (1 - pe) * entropi(ph_ne)
        return max(0.0, h0 - h_exp)

    def saran_berikutnya(self, ditemukan):
        sisa = [b for b in self.k.bukti if b.id not in ditemukan]
        if not sisa:
            return None
        return max(sisa, key=lambda b: (self.nilai_informasi(b, ditemukan) * (0.5 + b.keandalan)))

    def jelaskan(self, bukti, sebelum, sesudah):
        """Penjelasan perubahan peringkat setelah satu bukti baru."""
        T = {t.id: t.nama for t in self.k.tersangka}
        naik = max(sesudah, key=lambda h: sesudah[h] - sebelum[h])
        turun = min(sesudah, key=lambda h: sesudah[h] - sebelum[h])
        dn, dt = sesudah[naik] - sebelum[naik], sesudah[turun] - sebelum[turun]
        if abs(dn) < 0.01 and abs(dt) < 0.01:
            return (f"Bukti '{bukti.nama}' hampir tidak mengubah apa pun. "
                    f"(Keandalan {bukti.keandalan:.0%}, tidak membedakan tersangka.)")
        andal = "sangat andal" if bukti.keandalan >= 0.8 else "cukup andal" if bukti.keandalan >= 0.6 else "kurang andal"
        return (f"Bukti ini {andal} ({bukti.keandalan:.0%}). {T[naik]} naik {sebelum[naik]:.0%} -> {sesudah[naik]:.0%}, "
                f"{T[turun]} turun {sebelum[turun]:.0%} -> {sesudah[turun]:.0%}. {bukti.petunjuk}")

    def status(self, ditemukan):
        post = hitung_posterior(self.k, ditemukan)
        rk = peringkat(post)
        T = {t.id: t.nama for t in self.k.tersangka}
        if not ditemukan:
            return "Belum ada bukti. Semua tersangka masih di probabilitas awal. Telusuri ruangan dulu."
        top = rk[0]
        if len(rk) > 1 and rk[1][0] == top[0]:
            return "Peringkat teratas masih seri. Kumpulkan bukti lain sebelum menyimpulkan."
        if top[2] >= 0.70 and len(ditemukan) >= 4:
            return f"Keyakinan pada {T[top[1]]} sudah tinggi ({top[2]:.0%}). Kamu bisa menyimpulkan (tekan K)."
        return f"Saat ini {T[top[1]]} paling mungkin ({top[2]:.0%}), tapi belum cukup yakin. Cari bukti lagi."
