import hashlib
import unittest
from pathlib import Path
import uuid

from model_artifacts import ModelArtifact, compute_sha256, verify_artifact


class ModelArtifactsTestCase(unittest.TestCase):
    def test_compute_sha256_matches_known_content(self):
        file_path = Path(__file__).resolve().parent / f"tmp-{uuid.uuid4().hex}.bin"
        data = b"cave-drone-test"
        try:
            file_path.write_bytes(data)
            expected = hashlib.sha256(data).hexdigest()
            self.assertEqual(compute_sha256(file_path), expected)
        finally:
            if file_path.exists():
                file_path.unlink()

    def test_verify_artifact_reports_missing_file(self):
        artifact = ModelArtifact(
            key="missing",
            filename="missing.file",
            sha256="0" * 64,
            source_url="https://example.com/missing.file",
            license_note="n/a",
            description="missing artifact",
        )
        ok, message = verify_artifact(artifact)
        self.assertFalse(ok)
        self.assertIn("missing", message)

    def test_verify_artifact_detects_checksum_mismatch(self):
        file_path = Path(__file__).resolve().parent / f"tmp-{uuid.uuid4().hex}.bin"
        try:
            file_path.write_bytes(b"not-the-right-model")
            artifact = ModelArtifact(
                key="bad-hash",
                filename=file_path.name,
                sha256="f" * 64,
                source_url="https://example.com/model.bin",
                license_note="n/a",
                description="checksum mismatch",
            )
            ok, message = verify_artifact(artifact)
            self.assertFalse(ok)
            self.assertIn("checksum mismatch", message)
        finally:
            if file_path.exists():
                file_path.unlink()


if __name__ == "__main__":
    unittest.main()
