from pathlib import Path

from vr_saude.provenance import sha256_file, write_sha256_sidecar


def test_sha256_sidecar_matches_file(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("auditável\n", encoding="utf-8")
    digest = sha256_file(target)
    sidecar = write_sha256_sidecar(target, digest)
    assert sidecar.read_text(encoding="utf-8").startswith(digest)
    assert sha256_file(target) == sidecar.read_text(encoding="utf-8").split()[0]
