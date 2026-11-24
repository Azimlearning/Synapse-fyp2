"""FORMULAS: the small language the writer states a law in (build-script.md section 5, V5-D04).

A formula is compiled twice from one parse: to JavaScript for the page (`to_js`) and to a Python evaluator for the reference (`evaluate`). The browser check compares
the two across each control's range. This is what makes a formula more checkable than model code: Synapse, not the model, turns it into running code.

What this proves: the page computes what the formula says. It does not prove the formula is right; the second reader reads every formula and the label stays
`model-checked`.

The grammar is closed on purpose: numbers, names, `+ - * / ^`, unary minus, parentheses and a fixed list of functions and constants. No conditionals, no
definitions, no randomness, no time. A result that is not finite (division by zero, the log of a non-positive number, a square root of a negative number, an overflow)
is an error in both evaluators, at every step, so the two cannot disagree about whether a value exists.

Units (`[N/m]` after a formula, or a control's unit) are checked by DIMENSION where every named input carries a known unit: metres added to seconds, a force declared
as a length. Scale is not checked (cm against m, g against kg): a bare constant such as `/ 1000` or `* 9.81` is how a writer converts, and refusing it would cost a retry for
a formula that is right. An unknown unit, or a bare constant other than a small whole number or one half, makes the expression's unit unknown and the check stands
down for it; it never guesses. The second reader looks for scale slips.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from fractions import Fraction

# ── constants ────────────────────────────────────────────────────────────────────────────────────────────────────────────
# name: (value, unit). g_earth, c_light and avogadro are the values the KSSM textbooks use (api/pipeline/constants.py, PLAN-020). G is the SI value.
# ASSUMED (A-V5-2-4): G = 6.674e-11 is not in the PLAN-020 table (no Plan uses it); a teacher has not reviewed it.
CONSTANTS: dict[str, tuple[float, str]] = {
    "pi": (math.pi, ""),
    "g_earth": (9.81, "m/s^2"),
    "G": (6.674e-11, "m^3/kg/s^2"),
    "c_light": (3.0e8, "m/s"),
    "avogadro": (6.02e23, "1/mol"),
}
FUNCTIONS: dict[str, tuple[int, int | None]] = {
    # name: (minimum arguments, maximum arguments or None for any)
    "sqrt": (1, 1),
    "abs": (1, 1),
    "min": (2, None),
    "max": (2, None),
    "exp": (1, 1),
    "ln": (1, 1),
    "log10": (1, 1),
    "sin": (1, 1),
    "cos": (1, 1),
    "tan": (1, 1),
    "asin": (1, 1),
    "acos": (1, 1),
    "atan": (1, 1),
    "deg": (1, 1),
    "rad": (1, 1),
}
RESERVED = frozenset(CONSTANTS) | frozenset(FUNCTIONS)
MAX_LENGTH = 300
MAX_DEPTH = 40


class FormulaError(ValueError):
    """The formula is not in the grammar, or it has no value here. The message is in plain words and is sent back to the writer."""


# ── syntax tree ──────────────────────────────────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Num:
    value: float


@dataclass(frozen=True)
class Name:
    name: str


@dataclass(frozen=True)
class Neg:
    arg: Node


@dataclass(frozen=True)
class Bin:
    op: str
    left: Node
    right: Node


@dataclass(frozen=True)
class Call:
    fn: str
    args: tuple[Node, ...]


Node = Num | Name | Neg | Bin | Call

_TOKEN = re.compile(r"\s*(?:(?P<num>(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)|(?P<id>[A-Za-z_][A-Za-z0-9_]*)|(?P<op>[-+*/^(),]))")
_BANNED = {
    "if": "conditionals are not allowed in a formula",
    "else": "conditionals are not allowed in a formula",
    "time": "a formula cannot use time",
    "random": "a formula cannot use randomness",
    "rand": "a formula cannot use randomness",
    "eval": "eval is not allowed",
    "function": "a formula cannot define a function",
    "return": "a formula is one expression",
}


def _tokens(text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    pos = 0
    text = text.rstrip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m:
            bad = text[pos:].lstrip()[:1]
            raise FormulaError(f"the character '{bad}' is not allowed in a formula (use numbers, names, + - * / ^, parentheses and the listed functions)")
        kind = "num" if m.group("num") else "id" if m.group("id") else "op"
        out.append((kind, m.group(kind)))
        pos = m.end()
    return out


class _Parser:
    def __init__(self, text: str) -> None:
        if len(text) > MAX_LENGTH:
            raise FormulaError(f"a formula is at most {MAX_LENGTH} characters")
        self.toks = _tokens(text)
        self.i = 0
        self.depth = 0

    def peek(self) -> tuple[str, str] | None:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def take(self) -> tuple[str, str]:
        t = self.peek()
        if t is None:
            raise FormulaError("the formula ends too soon")
        self.i += 1
        return t

    def expect(self, op: str) -> None:
        t = self.take()
        if t != ("op", op):
            raise FormulaError(f"expected '{op}' but found '{t[1]}'")

    def parse(self) -> Node:
        if not self.toks:
            raise FormulaError("the formula is empty")
        node = self.expr()
        if self.peek() is not None:
            raise FormulaError(f"unexpected '{self.peek()[1]}' (write the multiplication sign: 2 * x, not 2 x)")  # type: ignore[index]
        return node

    def _enter(self) -> None:
        self.depth += 1
        if self.depth > MAX_DEPTH:
            raise FormulaError("the formula is nested too deeply")

    def expr(self) -> Node:
        self._enter()
        node = self.term()
        while self.peek() in (("op", "+"), ("op", "-")):
            op = self.take()[1]
            node = Bin(op, node, self.term())
        self.depth -= 1
        return node

    def term(self) -> Node:
        node = self.unary()
        while self.peek() in (("op", "*"), ("op", "/")):
            op = self.take()[1]
            node = Bin(op, node, self.unary())
        return node

    def unary(self) -> Node:
        if self.peek() == ("op", "-"):
            self.take()
            return Neg(self.unary())
        return self.power()

    def power(self) -> Node:
        base = self.atom()
        if self.peek() == ("op", "^"):
            self.take()
            self._enter()
            exp = self.exponent()
            self.depth -= 1
            return Bin("^", base, exp)
        return base

    def exponent(self) -> Node:
        if self.peek() == ("op", "-"):
            self.take()
            return Neg(self.exponent())
        return self.power()

    def atom(self) -> Node:
        kind, text = self.take()
        if kind == "num":
            return Num(float(text))
        if kind == "id":
            if self.peek() == ("op", "("):
                return self.call(text)
            if text in FUNCTIONS:
                raise FormulaError(f"'{text}' is a function: write {text}( ... )")
            if text in _BANNED:
                raise FormulaError(_BANNED[text])
            return Name(text)
        if (kind, text) == ("op", "("):
            node = self.expr()
            self.expect(")")
            return node
        raise FormulaError(f"unexpected '{text}'")

    def call(self, fn: str) -> Node:
        if fn not in FUNCTIONS:
            reason = _BANNED.get(fn, f"'{fn}' is not an allowed function (allowed: {', '.join(sorted(FUNCTIONS))})")
            raise FormulaError(reason)
        self.expect("(")
        args = [self.expr()]
        while self.peek() == ("op", ","):
            self.take()
            args.append(self.expr())
        self.expect(")")
        lo, hi = FUNCTIONS[fn]
        if len(args) < lo or (hi is not None and len(args) > hi):
            want = f"{lo}" if hi == lo else f"at least {lo}" if hi is None else f"{lo} to {hi}"
            raise FormulaError(f"{fn} takes {want} argument(s), not {len(args)}")
        return Call(fn, tuple(args))


def parse(text: str) -> Node:
    """The syntax tree of one expression, or a FormulaError saying what is wrong."""
    return _Parser(text).parse()


def names(node: Node) -> set[str]:
    """Every name the expression reads (constants included)."""
    if isinstance(node, Name):
        return {node.name}
    if isinstance(node, Neg):
        return names(node.arg)
    if isinstance(node, Bin):
        return names(node.left) | names(node.right)
    if isinstance(node, Call):
        return set().union(*(names(a) for a in node.args))
    return set()


def free_names(node: Node) -> set[str]:
    """The names that must be defined by the page: every name except the built-in constants."""
    return names(node) - set(CONSTANTS)


# ── the Python evaluator ─────────────────────────────────────────────────────────────────────────────────────────────────
def _finite(x: float, what: str) -> float:
    if not math.isfinite(x):
        raise FormulaError(f"{what} has no finite value")
    return x


def evaluate(node: Node, env: dict[str, float]) -> float:
    """The value, or a FormulaError. Every intermediate value must be finite, as in the page."""
    if isinstance(node, Num):
        return node.value
    if isinstance(node, Name):
        if node.name in env:
            return _finite(float(env[node.name]), node.name)
        if node.name in CONSTANTS:
            return CONSTANTS[node.name][0]
        raise FormulaError(f"'{node.name}' has no value")
    if isinstance(node, Neg):
        return -evaluate(node.arg, env)
    if isinstance(node, Bin):
        a, b = evaluate(node.left, env), evaluate(node.right, env)
        try:
            if node.op == "+":
                r = a + b
            elif node.op == "-":
                r = a - b
            elif node.op == "*":
                r = a * b
            elif node.op == "/":
                r = a / b
            else:
                r = math.pow(a, b)
        except (ZeroDivisionError, ValueError, OverflowError) as exc:
            raise FormulaError(f"'{node.op}' has no value here ({type(exc).__name__})") from exc
        return _finite(r, f"'{a:g} {node.op} {b:g}'")
    args = [evaluate(a, env) for a in node.args]
    try:
        r = _call(node.fn, args)
    except (ZeroDivisionError, ValueError, OverflowError) as exc:
        raise FormulaError(f"{node.fn}({', '.join(f'{a:g}' for a in args)}) has no value ({type(exc).__name__})") from exc
    return _finite(r, f"{node.fn}(...)")


def _call(fn: str, a: list[float]) -> float:
    match fn:
        case "sqrt":
            return math.sqrt(a[0])
        case "abs":
            return abs(a[0])
        case "min":
            return min(a)
        case "max":
            return max(a)
        case "exp":
            return math.exp(a[0])
        case "ln":
            return math.log(a[0])
        case "log10":
            return math.log10(a[0])
        case "sin":
            return math.sin(a[0])
        case "cos":
            return math.cos(a[0])
        case "tan":
            return math.tan(a[0])
        case "asin":
            return math.asin(a[0])
        case "acos":
            return math.acos(a[0])
        case "atan":
            return math.atan(a[0])
        case "deg":
            return a[0] * 180.0 / math.pi
        case "rad":
            return a[0] * math.pi / 180.0
    raise FormulaError(f"'{fn}' is not an allowed function")


# ── the JavaScript emitter ───────────────────────────────────────────────────────────────────────────────────────────────
# The page defines N (a finite number or NaN), D (division) and P (power) once, so an expression reads as plain nested calls and a value that has no value is NaN at
# the step where it arises, exactly where `evaluate` raises. Variables are read from the object V.
JS_HELPERS = (
    "function N(r){return isFinite(r)?r:NaN}"
    "function D(a,b){return b===0?NaN:N(a/b)}"
    "function P(a,b){return N(Math.pow(a,b))}"
)
_JS_FN = {
    "sqrt": "Math.sqrt",
    "abs": "Math.abs",
    "min": "Math.min",
    "max": "Math.max",
    "exp": "Math.exp",
    "ln": "Math.log",
    "log10": "Math.log10",
    "sin": "Math.sin",
    "cos": "Math.cos",
    "tan": "Math.tan",
    "asin": "Math.asin",
    "acos": "Math.acos",
    "atan": "Math.atan",
}


def _js_num(x: float) -> str:
    return repr(float(x))


def to_js(node: Node) -> str:
    """A JavaScript expression equal to the formula, reading names from `V`. Needs `JS_HELPERS` in scope."""
    if isinstance(node, Num):
        return _js_num(node.value)
    if isinstance(node, Name):
        if node.name in CONSTANTS:
            return _js_num(CONSTANTS[node.name][0])
        return f"V.{node.name}"
    if isinstance(node, Neg):
        return f"(-{to_js(node.arg)})"
    if isinstance(node, Bin):
        a, b = to_js(node.left), to_js(node.right)
        if node.op == "/":
            return f"D({a},{b})"
        if node.op == "^":
            return f"P({a},{b})"
        return f"N({a}{node.op}{b})"
    args = ",".join(to_js(a) for a in node.args)
    if node.fn == "deg":
        return f"N({args}*180/Math.PI)"
    if node.fn == "rad":
        return f"N({args}*Math.PI/180)"
    return f"N({_JS_FN[node.fn]}({args}))"


# ── units ────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# A unit is a dimension vector over (m, kg, s, A, K, mol, cd) and a scale to the SI unit. Fractions, so a square root can halve a dimension.
_DIMS = ("m", "kg", "s", "A", "K", "mol", "cd")
Dims = tuple[Fraction, ...]


@dataclass(frozen=True)
class Unit:
    dims: Dims
    scale: float = 1.0

    def __mul__(self, other: Unit) -> Unit:
        return Unit(tuple(a + b for a, b in zip(self.dims, other.dims, strict=True)), self.scale * other.scale)

    def __truediv__(self, other: Unit) -> Unit:
        return Unit(tuple(a - b for a, b in zip(self.dims, other.dims, strict=True)), self.scale / other.scale)

    def power(self, p: Fraction) -> Unit:
        return Unit(tuple(a * p for a in self.dims), self.scale ** float(p))

    @property
    def dimensionless(self) -> bool:
        return all(d == 0 for d in self.dims)


def _d(**kw: int) -> Dims:
    return tuple(Fraction(kw.get(k, 0)) for k in _DIMS)


ONE = Unit(_d())
_N = _d(kg=1, m=1, s=-2)
_J = _d(kg=1, m=2, s=-2)
_W = _d(kg=1, m=2, s=-3)
_PA = _d(kg=1, m=-1, s=-2)
_V = _d(kg=1, m=2, s=-3, A=-1)
_ATOMS: dict[str, Unit] = {
    "m": Unit(_d(m=1)), "cm": Unit(_d(m=1), 1e-2), "mm": Unit(_d(m=1), 1e-3), "km": Unit(_d(m=1), 1e3), "dm": Unit(_d(m=1), 1e-1),
    "g": Unit(_d(kg=1), 1e-3), "kg": Unit(_d(kg=1)), "mg": Unit(_d(kg=1), 1e-6),
    "s": Unit(_d(s=1)), "ms": Unit(_d(s=1), 1e-3), "min": Unit(_d(s=1), 60.0), "h": Unit(_d(s=1), 3600.0),
    "A": Unit(_d(A=1)), "mA": Unit(_d(A=1), 1e-3), "K": Unit(_d(K=1)), "mol": Unit(_d(mol=1)), "cd": Unit(_d(cd=1)),
    "N": Unit(_N), "kN": Unit(_N, 1e3), "J": Unit(_J), "kJ": Unit(_J, 1e3), "W": Unit(_W), "kW": Unit(_W, 1e3),
    "Pa": Unit(_PA), "kPa": Unit(_PA, 1e3), "MPa": Unit(_PA, 1e6), "Hz": Unit(_d(s=-1)),
    "V": Unit(_V), "C": Unit(_d(A=1, s=1)), "ohm": Unit(_d(kg=1, m=2, s=-3, A=-2)),
    "L": Unit(_d(m=3), 1e-3), "mL": Unit(_d(m=3), 1e-6),
    "deg": ONE, "rad": ONE, "planet": ONE, "count": ONE, "ratio": ONE,
}
_FACTOR = re.compile(r"^([A-Za-z]+)(?:\^?(-?\d+))?$")


def parse_unit(text: str) -> Unit | None:
    """The unit, ONE for no unit, or None when the text is not a unit this module knows (the check is then skipped, never guessed)."""
    t = text.strip()
    if not t or t == "1":
        return ONE
    segments = t.split("/")
    out: Unit | None = None
    for i, seg in enumerate(segments):
        part = ONE
        for fac in re.split(r"[\s*.·]+", seg.strip()):
            if not fac:
                continue
            m = _FACTOR.match(fac)
            if not m or m.group(1) not in _ATOMS:
                return None
            part = part * _ATOMS[m.group(1)].power(Fraction(int(m.group(2) or 1)))
        out = part if i == 0 else (out / part if out is not None else None)
    return out


def _same(a: Unit, b: Unit) -> bool:
    """Same dimension. Scale is deliberately not compared (see the module note)."""
    return a.dims == b.dims


def _is_literal(node: Node) -> bool:
    return isinstance(node, Num) or (isinstance(node, Neg) and isinstance(node.arg, Num))


def _plain(value: float) -> bool:
    """A number that does not change a quantity's dimension: a small whole number or one half. Any other literal may stand for a constant with a unit."""
    return value in (0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0)


