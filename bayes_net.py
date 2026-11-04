"""Jaringan Bayes (Bayesian network) sederhana dengan inferensi eksak.

Setiap node punya daftar state dan CPT: untuk setiap kombinasi nilai induk,
distribusi peluang atas state node tersebut. Inferensi dilakukan dengan
enumerasi semua variabel tersembunyi (exact inference).
"""
import itertools


class Node:
    def __init__(self, nama, parents, states, cpt):
        """cpt: dict dari tuple nilai induk -> {state: peluang}."""
        self.nama = nama
        self.parents = list(parents)
        self.states = list(states)
        self.cpt = cpt


class JaringanBayes:
    def __init__(self, nodes):
        """nodes harus sudah terurut topologis (induk sebelum anak)."""
        self.urutan = list(nodes)
        self.nodes = {n.nama: n for n in self.urutan}

    def peluang(self, node, nilai, assign):
        """P(node = nilai | induk sesuai assign)."""
        induk = tuple(assign[p] for p in node.parents)
        return node.cpt[induk][nilai]

    def gabungan(self, assign):
        """P(semua variabel = nilai pada assign) memakai aturan rantai jaringan."""
        hasil = 1.0
        for node in self.urutan:
            hasil *= self.peluang(node, assign[node.nama], assign)
        return hasil

    def posterior(self, query, bukti):
        """P(query | bukti). bukti: dict nama_node -> nilai yang diamati.
        Mengembalikan dict {state: peluang}, atau None jika P(bukti) = 0."""
        tersembunyi = [n.nama for n in self.urutan if n.nama != query and n.nama not in bukti]
        skor = {}
        for s in self.nodes[query].states:
            total = 0.0
            for nilai in itertools.product(*(self.nodes[h].states for h in tersembunyi)):
                assign = dict(bukti)
                assign[query] = s
                assign.update(zip(tersembunyi, nilai))
                total += self.gabungan(assign)
            skor[s] = total
        z = sum(skor.values())
        if z <= 0:
            return None
        return {s: v / z for s, v in skor.items()}
