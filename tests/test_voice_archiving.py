"""Rangement automatique : paires WAV/JSON, identité, prises et catalogue."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

path = Path(__file__).resolve().parents[1] / "scripts/colab/archiver_voix.py"
spec = importlib.util.spec_from_file_location("archiver", path)
archiver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archiver)


class VoiceArchivingTest(unittest.TestCase):
    def prepare(self, base):
        reference = base / "reference"
        reference.mkdir()
        audio = b"RIFFtestWAVEreference"
        (reference / "reference.wav").write_bytes(audio)
        sha = hashlib.sha256(audio).hexdigest()
        doc = {"profile_id": "M-petit", "variant": 1, "reference_sha256": sha, "label": "Enfant fictif"}
        (reference / "voix.json").write_text(json.dumps(doc))
        return reference, sha

    def audition(self, base, sha, data, language="ar"):
        path = base / "audition.wav"
        path.write_bytes(data)
        path.with_suffix(".json").write_text(json.dumps({"reference_sha256": sha,
            "language": language, "audio_sha256": hashlib.sha256(data).hexdigest()}))
        return path

    def test_named_files_and_reusable_reference_in_zip(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            reference, sha = self.prepare(base)
            folder, archive, _ = archiver.save_voice(base / "Voix", reference)
            self.assertTrue(folder.name.startswith("M-petit_var1_"))
            self.assertTrue((folder / "M-petit_var1_reference.wav").is_file())
            self.assertTrue((folder / "M-petit_var1_reference.json").is_file())
            with zipfile.ZipFile(folder / "voix-fictive.zip") as z:
                self.assertEqual(set(z.namelist()), {"reference.wav", "voix.json"})
                self.assertEqual(hashlib.sha256(z.read("reference.wav")).hexdigest(), sha)
            with zipfile.ZipFile(archive) as z:
                self.assertIsNone(z.testzip())

    def test_repeat_is_deduplicated_new_take_preserves_old_and_language_pairs(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            reference, sha = self.prepare(base)
            root = base / "Voix"
            first = self.audition(base, sha, b"first")
            folder, _, one = archiver.save_voice(root, reference, first)
            _, _, same = archiver.save_voice(root, reference, first)
            self.assertEqual(one, same)
            second = self.audition(base, sha, b"second")
            _, _, two = archiver.save_voice(root, reference, second)
            self.assertNotEqual(one, two)
            self.assertEqual(one.read_bytes(), b"first")
            french = self.audition(base, sha, b"bonjour", "fr")
            _, _, fr = archiver.save_voice(root, reference, french)
            self.assertIn("_FR_", fr.name)
            self.assertTrue(fr.with_suffix(".json").is_file())
            catalogue = json.loads((root / "catalogue_voix.json").read_text())
            self.assertEqual(catalogue["voices_count"], 1)
            self.assertIn(two.name, catalogue["entries"][0]["files"])

    def test_wrong_reference_or_corrupt_audition_not_stored(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            reference, sha = self.prepare(base)
            wrong = self.audition(base, "0" * 64, b"wrong")
            with self.assertRaises(ValueError):
                archiver.save_voice(base / "Voix", reference, wrong)
            self.assertFalse((base / "Voix").exists())
            correct = self.audition(base, sha, b"correct")
            correct.write_bytes(b"corrupted")
            with self.assertRaises(ValueError):
                archiver.save_voice(base / "Voix", reference, correct)

    def test_untrusted_profile_cannot_escape_destination(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            reference, _ = self.prepare(base)
            doc = json.loads((reference / "voix.json").read_text())
            doc["profile_id"] = "../../escape"
            (reference / "voix.json").write_text(json.dumps(doc))
            with self.assertRaises(ValueError):
                archiver.save_voice(base / "Voix", reference)
            self.assertFalse((base / "Voix").exists())


if __name__ == "__main__":
    unittest.main()