def describe(u: Unit) -> str:
    parts = [f"{k}^{v}" if v != 1 else k for k, v in zip(_DIMS, u.dims, strict=True) if v != 0]
    scale = "" if math.isclose(u.scale, 1.0) else f" x {u.scale:g}"
    return (" ".join(parts) or "a pure number") + scale


def _power_unit(node: Bin, a: Unit | None, b: Unit | None) -> Unit | None:
    if a is not None and a.dimensionless:
        return ONE
    if not _is_literal(node.right):
        if a is None:
            return None
        raise FormulaError("an exponent on a quantity with a unit must be a plain number")
    if a is None:
        return None
    lit = node.right
    e = lit.value if isinstance(lit, Num) else -lit.arg.value  # type: ignore[union-attr]
    return a.power(Fraction(e).limit_denominator(8))


def unit_of(node: Node, units: dict[str, Unit | None]) -> Unit | None:
    """The unit of an expression, None where it cannot be known, or a FormulaError where the units do not fit (adding metres to seconds)."""
    if isinstance(node, Num):
        return ONE if _plain(node.value) else None
    if isinstance(node, Name):
        if node.name in CONSTANTS:
            return parse_unit(CONSTANTS[node.name][1])
        return units.get(node.name)
    if isinstance(node, Neg):
        return unit_of(node.arg, units)
    if isinstance(node, Bin):
        a, b = unit_of(node.left, units), unit_of(node.right, units)
        if node.op in "+-":
            # A bare number joined to a quantity takes the quantity's unit (T - 273, x + 0.5): it is only a magnitude.
            a = None if _is_literal(node.left) else a
            b = None if _is_literal(node.right) else b
            if a is not None and b is not None and not _same(a, b):
                raise FormulaError(f"'{node.op}' joins {describe(a)} and {describe(b)}; convert one so the units match")
            return a if a is not None else b
        if node.op == "^":
            return _power_unit(node, a, b)
        if a is None or b is None:
            return None
        return a * b if node.op == "*" else a / b
    args = [unit_of(a, units) for a in node.args]
    if node.fn in ("sin", "cos", "tan", "exp", "ln", "log10"):
        if args[0] is not None and not args[0].dimensionless:
            raise FormulaError(f"{node.fn} needs a pure number or an angle, not {describe(args[0])}")
        return ONE
    if node.fn in ("asin", "acos", "atan", "deg", "rad"):
        if args[0] is not None and not args[0].dimensionless:
            raise FormulaError(f"{node.fn} needs a pure number, not {describe(args[0])}")
        return ONE
    if node.fn == "sqrt":
        return args[0].power(Fraction(1, 2)) if args[0] is not None else None
    if node.fn == "abs":
        return args[0]
    known = [a for a, n in zip(args, node.args, strict=True) if a is not None and not _is_literal(n)]
    if any(not _same(known[0], k) for k in known[1:]):
        raise FormulaError(f"{node.fn} compares quantities in different units; convert them first")
    return known[0] if known else None


def check_units(node: Node, units: dict[str, Unit | None], declared: str | None) -> None:
    """Raise a FormulaError if the units do not fit, or if the result's unit disagrees with the declared one. A no-op wherever a unit is unknown."""
    got = unit_of(node, units)
    if declared is None or got is None:
        return
    want = parse_unit(declared)
    if want is not None and not _same(got, want):
        raise FormulaError(f"the formula gives {describe(got)} but it is declared in [{declared}] ({describe(want)})")
