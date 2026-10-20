"""Minimal NBT reader/writer.

Java structure files are gzip'd big-endian NBT; Bedrock .mcstructure files are
uncompressed little-endian NBT.  Values are decoded into plain Python types;
writing needs explicit tags, built with the Tag helpers below.
"""
import gzip
import io
import struct

END, BYTE, SHORT, INT, LONG, FLOAT, DOUBLE, BYTE_ARRAY, STRING, LIST, COMPOUND, INT_ARRAY, LONG_ARRAY = range(13)


class Reader:
    def __init__(self, data, little=False):
        self.f = io.BytesIO(data)
        self.e = "<" if little else ">"

    def _u(self, fmt, n):
        return struct.unpack(self.e + fmt, self.f.read(n))[0]

    def string(self):
        n = self._u("H", 2)
        return self.f.read(n).decode("utf-8", "replace")

    def payload(self, t):
        if t == BYTE:
            return self._u("b", 1)
        if t == SHORT:
            return self._u("h", 2)
        if t == INT:
            return self._u("i", 4)
        if t == LONG:
            return self._u("q", 8)
        if t == FLOAT:
            return self._u("f", 4)
        if t == DOUBLE:
            return self._u("d", 8)
        if t == BYTE_ARRAY:
            n = self._u("i", 4)
            return list(self.f.read(n))
        if t == STRING:
            return self.string()
        if t == LIST:
            et = self._u("b", 1)
            n = self._u("i", 4)
            return [self.payload(et) for _ in range(n)]
        if t == COMPOUND:
            out = {}
            while True:
                tt = self._u("b", 1)
                if tt == END:
                    return out
                name = self.string()
                out[name] = self.payload(tt)
        if t == INT_ARRAY:
            n = self._u("i", 4)
            return [self._u("i", 4) for _ in range(n)]
        if t == LONG_ARRAY:
            n = self._u("i", 4)
            return [self._u("q", 8) for _ in range(n)]
        raise ValueError(f"bad tag {t}")

    def root(self):
        t = self._u("b", 1)
        self.string()
        return self.payload(t)


def read_java(data):
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    return Reader(data).root()


# ------------------------------------------------------------- writing

class Tag:
    def __init__(self, t, v, et=None):
        self.t, self.v, self.et = t, v, et


def Byte(v): return Tag(BYTE, v)
def Short(v): return Tag(SHORT, v)
def Int(v): return Tag(INT, v)
def Long(v): return Tag(LONG, v)
def Float(v): return Tag(FLOAT, v)
def String(v): return Tag(STRING, v)
def Compound(d): return Tag(COMPOUND, d)
def List(et, items): return Tag(LIST, items, et)


class Writer:
    def __init__(self, little=True):
        self.f = io.BytesIO()
        self.e = "<" if little else ">"

    def _p(self, fmt, v):
        self.f.write(struct.pack(self.e + fmt, v))

    def string(self, s):
        b = s.encode("utf-8")
        self._p("H", len(b))
        self.f.write(b)

    def payload(self, tag):
        t, v = tag.t, tag.v
        if t == BYTE:
            self._p("b", v)
        elif t == SHORT:
            self._p("h", v)
        elif t == INT:
            self._p("i", v)
        elif t == LONG:
            self._p("q", v)
        elif t == FLOAT:
            self._p("f", v)
        elif t == STRING:
            self.string(v)
        elif t == LIST:
            self._p("b", tag.et if v else (tag.et or END))
            self._p("i", len(v))
            for item in v:
                self.payload(item if isinstance(item, Tag) else Tag(tag.et, item))
        elif t == COMPOUND:
            for name, item in v.items():
                self._p("b", item.t)
                self.string(name)
                self.payload(item)
            self._p("b", END)
        else:
            raise ValueError(t)

    def root(self, tag):
        self._p("b", tag.t)
        self.string("")
        self.payload(tag)
        return self.f.getvalue()


def write_bedrock(tag):
    return Writer(little=True).root(tag)
