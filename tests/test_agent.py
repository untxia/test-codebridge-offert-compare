import io
import json
import os
import unittest
from unittest import mock

from offercompare import agent
from offercompare.diff import compare_files

PDF = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "testset", "pdf")


def report():
    return compare_files(os.path.join(PDF, "offer_original.pdf"), os.path.join(PDF, "offer_revised.pdf"), {},
                         names={"original": "o.pdf", "revised": "r.pdf"})


class FakeResp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False


class AgentTests(unittest.TestCase):
    def test_digest_drops_geometry(self):
        s = json.dumps(agent.digest(report()), ensure_ascii=False)
        self.assertNotIn("bbox", s)
        self.assertNotIn("_ms", s)
        self.assertIn("Écran 27 pouces QHD", s)

    def test_numbers_found_in_report_are_grounded(self):
        dg = agent.digest(report())
        ok = "Le total HT passe de 18 900,00 € à 19 060,00 € ; recalculé : 18 960.00. Prix unitaire 280,00 → 295,00, TVA 20 %, ligne 2 page 1."
        self.assertEqual(agent.ungrounded_numbers(ok, dg), [])

    def test_invented_numbers_are_flagged(self):
        dg = agent.digest(report())
        bad = agent.ungrounded_numbers("Le total est de 12 345,67 € et la remise de 7,5 %.", dg)
        self.assertIn("12 345,67", bad)
        self.assertTrue(any("7,5" in b for b in bad))

    def test_disabled_without_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(agent.enabled())
            with self.assertRaises(agent.AgentDisabled):
                agent.ask(report(), "Résume", [], "fr")

    def test_prompt_rules_and_injection_guard(self):
        sp = agent.system_prompt(agent.digest(report()), "fr")
        self.assertIn("<report>", sp)
        self.assertIn("DONNÉES", sp)
        self.assertIn("ne « corrige » jamais", sp)
        self.assertIn("EXCERPT" if False else "RULES", agent.system_prompt(agent.digest(report()), "en"))

    def test_history_alternates_and_ends_with_assistant(self):
        h = agent._clean_history([{"role": "assistant", "content": "x"}, {"role": "user", "content": "a"}, {"role": "user", "content": "b"},
                                  {"role": "assistant", "content": "c"}, {"role": "user", "content": "d"}, {"role": "evil", "content": "z"}])
        self.assertEqual([m["role"] for m in h], ["user", "assistant"])
        self.assertEqual(h[0]["content"], "a\nb")

    def test_ask_with_mocked_api(self):
        payload = {"content": [{"type": "text", "text": "Le prix de l'écran passe de 280,00 à 295,00 (Original p.1 ligne 2). Remise 99,99 €."}]}
        seen = {}
        def fake(req, timeout=0):
            seen["body"] = json.loads(req.data); seen["key"] = req.headers.get("X-api-key")
            return FakeResp(json.dumps(payload).encode())
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "k"}), mock.patch("urllib.request.urlopen", fake):
            out = agent.ask(report(), "Résume les écarts", [], "fr")
        self.assertEqual(seen["key"], "k")
        self.assertEqual(seen["body"]["messages"][-1], {"role": "user", "content": "Résume les écarts"})
        self.assertIn("<report>", seen["body"]["system"])
        self.assertEqual(out["unverified_numbers"], ["99,99"])

    def test_rejects_bad_input(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "k"}):
            with self.assertRaises(agent.AgentError):
                agent.ask(report(), "", [], "fr")
            with self.assertRaises(agent.AgentError):
                agent.ask(report(), "x" * 700, [], "fr")
            with self.assertRaises(agent.AgentError):
                agent.ask({"nope": 1}, "salut", [], "fr")


if __name__ == "__main__":
    unittest.main()
