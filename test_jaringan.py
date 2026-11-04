"""Pengujian jaringan Bayes: inferensi eksak dan kesesuaian dengan rumus data kasus.
Jalankan: python -m unittest -v test_jaringan
"""
import itertools
import os
import random
import unittest

import bayes_engine as be
from bayes_net import JaringanBayes, Node

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


class TestJaringanUmum(unittest.TestCase):
    def test_hujan_sprinkler_kecil(self):
        # Contoh klasik: Hujan -> Basah <- Sprinkler, dihitung manual.
        hujan = Node("Hujan", [], [True, False], {(): {True: 0.2, False: 0.8}})
        sprinkler = Node("Sprinkler", [], [True, False], {(): {True: 0.5, False: 0.5}})
        basah = Node("Basah", ["Hujan", "Sprinkler"], [True, False], {
            (True, True): {True: 0.99, False: 0.01},
            (True, False): {True: 0.8, False: 0.2},
            (False, True): {True: 0.9, False: 0.1},
            (False, False): {True: 0.0, False: 1.0},
        })
        jn = JaringanBayes([hujan, sprinkler, basah])
        p = jn.posterior("Hujan", {"Basah": True})
        # P(H|B) = P(B|H)P(H)/P(B); P(B) = 0.2*0.9*... dihitung langsung:
        num = 0.2 * (0.5 * 0.99 + 0.5 * 0.8)
        den = num + 0.8 * (0.5 * 0.9 + 0.5 * 0.0)
        self.assertAlmostEqual(p[True], num / den, places=9)

    def test_bukti_nol_peluang_mengembalikan_none(self):
        a = Node("A", [], [True, False], {(): {True: 1.0, False: 0.0}})
        b = Node("B", ["A"], [True, False], {(True,): {True: 1.0, False: 0.0},
                                             (False,): {True: 0.0, False: 1.0}})
        jn = JaringanBayes([a, b])
        # P(B=False) = 0, jadi evidence ini mustahil
        self.assertIsNone(jn.posterior("A", {"B": False}))


class TestJaringanKasus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.k = be.muat_kasus(PATH)

    def rumus_naif(self, ditemukan):
        """Rumus lama: P(H) * prod L_efektif, lalu dinormalisasi."""
        prior = {t.id: t.prior for t in self.k.tersangka}
        skor = dict(prior)
        for b in self.k.bukti:
            if b.id in ditemukan:
                for tid in skor:
                    skor[tid] *= be.likelihood_efektif(b, tid)
        z = sum(skor.values())
        return {h: v / z for h, v in skor.items()} if z > 0 else prior

    def test_jaringan_sama_dengan_rumus_naif(self):
        ids = [b.id for b in self.k.bukti]
        rnd = random.Random(1)
        for _ in range(60):
            n = rnd.randint(0, len(ids))
            subset = set(rnd.sample(ids, n))
            jn = be.hitung_posterior(self.k, subset)
            naif = self.rumus_naif(subset)
            for h in naif:
                self.assertAlmostEqual(jn[h], naif[h], places=9, msg=f"{subset} {h}")

    def test_struktur_node(self):
        jn, teramati = be.bangun_jaringan(self.k, {"E1", "E5"})
        self.assertEqual(set(jn.nodes), {"H", "V_E1", "E_E1", "V_E5", "E_E5"})
        self.assertEqual(teramati, {"E_E1": True, "E_E5": True})
        self.assertEqual(jn.nodes["E_E1"].parents, ["H", "V_E1"])


if __name__ == "__main__":
    unittest.main()
