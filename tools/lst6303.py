#!/usr/bin/env python3
"""Листинг и покрытие для прошивок на HD6303X (MAC-14, MAC-12D).

Запуск:
    python3 -I tools/lst6303.py src/MAC-14.BIN docs/asm/MAC-14.notes  > docs/asm/MAC-14.lst
    python3 -I tools/lst6303.py src/MAC-14.BIN docs/asm/MAC-14.notes --cov
    python3 -I tools/lst6303.py src/MAC-14.BIN docs/asm/MAC-14.notes --todo   # непокрытые участки

Код находится обходом от векторов и от точек входа из файла разметки.
Комментарии и имена берутся только из файла разметки (.notes), формат описан
в docs/asm/NOTES_FORMAT.md.

Покрытие:
  участок   — линейный кусок кода от метки/перехода до следующего перехода;
              покрыт, если у него есть комментарий (на любой его строке или
              заголовок перед ним) и у каждого условного перехода в нём
              есть свой комментарий;
  ветка     — условный переход (Bcc, кроме BRA/BRN); покрыт, если на его
              строке есть комментарий;
  данные    — байты вне кода; покрыты, если входят в объявленную таблицу.
"""
import sys
from collections import defaultdict

# Служебные строки листинга на языке разметки: --lang=ru (по умолчанию), en, de.
LANG = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--lang=")), "ru")
T = {
    "ru": {"called": "вызов из", "table": "таблица $%04X, %d байт: %s",
           "title": "Листинг %s (HD6303X), база $%04X. Комментарии: %s"},
    "en": {"called": "called from", "table": "table $%04X, %d bytes: %s",
           "title": "Listing of %s (HD6303X), base $%04X. Comments: %s"},
    "de": {"called": "aufgerufen von", "table": "Tabelle $%04X, %d Bytes: %s",
           "title": "Listing %s (HD6303X), Basis $%04X. Kommentare: %s"},
}[LANG]

INH, IMM8, IMM16, DIR, IDX, EXT, REL, IMDIR, IMIDX = range(9)
SIZE = {INH: 1, IMM8: 2, IMM16: 3, DIR: 2, IDX: 2, EXT: 3, REL: 2, IMDIR: 3, IMIDX: 3}

OPS = {}
for op, n in {0x01: "NOP", 0x04: "LSRD", 0x05: "ASLD", 0x06: "TAP", 0x07: "TPA", 0x08: "INX",
              0x09: "DEX", 0x0A: "CLV", 0x0B: "SEV", 0x0C: "CLC", 0x0D: "SEC", 0x0E: "CLI",
              0x0F: "SEI", 0x10: "SBA", 0x11: "CBA", 0x16: "TAB", 0x17: "TBA", 0x18: "XGDX",
              0x19: "DAA", 0x1A: "SLP", 0x1B: "ABA", 0x30: "TSX", 0x31: "INS", 0x32: "PULA",
              0x33: "PULB", 0x34: "DES", 0x35: "TXS", 0x36: "PSHA", 0x37: "PSHB", 0x38: "PULX",
              0x39: "RTS", 0x3A: "ABX", 0x3B: "RTI", 0x3C: "PSHX", 0x3D: "MUL", 0x3E: "WAI",
              0x3F: "SWI"}.items():
    OPS[op] = (n, INH)
for i, n in enumerate("BRA BRN BHI BLS BCC BCS BNE BEQ BVC BVS BPL BMI BGE BLT BGT BLE".split()):
    OPS[0x20 + i] = (n, REL)
RMW = {0: "NEG", 3: "COM", 4: "LSR", 6: "ROR", 7: "ASR", 8: "ASL", 9: "ROL", 0xA: "DEC",
       0xC: "INC", 0xD: "TST", 0xF: "CLR"}
for lo, n in RMW.items():
    OPS[0x40 | lo] = (n + "A", INH)
    OPS[0x50 | lo] = (n + "B", INH)
    OPS[0x60 | lo] = (n, IDX)
    OPS[0x70 | lo] = (n, EXT)
OPS[0x6E] = ("JMP", IDX)
OPS[0x7E] = ("JMP", EXT)
for lo, n in {1: "AIM", 2: "OIM", 5: "EIM", 0xB: "TIM"}.items():
    OPS[0x60 | lo] = (n, IMIDX)
    OPS[0x70 | lo] = (n, IMDIR)
