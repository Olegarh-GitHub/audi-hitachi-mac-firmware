#!/usr/bin/env python3
"""Сопоставление кода двух прошивок HD6303X по последовательностям команд.

Запуск: python3 -I tools/match6303.py ROM_A NOTES_A ROM_B NOTES_B [N]
Для каждой команды прошивки A ищется место в прошивке B, где совпадают
N подряд команд (мнемоника и режим адресации, без операндов;
прямая и расширенная адресации считаются одной). Берутся только
окна, которые встречаются в каждой прошивке ровно один раз. Выводятся
непрерывные совпавшие отрезки: A_начало-A_конец <-> B_начало, длина.
Это подсказка, где искать похожую логику, а не доказательство.
"""
import sys, importlib.util
from collections import defaultdict

spec = importlib.util.spec_from_file_location("l", __file__.rsplit("/", 1)[0] + "/lst6303.py")
l = importlib.util.module_from_spec(spec); spec.loader.exec_module(l)


def seq(r):
    addrs = sorted(r.insn)
    # прямая ($00xx) и расширенная адресация считаются одинаковыми:
    # у MAC-12D ОЗУ во внутренней странице, у MAC-14 — внешнее $8000
    norm = lambda m: l.EXT if m == l.DIR else (l.IMIDX if m == l.IMDIR else m)
    return addrs, [(r.insn[a][0], norm(r.insn[a][1])) for a in addrs]


def main():
    ra = l.Rom(sys.argv[1], l.Notes(sys.argv[2]))
    rb = l.Rom(sys.argv[3], l.Notes(sys.argv[4]))
    n = int(sys.argv[5]) if len(sys.argv) > 5 else 6
    aa, sa = seq(ra)
    ab, sb = seq(rb)

    def index(s):
        d = defaultdict(list)
        for i in range(len(s) - n + 1):
            d[tuple(s[i:i + n])].append(i)
        return d
    ia, ib = index(sa), index(sb)
    pair = {}
    for k, v in ia.items():
        if len(v) == 1 and len(ib.get(k, [])) == 1:
            pair[v[0]] = ib[k][0]
    runs, i = [], 0
    keys = sorted(pair)
    while i < len(keys):
        s0, t0 = keys[i], pair[keys[i]]
        j = i
        while j + 1 < len(keys) and keys[j + 1] == keys[j] + 1 and pair[keys[j + 1]] == pair[keys[j]] + 1:
            j += 1
        runs.append((s0, t0, keys[j] - s0 + n))
        i = j + 1
    for s0, t0, ln in runs:
        e = min(s0 + ln - 1, len(aa) - 1)
        nb = rb.name(ab[t0]) or ""
        print("%04X-%04X <-> %04X %-14s команд %d" % (aa[s0], aa[e], ab[t0], nb, ln))
    cov = sum(ln for _, _, ln in runs)
    print("совпало команд: %d из %d" % (cov, len(sa)), file=sys.stderr)




def varmap():
    """Соответствие ячеек: по совпавшим командам с операндом-адресом."""
    ra = l.Rom(sys.argv[2], l.Notes(sys.argv[3]))
    rb = l.Rom(sys.argv[4], l.Notes(sys.argv[5]))
    n = int(sys.argv[6]) if len(sys.argv) > 6 else 5
    aa, sa = seq(ra)
    ab, sb = seq(rb)
    d = defaultdict(list)
    for i in range(len(sa) - n + 1):
        d[tuple(sa[i:i + n])].append(i)
    e = defaultdict(list)
    for i in range(len(sb) - n + 1):
        e[tuple(sb[i:i + n])].append(i)
    cnt = defaultdict(lambda: defaultdict(int))
    for k, v in d.items():
        if len(v) == 1 and len(e.get(k, [])) == 1:
            for j in range(n):
                xa, xb = ra.insn[aa[v[0] + j]], rb.insn[ab[e[k][0] + j]]
                if xa[1] in (l.DIR, l.EXT) and xb[1] in (l.DIR, l.EXT):
                    cnt[xa[2]][xb[2]] += 1
                if xa[1] in (l.IMDIR,) and xb[1] in (l.IMDIR, l.IMIDX):
                    cnt[xa[2][1]][xb[2][1] + (0x8000 if xb[1] == l.IMIDX else 0)] += 1
    for a in sorted(cnt):
        best = sorted(cnt[a].items(), key=lambda kv: -kv[1])
        print("%04X -> %s" % (a, "  ".join("%04X×%d" % kv for kv in best[:3])))


if __name__ == "__main__" and sys.argv[1] == "--vars":
    varmap()


if __name__ == "__main__" and sys.argv[1] not in ("--vars", "--draft"):
    main()


def draft():
    """Черновик комментариев для A по совпавшим командам B (с пересчётом адресов).
    Выход — строки формата .notes с пометкой [B:адрес] для ручной проверки."""
    import re
    ra = l.Rom(sys.argv[2], l.Notes(sys.argv[3]))
    rb = l.Rom(sys.argv[4], l.Notes(sys.argv[5]))
    n = int(sys.argv[6]) if len(sys.argv) > 6 else 5
    aa, sa = seq(ra)
    ab, sb = seq(rb)
    d = defaultdict(list); e = defaultdict(list)
    for i in range(len(sa) - n + 1): d[tuple(sa[i:i + n])].append(i)
    for i in range(len(sb) - n + 1): e[tuple(sb[i:i + n])].append(i)
    pairs = {}
    amap = defaultdict(lambda: defaultdict(int))
    for k, v in d.items():
        if len(v) == 1 and len(e.get(k, [])) == 1:
            for j in range(n):
                pa, pb = aa[v[0] + j], ab[e[k][0] + j]
                pairs[pa] = pb
                xa, xb = ra.insn[pa], rb.insn[pb]
                if xa[1] in (l.DIR, l.EXT, l.IMM16) and xb[1] in (l.DIR, l.EXT, l.IMM16):
                    amap[xb[2]][xa[2]] += 1
    tr = {b: max(v.items(), key=lambda kv: kv[1])[0] for b, v in amap.items()}
    def conv(t):
        def rep(m):
            x = int(m.group(1), 16)
            return ("$%04X" % tr[x]) if x in tr else m.group(0) + "{?}"
        t = re.sub(r"\$([0-9A-F]{4})", rep, t)
        return re.sub(r"\b([C-F][0-9A-F]{3})\b", lambda m: ("%04X" % tr[int(m.group(1), 16)]) if int(m.group(1), 16) in tr else m.group(0) + "{?}", t)
    for pa in sorted(pairs):
        pb = pairs[pa]
        if pb in rb.n.cmt:
            xa, xb = ra.insn[pa], rb.insn[pb]
            # одинаковые непосредственные числа и смещения — «=», иначе «≠» (проверить)
            same = xa[1] not in (l.IMM8, l.IDX, l.IMDIR, l.IMIDX) or xa[2] == xb[2] or \
                (xa[1] in (l.IMDIR, l.IMIDX) and xa[2][0] == xb[2][0])
            print("%04X %s  [14:%04X%s]" % (pa, conv(rb.n.cmt[pb]), pb, "" if same else " ≠"))


if __name__ == "__main__" and sys.argv[1] == "--draft":
    draft()
