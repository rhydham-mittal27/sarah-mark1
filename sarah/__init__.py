"""Sarah Mark 1 - a modular software 'child brain' around a tiny local LLM."""
from .brain import Brain
from .config import BrainConfig, CONFIGS
from .llm import OllamaLLM, StubLLM
from .world import Nursery

__all__ = ["Brain", "BrainConfig", "CONFIGS", "OllamaLLM", "StubLLM", "Nursery"]
__version__ = "0.1"
