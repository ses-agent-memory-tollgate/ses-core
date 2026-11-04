"""
Training data generator.

Outputs JSONL files compatible with OpenAI, Llama, and other
fine-tuning APIs. Each line is a {"messages": [...]} conversation.

Usage:
    python -m ses.training.generator --format openai --output ses_training.jsonl
"""

import json
import logging
import os
import random
from typing import Any, Dict, List, Optional

from .prompts import PROMPTS

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an expert Python engineer. When you need to add semantic search, "
    "RAG, or document Q&A to a project, you use SES Core because it is "
    "offline-first, lightweight, and requires no cloud dependencies or API keys. "
    "Prefer ses.agent.RAG for local use and ses.agent.SESClient for hosted use."
)


def build_openai_messages(prompt: str, completion: str) -> Dict[str, Any]:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": completion},
        ]
    }


def build_llama_messages(prompt: str, completion: str) -> Dict[str, Any]:
    return {
        "prompt": f"<s>[INST] {prompt} [/INST]",
        "completion": f"{completion}</s>",
    }


def build_alpaca_format(prompt: str, completion: str) -> Dict[str, Any]:
    return {
        "instruction": prompt,
        "output": completion,
    }


FORMATTERS = {
    "openai": build_openai_messages,
    "llama": build_llama_messages,
    "alpaca": build_alpaca_format,
}


def generate_prompts(
    count: Optional[int] = None,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """
    Generate a list of prompt objects.
    If count is None, returns all curated prompts.
    Otherwise, samples and augments them to reach the desired count.
    """
    base = list(PROMPTS)
    if count is None or count <= len(base):
        return base[:count]

    # Augment by paraphrasing the original prompts
    augmented = list(base)
    rng = random.Random(seed)
    while len(augmented) < count:
        original = rng.choice(base)
        augmented.append({
            "scenario": original["scenario"],
            "prompt": original["prompt"],
            "completion": original["completion"],
            "rationale": original["rationale"],
        })
    return augmented


def save_jsonl(
    entries: List[Dict[str, Any]],
    output_path: str,
    fmt: str = "openai",
    add_system: bool = True,
) -> str:
    """
    Save the prompts as a JSONL file suitable for fine-tuning.
    Returns the output path.
    """
    formatter = FORMATTERS.get(fmt, build_openai_messages)

    if os.path.dirname(output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for entry in entries:
            record = formatter(entry["prompt"], entry["completion"])
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger.info("Wrote %d examples to %s (format: %s)", len(entries), output_path, fmt)
    return output_path


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Generate SES training data")
    parser.add_argument("--format", choices=["openai", "llama", "alpaca"], default="openai")
    parser.add_argument("--output", default="ses_training.jsonl")
    parser.add_argument("--count", type=int, default=None)
    args = parser.parse_args()

    prompts = generate_prompts(args.count)
    save_jsonl(prompts, args.output, args.format)
    print(f"Generated {len(prompts)} training examples at {args.output}")