A = "SUBA CMPA SBCA SUBD ANDA BITA LDAA STAA EORA ADCA ORAA ADDA CPX JSR LDS STS".split()
B = "SUBB CMPB SBCB ADDD ANDB BITB LDAB STAB EORB ADCB ORAB ADDB LDD STD LDX STX".split()
for base, names in ((0x80, A), (0xC0, B)):
    for lo, n in enumerate(names):
        for hi, mode in ((0, IMM8), (0x10, DIR), (0x20, IDX), (0x30, EXT)):
            if hi == 0 and lo in (7, 0xD, 0xF):
                continue
            if hi == 0:
                mode = IMM16 if lo in (3, 0xC, 0xE) else IMM8
            OPS[base + hi + lo] = (n, mode)
OPS[0x8D] = ("BSR", REL)
OPS[0xCC] = ("LDD", IMM16)

# Встроенные регистры HD6303X. Имена по документации Hitachi на HD6301X/HD6303X.
REGS = {0x01: "P2DDR", 0x03: "PORT2", 0x08: "TCSR1", 0x09: "FRCH", 0x0A: "FRCL",
        0x0B: "OCR1H", 0x0C: "OCR1L", 0x0D: "ICRH", 0x0E: "ICRL", 0x0F: "TCSR2",
        0x10: "RMCR", 0x11: "TRCSR1", 0x12: "RDR", 0x13: "TDR", 0x14: "RP5CR",
        0x15: "PORT5", 0x16: "P6DDR", 0x17: "PORT6", 0x18: "PORT7", 0x19: "OCR2H",
        0x1A: "OCR2L", 0x1B: "TCSR3", 0x1C: "TCONR", 0x1D: "T2CNT", 0x1E: "TRCSR2"}
VEC = ["IRQ2", "CMI", "TRAP", "SCI", "TOF", "OCF", "ICF", "IRQ1", "SWI", "NMI", "RES"]
COND = {"BHI", "BLS", "BCC", "BCS", "BNE", "BEQ", "BVC", "BVS", "BPL", "BMI", "BGE",
        "BLT", "BGT", "BLE"}


# ---------------------------------------------------------------- разметка
class Notes:
    def __init__(self, path):
        self.label, self.cmt, self.head = {}, {}, {}
        self.entry, self.noret, self.ptrtab, self.table = [], set(), [], {}
        self.legend, self.var = [], {}
        cur = None
        for no, raw in enumerate(open(path, encoding="utf-8"), 1):
            ln = raw.rstrip("\n")
            if ln.startswith("|"):
                if cur is None:
                    sys.exit("%s:%d: строка '|' без заголовка" % (path, no))
                cur.append(ln[2:].rstrip() if ln[1:2] == " " else ln[1:].rstrip())
                continue
            cur = None
            s = ln.strip()
            if not s or s.startswith("#"):
                continue
            w = s.split(None, 1)
            k, rest = w[0], (w[1] if len(w) > 1 else "")
            try:
                if k == "legend":
                    cur = self.legend
                elif k == "head":
                    a = int(rest.split()[0], 16)
                    cur = self.head.setdefault(a, [])
                elif k == "label":
                    a, name = rest.split(None, 1)
                    self.label[int(a, 16)] = name.strip()
                elif k == "entry":
                    self.entry += [int(x, 16) for x in rest.split()]
                elif k == "noret":
                    self.noret |= {int(x, 16) for x in rest.split()}
                elif k == "ptrtab":
                    a, n = rest.split()[:2]
                    self.ptrtab.append((int(a, 16), int(n)))
                elif k == "table":
                    a, n, text = rest.split(None, 2)
                    self.table[int(a, 16)] = (int(n), text)
                elif k == "var":
                    a, text = rest.split(None, 1)
                    self.var[int(a, 16)] = text
                elif len(k) == 4 and all(c in "0123456789ABCDEFabcdef" for c in k):
                    self.cmt[int(k, 16)] = rest
                else:
                    raise ValueError(k)
            except ValueError as e:
                sys.exit("%s:%d: не понял строку (%s): %s" % (path, no, e, ln))


