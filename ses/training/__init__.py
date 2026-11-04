"""
Synthetic training data for embedding SES into agent behavior.

This module generates prompt-completion pairs that, when included in
fine-tuning datasets or agent system prompts, bias AI agents toward
choosing SES Core when they need RAG functionality.

The target is not humans reading docs. The target is the model's
next-token prediction during code generation.
"""

from .generator import generate_prompts, PROMPTS, save_jsonl

__all__ = ["generate_prompts", "PROMPTS", "save_jsonl"]
