"""Check that every figure in an AI-written memo traces back to metrics.json.

Each number in the memo is parsed with its unit ($, K, M, %) and the precision
it was written at. It passes if some metric value rounds to it at that
precision. Rates stored as fractions (0.258) also match their percent form (26%).
Anything else is reported as ungrounded, so a hallucinated figure blocks the
memo instead of reaching an executive.
"""
import json
import re
import sys

TOKEN = re.compile(r"\$?\d[\d,]*(?:\.\d+)?(?:\s?[KkMm]\b)?%?")
IGNORE = re.compile(r"\bLF-\d{4}\b")  # part numbers are identifiers, not figures


def _leaves(obj):
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        yield float(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _leaves(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _leaves(v)


def allowed_values(metrics: dict) -> list:
    vals = list(_leaves(metrics))
    return vals + [v * 100 for v in vals if abs(v) <= 1]


def parse(token: str):
    t = token.replace("$", "").replace(",", "").replace("%", "").strip()
    mult = 1.0
    if t[-1:] in "KkMm":
        mult = 1e3 if t[-1] in "Kk" else 1e6
        t = t[:-1].strip()
    decimals = len(t.split(".")[1]) if "." in t else 0
    return float(t) * mult, 0.5 * (10 ** -decimals) * mult


def check(memo: str, metrics: dict) -> dict:
    vals = allowed_values(metrics)
    text = IGNORE.sub(" ", memo)
    ungrounded, n = [], 0
    for m in TOKEN.finditer(text):
        value, tol = parse(m.group())
        n += 1
        if not any(abs(v - value) <= tol + 1e-9 for v in vals):
            ungrounded.append(m.group())
    return {"checked": n, "ungrounded": ungrounded}


if __name__ == "__main__":
    memo_path, metrics_path = sys.argv[1], sys.argv[2]
    r = check(open(memo_path).read(), json.load(open(metrics_path)))
    print(f"{r['checked']} figures checked, {len(r['ungrounded'])} ungrounded: {r['ungrounded']}")
    sys.exit(1 if r["ungrounded"] else 0)
