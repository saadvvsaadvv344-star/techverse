"""Auric's brain on a computer without a graphics card (GitHub's free cloud computers): the same 7B brains, compact
(GGUF q4_k_m), run by llama.cpp's server. Same methods as auricv2_local.AuricV2, so the TechVerse agent doesn't change:
prompt(), ask(), complete(), scores(), choose(), keep().

    b = LlamaBrain("http://127.0.0.1:8081")       # a llama-server already running with the model
"""
import json
import math
import urllib.request


class LlamaBrain:
    def __init__(self, url, label="7B (cloud, processor)"):
        self.url, self.label = url.rstrip("/"), label

    # ---- the chat format Qwen was trained with (ChatML)
    def prompt(self, system, user, examples=()):
        parts = [f"<|im_start|>system\n{system}<|im_end|>\n"]
        for q, a in examples:
            parts.append(f"<|im_start|>user\n{q}<|im_end|>\n<|im_start|>assistant\n{a}<|im_end|>\n")
        parts.append(f"<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n")
        return "".join(parts)

    def _post(self, body, timeout=3600):
        req = urllib.request.Request(f"{self.url}/completion", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())

    def complete(self, text, max_new=150):
        r = self._post({"prompt": text, "n_predict": max_new, "temperature": 0, "cache_prompt": True,
                        "stop": ["<|im_end|>", "<|endoftext|>"]})
        return r.get("content", "")

    def ask(self, system, user, max_new=220, examples=()):
        return self.complete(self.prompt(system, user, examples), max_new).strip()

    def keep(self, prefix):
        """(llama-server keeps the last prompt's reading by itself: cache_prompt)"""

    def scores(self, text, options):
        """{option: log-probability of its first token right after text} (enough for yes / no and labels)."""
        r = self._post({"prompt": text, "n_predict": 1, "temperature": 0, "cache_prompt": True, "n_probs": 40})
        first = (r.get("completion_probabilities") or [{}])[0]
        top = {}
        for p in first.get("top_logprobs") or []:                       # newer llama.cpp (OpenAI-like)
            top[p.get("token", "").strip().lower()] = max(top.get(p.get("token", "").strip().lower(), -99), p.get("logprob", -99))
        for p in first.get("probs") or []:                              # older llama.cpp
            t = p.get("tok_str", "").strip().lower()
            top[t] = max(top.get(t, -99), math.log(max(p.get("prob", 0), 1e-12)))
        out = {}
        for o in options:
            key = o.strip().strip('"').lower()
            hits = [lp for t, lp in top.items() if t and (key.startswith(t) or t.startswith(key))]
            out[o] = max(hits) if hits else -30.0
        return out

    def choose(self, text, options, bias_text=None):
        s = self.scores(text, options)
        if bias_text:
            b = self.scores(bias_text, options)
            s = {o: s[o] - b[o] for o in options}
        return max(options, key=lambda o: s[o])
