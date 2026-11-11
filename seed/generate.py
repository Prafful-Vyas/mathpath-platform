"""Generates the seed problem bank (seed/topics.json, seed/problems.json) deterministically.
Each generator takes a difficulty level 0-5 and maps it to a rating band, so every topic
spans roughly 500-1450. Run: python -m seed.generate"""

import json
import random
from fractions import Fraction
from pathlib import Path

OUT = Path(__file__).parent
rng = random.Random(42)

TOPICS = [
    ("integers", "Integers", 6, "Adding, subtracting and multiplying negative numbers."),
    ("fractions", "Fractions", 6, "Adding and subtracting fractions with unlike denominators."),
    ("percentages", "Percentages", 7, "Percent of a quantity, percentage change and discounts."),
    ("linear-equations", "Linear Equations", 7, "Solving one-variable equations of the form ax + b = c."),
    ("expressions", "Algebraic Expressions", 8, "Expanding and simplifying products of binomials."),
    ("exponents", "Laws of Exponents", 8, "Multiplying, dividing and raising powers."),
]


def num(f: Fraction) -> str:
    """Display form of an exact answer: integer, terminating decimal, or fraction."""
    if f.denominator == 1:
        return str(f.numerator)
    d = f.denominator
    while d % 2 == 0:
        d //= 2
    while d % 5 == 0:
        d //= 5
    return f"{float(f):g}" if d == 1 else f"{f.numerator}/{f.denominator}"


def poly(a2, a1, a0) -> str:
    """Formats a2 x^2 + a1 x + a0 the way a teacher would write it."""
    out = ""
    for coef, var in ((a2, "x^2"), (a1, "x"), (a0, "")):
        if coef == 0:
            continue
        sign = "-" if coef < 0 else "+"
        mag = abs(coef)
        body = f"{'' if mag == 1 and var else mag}{var}"
        out += (f"-{body}" if sign == "-" else body) if not out else f" {sign} {body}"
    return out or "0"


def integers(level):
    a, b = rng.randint(2, 5 + 4 * level) * rng.choice([-1, 1]), rng.randint(2, 5 + 4 * level) * -1
    if level < 3:
        op, ans = ("+", a + b) if level % 2 == 0 else ("-", a - b)
    else:
        op, ans = "×", a * b
    return f"Calculate {a} {op} ({b})", str(ans), "numeric", "Subtracting a negative is the same as adding."


def fractions(level):
    dens = [[2, 4], [3, 6], [3, 4], [5, 6], [4, 7], [8, 9]][level]
    b, d = dens
    a, c = rng.randint(1, b - 1), rng.randint(1, d - 1)
    op = "+" if level < 3 or rng.random() < 0.5 else "-"
    ans = Fraction(a, b) + Fraction(c, d) if op == "+" else Fraction(a, b) - Fraction(c, d)
    return (f"Work out {a}/{b} {op} {c}/{d}. Give your answer as a fraction in simplest form.",
            f"{ans.numerator}/{ans.denominator}", "fraction", "Rewrite both fractions over a common denominator first.")


def percentages(level):
    if level < 2:
        p, n = rng.choice([10, 25, 50, 20]), rng.randrange(40, 400, 20)
        return f"What is {p}% of {n}?", str(n * p // 100), "numeric", "Divide by 100, then multiply by the percent."
    if level < 4:
        n, p = rng.randrange(200, 2000, 50), rng.choice([15, 30, 35, 12])
        return (f"A bag costs ₹{n}. It is discounted by {p}%. What is the new price in ₹?",
                num(Fraction(n * (100 - p), 100)), "numeric", "Find the discount, then subtract it.")
    old = rng.randrange(40, 200, 8)
    new = old + old * rng.choice([1, 3, 5]) // 8 * (1 if level == 4 else -1)
    return (f"A price changes from ₹{old} to ₹{new}. What is the percentage change? (Use a minus sign for a decrease.)",
            num(Fraction(new - old, old) * 100), "numeric", "Change ÷ original × 100.")


def linear_equations(level):
    x = rng.randint(-6, 9) if level > 1 else rng.randint(1, 9)
    a = rng.choice([2, 3, 4, 5, 6, 7]) * (rng.choice([-1, 1]) if level > 2 else 1)
    b = rng.randint(-12, 15)
    if level < 4:
        return f"Solve for x: {a}x {'+' if b >= 0 else '-'} {abs(b)} = {a * x + b}", str(x), "numeric", \
            "Undo the addition first, then divide by the coefficient."
    c = rng.choice([1, 2, 3]) if a != 1 else 2
    # a x + b = c x + d  ->  x = (d - b) / (a - c)
    d = (a - c) * x + b
    return (f"Solve for x: {a}x {'+' if b >= 0 else '-'} {abs(b)} = {c}x {'+' if d >= 0 else '-'} {abs(d)}",
            str(x), "numeric", "Collect the x terms on one side.")


def expressions(level):
    a, c = (1, 1) if level < 2 else (rng.randint(1, 3), rng.randint(2, 4))
    b, d = rng.randint(1, 6) * (1 if level < 1 else rng.choice([-1, 1])), rng.randint(1, 7) * rng.choice([-1, 1])
    fmt = lambda p, q: f"({'' if p == 1 else p}x {'+' if q >= 0 else '-'} {abs(q)})"
    ans = poly(a * c, a * d + b * c, b * d)
    hint = "Multiply every term in the first bracket by every term in the second."
    if level >= 4:
        return f"Expand and simplify {fmt(a, b)}^2", poly(a * a, 2 * a * b, b * b), "expression", hint
    return f"Expand and simplify {fmt(a, b)}{fmt(c, d)}", ans, "expression", hint


def exponents(level):
    m, n = rng.randint(2, 6), rng.randint(2, 6)
    if level < 2:
        return f"Simplify x^{m} × x^{n}", f"x^{m + n}", "expression", "When multiplying powers, add the exponents."
    if level < 4:
        return f"Simplify (x^{m})^{n}", f"x^{m * n}", "expression", "A power of a power multiplies the exponents."
    k = rng.randint(2, 4)
    return (f"Simplify ({k}x^{m})^2 ÷ x^{n}", f"{k * k}x^{2 * m - n}", "expression",
            "Square the coefficient, then subtract the exponents.")


GENERATORS = {"integers": integers, "fractions": fractions, "percentages": percentages,
              "linear-equations": linear_equations, "expressions": expressions, "exponents": exponents}


def main():
    topics = [{"slug": s, "title": t, "grade": g, "order": i, "description": d} for i, (s, t, g, d) in enumerate(TOPICS)]
    problems = []
    for slug, gen in GENERATORS.items():
        seen = set()
        for level in range(6):
            for i in range(6):
                prompt, answer, kind, hint = gen(level)
                if prompt in seen:
                    continue
                seen.add(prompt)
                problems.append({"id": f"{slug}-{level}{i}", "topic": slug, "rating": 500 + 180 * level + rng.randint(-40, 40),
                                 "prompt": prompt, "answer": answer, "answer_type": kind, "hint": hint})
    (OUT / "topics.json").write_text(json.dumps(topics, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "problems.json").write_text(json.dumps(problems, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{len(topics)} topics, {len(problems)} problems")


if __name__ == "__main__":
    main()
