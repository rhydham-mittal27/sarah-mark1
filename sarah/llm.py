"""LLM wrapper.  OllamaLLM talks to a local Ollama server (default: llama3.2:1b); StubLLM is a deterministic stand-in for tests."""
import hashlib
import json
import re
import urllib.request


def normalise(text: str) -> str:
    return re.sub(r"[\s\-]+", "_", text.lower())


def parse_choice(reply: str, options):
    """Return the option mentioned earliest in the reply (spaces/hyphens treated as underscores), or None."""
    t = normalise(reply)
    best, pos = None, 10 ** 9
    for o in sorted(options, key=len, reverse=True):
        for m in re.finditer(r"(?<![a-z])" + re.escape(o) + r"(?![a-z])", t):
            if m.start() < pos:
                best, pos = o, m.start()
            break
    return best


class OllamaLLM:
    def __init__(self, model="llama3.2:1b", host="http://localhost:11434", temperature=0.3, timeout=120):
        self.model, self.host, self.temperature, self.timeout = model, host, temperature, timeout
        self.calls = 0
        self.cache = {}

    def generate(self, prompt: str, max_tokens: int = 24, temperature=None, seed=None) -> str:
        temp = self.temperature if temperature is None else temperature
        key = hashlib.md5(f"{self.model}|{temp}|{seed}|{max_tokens}|{prompt}".encode()).hexdigest()
        if key in self.cache and temp == 0:
            return self.cache[key]
        body = {"model": self.model, "prompt": prompt, "stream": False, "keep_alive": "10m",
                "options": {"temperature": temp, "num_predict": max_tokens, **({"seed": seed} if seed is not None else {})}}
        req = urllib.request.Request(self.host + "/api/generate", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            out = json.loads(r.read())["response"]
        self.calls += 1
        if temp == 0:
            self.cache[key] = out
        return out

    def choose(self, prompt: str, options, seed=None):
        """Ask for one of `options`; returns (choice or None, raw reply)."""
        reply = self.generate(prompt, max_tokens=20, seed=seed)
        return parse_choice(reply, options), reply


class StubLLM:
    """Deterministic fake: picks the first option that appears in the prompt's OPTIONS line in a seeded-random order.  Used by tests."""
    def __init__(self, rng=None, noise=0.0):
        import random
        self.rng = rng or random.Random(0)
        self.calls = 0
        self.noise = noise

    def generate(self, prompt, max_tokens=24, temperature=None, seed=None):
        self.calls += 1
        m = re.search(r"OPTIONS: (.*)", prompt)
        opts = [o.strip() for o in m.group(1).split(",")] if m else ["wet"]
        return self.rng.choice(opts)

    def choose(self, prompt, options, seed=None):
        r = self.generate(prompt)
        return parse_choice(r, options), r
