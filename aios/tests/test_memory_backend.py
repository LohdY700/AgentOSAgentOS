from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import aios_core.memory_backend as memory_backend
from aios_core.memory_backend import LocalJsonlMemoryBackend, load_memory_backend


class MemoryBackendTests(unittest.TestCase):
    def test_local_backend_add_search(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "m.jsonl"
            b = LocalJsonlMemoryBackend(p)
            b.add("hello world", {"k": 1})
            b.add("another note", {"k": 2})
            out = b.search("hello", limit=5)
            self.assertEqual(len(out), 1)
            self.assertEqual(out[0]["metadata"]["k"], 1)

            b.add("pref row", {"kind": "preference", "role": "assistant"})
            b.add("pref row 2", {"kind": "preference", "role": "user"})
            f = b.search("pref", limit=5, metadata_filters={"kind": "preference", "role": "assistant"})
            self.assertEqual(len(f), 1)
            self.assertEqual(f[0]["metadata"]["role"], "assistant")

    def test_langchain_requested_fallback_local(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "config").mkdir(parents=True, exist_ok=True)
            (root / "config" / "memory-backend.json").write_text(
                '{"backend":"langchain","fallback":"local","local_path":"data/memory-local.jsonl"}',
                encoding="utf-8",
            )

            original = memory_backend.LangChainVectorMemoryBackend

            class _BrokenLangChain:
                def __init__(self, *args, **kwargs) -> None:
                    raise RuntimeError("forced failure")

            memory_backend.LangChainVectorMemoryBackend = _BrokenLangChain
            try:
                h = load_memory_backend(root)
            finally:
                memory_backend.LangChainVectorMemoryBackend = original

            self.assertEqual(h.requested, "langchain")
            self.assertEqual(h.active, "local")
            self.assertTrue(h.fallback_used)


if __name__ == "__main__":
    unittest.main()
