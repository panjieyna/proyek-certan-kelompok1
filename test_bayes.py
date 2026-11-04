"""Pengujian sesuai skenario uji laporan (bagian VII). Jalankan: python -m unittest -v"""
import os
import unittest

import bayes_engine as be

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


class TestBayes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.k = be.muat_kasus(PATH)

    def test_T1_prior_awal(self):
        p = be.hitung_posterior(self.k, set())
        self.assertAlmostEqual(p["S1"], 0.35)
        self.assertAlmostEqual(p["S2"], 0.30)
        self.assertAlmostEqual(p["S3"], 0.35)

    def test_T2_bukti_memperbarui(self):
        p = be.hitung_posterior(self.k, {"E1"})
        self.assertGreater(p["S2"], 0.30)
        self.assertAlmostEqual(sum(p.values()), 1.0)

    def test_T3_bukti_belum_ada_bukan_negatif(self):
        a = be.hitung_posterior(self.k, {"E1"})
        b = be.hitung_posterior(self.k, {"E1"} | set())
        self.assertEqual(a, b)

    def test_T4_peringkat_seri(self):
        rk = be.peringkat(be.hitung_posterior(self.k, set()))
        self.assertEqual(rk[0][0], rk[1][0])  # Arman & Clara sama-sama 0.35

    def test_T5_semua_nol_fallback(self):
        prior = {"S1": 0.5, "S2": 0.5}
        self.assertEqual(be.normalisasi({"S1": 0, "S2": 0}, prior), prior)

    def test_normalisasi_selalu_satu(self):
        ids = [b.id for b in self.k.bukti]
        for n in range(len(ids) + 1):
            p = be.hitung_posterior(self.k, set(ids[:n]))
            self.assertAlmostEqual(sum(p.values()), 1.0, places=9)

    def test_semua_bukti_menunjuk_pelaku(self):
        p = be.hitung_posterior(self.k, {b.id for b in self.k.bukti})
        self.assertEqual(max(p, key=p.get), "S2")
        self.assertGreater(p["S2"], 0.8)

    def test_keandalan_rendah_menetralkan(self):
        b = self.k.bukti_by_id("E3")
        b2 = be.Bukti(**{**b.__dict__, "keandalan": 0.0})
        for t in self.k.tersangka:
            self.assertAlmostEqual(be.likelihood_efektif(b2, t.id), 0.5)

    def test_aria_saran_dan_penjelasan(self):
        aria = be.Aria(self.k)
        s = aria.saran_berikutnya(set())
        self.assertIsNotNone(s)
        self.assertGreater(aria.nilai_informasi(s, set()), 0)
        self.assertIsNone(aria.saran_berikutnya({b.id for b in self.k.bukti}))
        sebelum = be.hitung_posterior(self.k, set())
        sesudah = be.hitung_posterior(self.k, {"E1"})
        self.assertIn("Bima", aria.jelaskan(s, sebelum, sesudah))

    def test_dataset_valid(self):
        self.assertEqual(len(self.k.tersangka), 3)
        self.assertTrue(6 <= len(self.k.bukti) <= 10)


if __name__ == "__main__":
    unittest.main()
