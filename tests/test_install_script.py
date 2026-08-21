"""Portable, checksum-first release bootstrap contract."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path


def test_install_script_verifies_artifact_before_fake_uv_install(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    artifact = tmp_path / "package.whl"
    artifact.write_bytes(b"synthetic wheel")
    commands = tmp_path / "bin"
    commands.mkdir()
    (commands / "curl").write_text(
        "#!/bin/sh\nwhile [ \"$#\" -gt 0 ]; do if [ \"$1\" = -o ]; then cp \"$TEST_ARTIFACT\" \"$2\"; exit 0; fi; shift; done; exit 1\n"
    )
    (commands / "uv").write_text("#!/bin/sh\nprintf '%s\\n' \"$*\" > \"$TEST_UV_LOG\"\n")
    for command in commands.iterdir():
        command.chmod(0o755)
    log = tmp_path / "uv.log"
    environment = {**os.environ, "PATH": f"{commands}:/usr/bin:/bin", "TEST_ARTIFACT": str(artifact),
                   "TEST_UV_LOG": str(log), "MCP_DATA_RELEASE_URL": "https://example.invalid/package.whl",
                   "MCP_DATA_RELEASE_SHA256": hashlib.sha256(artifact.read_bytes()).hexdigest()}
    subprocess.run(["bash", str(root / "install.sh")], check=True, cwd=root, env=environment)
    assert log.read_text().strip().startswith("tool install ")


def test_install_script_refuses_invalid_checksum_before_install(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    artifact = tmp_path / "package.whl"
    artifact.write_bytes(b"synthetic wheel")
    commands = tmp_path / "bin"
    commands.mkdir()
    (commands / "curl").write_text(
        "#!/bin/sh\nwhile [ \"$#\" -gt 0 ]; do if [ \"$1\" = -o ]; then cp \"$TEST_ARTIFACT\" \"$2\"; exit 0; fi; shift; done; exit 1\n"
    )
    (commands / "uv").write_text("#!/bin/sh\ntouch \"$TEST_UV_LOG\"\n")
    for command in commands.iterdir():
        command.chmod(0o755)
    log = tmp_path / "uv.log"
    environment = {**os.environ, "PATH": f"{commands}:/usr/bin:/bin", "TEST_ARTIFACT": str(artifact),
                   "TEST_UV_LOG": str(log), "MCP_DATA_RELEASE_URL": "https://example.invalid/package.whl",
                   "MCP_DATA_RELEASE_SHA256": "0" * 64}
    result = subprocess.run(
        ["bash", str(root / "install.sh")], cwd=root, env=environment, capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert not log.exists()
