"""Answer checking for typed math answers.

Student input is parsed with SymPy, but only after a whitelist check (digits, operators,
brackets and a few variable names), with evaluate=False and a guard on exponents, so input
like 9^9^9 cannot hang the worker. Expressions are compared numerically at random points,
the usual approach in online math assessment, instead of trusting simplify()."""

import math
import random
import re
from dataclasses import dataclass

from sympy import Add, Float, Integer, Mul, Pow, Rational, Symbol, pi, sqrt
from sympy.parsing.sympy_parser import (convert_xor, implicit_multiplication_application, parse_expr,
                                        standard_transformations)

VARIABLES = {"x", "y", "a", "b", "n", "m", "t"}
NAMES = VARIABLES | {"sqrt", "pi"}
ALLOWED = re.compile(r"^[0-9a-z+\-*/^().\s]{1,60}$")
TRANSFORMS = standard_transformations + (implicit_multiplication_application, convert_xor)
GLOBALS = {"Add": Add, "Mul": Mul, "Pow": Pow, "Integer": Integer, "Float": Float, "Rational": Rational,
           "Symbol": Symbol, "sqrt": sqrt, "pi": pi, "__builtins__": {}}
REPLACE = {"×": "*", "÷": "/", "−": "-", "–": "-", "²": "^2", "³": "^3", "**": "^"}


class InvalidAnswer(ValueError):
    pass


@dataclass
class Grade:
    correct: bool
    feedback: str


def _normalise(raw: str) -> str:
    s = raw.strip().lower()
    for k, v in REPLACE.items():
        s = s.replace(k, v)
    if not ALLOWED.match(s):
        raise InvalidAnswer("Use numbers, + - * / ^, brackets and variables like x.")

    def split_vars(m):  # "2xy" -> "2x*y"; anything else must be a known name
        word = m.group(0)
        if word in NAMES:
            return word
        if set(word) <= VARIABLES:
            return "*".join(word)
        raise InvalidAnswer(f"Unknown name '{word}'.")
    return re.sub(r"[a-z]+", split_vars, s)


def parse(raw: str):
    s = _normalise(raw)
    try:
        expr = parse_expr(s, local_dict={v: Symbol(v) for v in VARIABLES}, global_dict=dict(GLOBALS),
                          transformations=TRANSFORMS, evaluate=False)
    except Exception as e:  # SymPy raises many types for malformed input
        raise InvalidAnswer("That doesn't look like a complete answer.") from e
    for node in expr.atoms(Pow):
        exp = node.exp
        if exp.has(Pow) or (exp.is_Number and abs(exp) > 50):
            raise InvalidAnswer("Exponent too large.")
    return expr


def _value(expr, subs=None) -> complex:
    return complex(expr.subs(subs or {}).evalf(15))


def _close(a: complex, b: complex) -> bool:
    return abs(a - b) <= 1e-6 * (1 + abs(b))


def _equivalent(student, key) -> bool:
    syms = sorted(student.free_symbols | key.free_symbols, key=str)
    if not syms:
        return _close(_value(student), _value(key))
    rng = random.Random(7)  # fixed seed: grading must be deterministic
    checked = 0
    for _ in range(12):
        point = {s: Rational(rng.randint(-40, 40), rng.randint(1, 9)) for s in syms}
        try:
            a, b = _value(student, point), _value(key, point)
        except (ZeroDivisionError, TypeError):
            continue
        if any(math.isnan(z.real) or math.isinf(z.real) for z in (a, b)):
            continue
        if not _close(a, b):
            return False
        checked += 1
        if checked == 6:
            break
    return checked >= 3


def grade(answer_type: str, key: str, raw: str) -> Grade:
    student, expected = parse(raw), parse(key)
    if answer_type in ("numeric", "fraction") and student.free_symbols:
        return Grade(False, "The answer should be a number.")
    if not _equivalent(student, expected):
        return Grade(False, "Not quite. Check your working and try the hint.")
    if answer_type == "fraction" and (m := re.fullmatch(r"\s*(-?\d+)\s*/\s*(\d+)\s*", raw)):
        if math.gcd(int(m.group(1)), int(m.group(2))) > 1:
            return Grade(False, "Right value, but simplify the fraction fully.")
    return Grade(True, "Correct!")