# ---------------------------------------------------------------- разбор
class Rom:
    def __init__(self, path, notes):
        self.b = open(path, "rb").read()
        self.base = 0x10000 - len(self.b)
        self.n = notes
        self.insn, self.code = {}, set()
        self.xref = defaultdict(set)          # цель -> откуда
        self.subs, self.bad, self.indirect = set(), [], []
        self.vec = {}
        self.walk()

    def inrom(self, a):
        return self.base <= a < 0x10000

    def rd(self, a):
        return self.b[a - self.base]

    def rw(self, a):
        return (self.rd(a) << 8) | self.rd(a + 1)

    def walk(self):
        work = []
        for i, name in enumerate(VEC):
            t = self.rw(0xFFEA + 2 * i)
            self.vec[name] = t
            if self.inrom(t):
                work.append(t)
                self.subs.add(t)
        for a, cnt in self.n.ptrtab:
            for i in range(cnt):
                t = self.rw(a + 2 * i)
                work.append(t)
                self.subs.add(t)
                self.xref[t].add(a + 2 * i)
        for t in self.n.entry:
            work.append(t)
            self.subs.add(t)
        while work:
            pc = work.pop()
            while self.inrom(pc) and pc not in self.insn:
                if pc in self.code:
                    self.bad.append((pc, "переход в середину команды"))
                    break
                op = self.rd(pc)
                if op not in OPS:
                    self.bad.append((pc, "неизвестный код $%02X" % op))
                    break
                n, m = OPS[op]
                sz = SIZE[m]
                if not self.inrom(pc + sz - 1):
                    break
                arg = None
                if m in (IMM8, DIR, IDX):
                    arg = self.rd(pc + 1)
                elif m in (IMM16, EXT):
                    arg = self.rw(pc + 1)
                elif m == REL:
                    arg = (pc + 2 + ((self.rd(pc + 1) ^ 0x80) - 0x80)) & 0xFFFF
                elif m in (IMDIR, IMIDX):
                    arg = (self.rd(pc + 1), self.rd(pc + 2))
                self.insn[pc] = (n, m, arg, sz)
                self.code.update(range(pc, pc + sz))
                if n in ("JSR", "BSR") and m in (EXT, REL):
                    self.subs.add(arg)
                    self.xref[arg].add(pc)
                    work.append(arg)
                    if arg in self.n.noret:
                        break
                elif n == "JMP" and m == EXT:
                    self.xref[arg].add(pc)
                    work.append(arg)
                    break
                elif m == REL:
                    self.xref[arg].add(pc)
                    work.append(arg)
                    if n == "BRA":
                        break
                elif n in ("RTS", "RTI"):
                    break
                elif m == IDX and n in ("JMP", "JSR"):
                    self.indirect.append(pc)
                    if n == "JMP":
                        break
                pc += sz

    # участки: начало = точка входа, цель перехода, команда после перехода
    def blocks(self):
        starts = set(self.subs) | set(self.xref) | set(self.n.label) | set(self.n.head)
        for a, (n, m, arg, sz) in self.insn.items():
            if m == REL or n in ("JMP", "RTS", "RTI"):
                starts.add(a + sz)
        starts = sorted(s for s in starts if s in self.insn)
        res = []
        for s in starts:
            a, body = s, []
            while a in self.insn:
                body.append(a)
                n, m, arg, sz = self.insn[a]
                a += sz
                if m == REL or n in ("JMP", "RTS", "RTI") or a in starts:
                    break
            res.append(body)
        return res

    def roots(self):
        """Для каждой подпрограммы: из каких корней (векторы, задачи) она достижима."""
        roots = [(n, a) for n, a in self.vec.items() if self.inrom(a)]
        for a, cnt in self.n.ptrtab:
            for i in range(cnt):
                t = self.rw(a + 2 * i)
                roots.append((self.n.label.get(t, "%04X" % t), t))
        res = defaultdict(set)
        for rn, ra in roots:
            seen, work = set(), [ra]
            while work:
                pc = work.pop()
                while pc in self.insn and pc not in seen:
                    seen.add(pc)
                    n, m, arg, sz = self.insn[pc]
                    if m == REL or (n in ("JMP", "JSR", "BSR") and m in (EXT, REL)):
                        work.append(arg)
                    if n in ("RTS", "RTI", "BRA", "JMP"):
                        break
                    pc += sz
            for a in self.subs:
                if a in seen:
                    res[a].add(rn)
        return res

    def name(self, a):
        if a in self.n.label:
            return self.n.label[a]
        if a in self.subs:
            return "sub_%04X" % a
        if a in self.xref:
            return "loc_%04X" % a
        return None

    def opnd(self, n, m, arg):
        def adr(x):
            return self.name(x) or REGS.get(x) or ("$%04X" % x)
        if m == INH:
            return n
        if m == IMM8:
            return "%-5s #$%02X" % (n, arg)
        if m == IMM16:
            return "%-5s #$%04X" % (n, arg)
        if m == DIR:
            return "%-5s %s" % (n, REGS.get(arg, "$%02X" % arg))
        if m == IDX:
            return "%-5s $%02X,X" % (n, arg)
        if m in (EXT, REL):
            return "%-5s %s" % (n, adr(arg))
        if m == IMDIR:
            return "%-5s #$%02X,%s" % (n, arg[0], REGS.get(arg[1], "$%02X" % arg[1]))
        return "%-5s #$%02X,$%02X,X" % (n, arg[0], arg[1])


