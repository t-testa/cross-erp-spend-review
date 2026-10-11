"""Draft the executive memo with Claude, then check it is grounded in the metrics.

Usage: ANTHROPIC_API_KEY=... python -m spend.memo
Without a key, the filled prompt is written to output/memo_prompt.md so it can
be pasted into any chat interface, and the reply checked with spend.grounding.
"""
import json
import os
import sys
from pathlib import Path

from spend.grounding import check

ROOT = Path(__file__).resolve().parent.parent
MODEL = os.environ.get("MEMO_MODEL", "claude-sonnet-4-5")


def build_prompt(metrics: dict) -> str:
    return (ROOT / "prompts/exec_memo.md").read_text().replace("{metrics}", json.dumps(metrics, indent=1))


def draft(prompt: str) -> str:
    import anthropic  # only needed when a key is set
    client = anthropic.Anthropic()
    msg = client.messages.create(model=MODEL, max_tokens=1200, messages=[{"role": "user", "content": prompt}])
    return msg.content[0].text


if __name__ == "__main__":
    metrics = json.loads((ROOT / "output/metrics.json").read_text())
    prompt = build_prompt(metrics)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        (ROOT / "output/memo_prompt.md").write_text(prompt)
        sys.exit("No ANTHROPIC_API_KEY set: prompt written to output/memo_prompt.md")
    memo = draft(prompt)
    (ROOT / "output/exec_memo.md").write_text(memo)
    result = check(memo, metrics)
    print(f"{result['checked']} figures checked, {len(result['ungrounded'])} ungrounded: {result['ungrounded']}")
    sys.exit(1 if result["ungrounded"] else 0)