# ---------------------------------------------------------------- вывод
def listing(r, title):
    n = r.n
    out = [";" + "=" * 78, "; " + title, ";" + "=" * 78]
    if n.legend:
        out += ["; " + x if x else ";" for x in n.legend]
        out.append(";" + "-" * 78)
    tabend = 0
    rts = r.roots()
    a = r.base
    while a < 0x10000:
        if a in n.head:
            out.append("")
            out.append(";" + "-" * 78)
            out += ["; " + x if x else ";" for x in n.head[a]]
            out.append(";" + "-" * 78)
        if a in r.insn:
            nm, m, arg, sz = r.insn[a]
            lab = r.name(a)
            if lab:
                if a not in n.head:
                    out.append("")
                if a in r.subs and a in rts:
                    out.append(lab + ":".ljust(40 - len(lab)) + "; " + T["called"] + ": " + ", ".join(sorted(rts[a])))
                else:
                    out.append(lab + ":")
            hx = " ".join("%02X" % r.rd(a + k) for k in range(sz))
            ln = "  %04X  %-9s  %s" % (a, hx, r.opnd(nm, m, arg))
            if a in n.cmt:
                ln = ln.ljust(40) + "; " + n.cmt[a]
            out.append(ln)
            a += sz
            continue
        if a in n.table:
            cnt, text = n.table[a]
            out.append("")
            out.append("; " + T["table"] % (a, cnt, text))
            tabend = a + cnt
        s = a
        a += 1
        while a < 0x10000 and a not in r.insn and a not in n.table and a not in n.head \
                and a - s < 16 and (a != tabend):
            a += 1
        ln = "  %04X  db %s" % (s, " ".join("%02X" % r.rd(k) for k in range(s, a)))
        if s in n.cmt:
            ln = ln.ljust(40) + "; " + n.cmt[s]
        out.append(ln)
    return "\n".join(out)


def coverage(r):
    n = r.n
    blocks = r.blocks()
    ok_b, todo = 0, []
    br_all = br_ok = 0
    for body in blocks:
        has = any(a in n.cmt for a in body) or body[0] in n.head
        good = has
        for a in body:
            if r.insn[a][0] in COND:
                br_all += 1
                if a in n.cmt:
                    br_ok += 1
                else:
                    good = False
        if good:
            ok_b += 1
        else:
            todo.append(body[0])
    tab = set()
    for a, (cnt, _) in n.table.items():
        tab.update(range(a, a + cnt))
    data = [a for a in range(r.base, 0x10000) if a not in r.code]
    data_ok = sum(1 for a in data if a in tab)
    return dict(blocks=len(blocks), blocks_ok=ok_b, br=br_all, br_ok=br_ok,
                code=len(r.code), data=len(data), data_ok=data_ok, todo=todo)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    rom, notes = sys.argv[1], sys.argv[2]
    r = Rom(rom, Notes(notes))
    mode = next((a for a in sys.argv[3:] if not a.startswith("--lang=")), "")
    if mode in ("--cov", "--todo"):
        c = coverage(r)
        pct = lambda x, y: 100.0 * x / y if y else 0.0
        print("ROM %s, база $%04X, %d байт" % (rom, r.base, len(r.b)))
        print("код: %d байт, данные: %d байт (в таблицах %d = %.1f %%)" % (
            c["code"], c["data"], c["data_ok"], pct(c["data_ok"], c["data"])))
        print("участки: %d из %d = %.1f %%" % (c["blocks_ok"], c["blocks"], pct(c["blocks_ok"], c["blocks"])))
        print("ветки:   %d из %d = %.1f %%" % (c["br_ok"], c["br"], pct(c["br_ok"], c["br"])))
        print("косвенные переходы: " + (" ".join("%04X" % x for x in r.indirect) or "нет"))
        tabs = set()
        for ta, (cnt, _) in r.n.table.items():
            tabs.update(range(ta, ta + cnt))
        lost = [a for a in sorted(r.n.cmt) if a not in r.insn and a not in tabs]
        for a in lost:
            print("КОММЕНТАРИЙ НЕ НА КОМАНДЕ %04X: %s" % (a, r.n.cmt[a]))
        for a in sorted(r.n.head):
            if a not in r.insn and a not in r.n.table:
                print("ЗАГОЛОВОК НЕ НА КОМАНДЕ %04X" % a)
        for a, why in r.bad:
            print("ОШИБКА РАЗБОРА %04X: %s" % (a, why))
        if mode == "--todo":
            print("непокрытые участки:")
            for a in c["todo"]:
                print("  %04X" % a)
        return
    title = T["title"] % (rom, r.base, notes)
    print(listing(r, title))


if __name__ == "__main__":
    main()
