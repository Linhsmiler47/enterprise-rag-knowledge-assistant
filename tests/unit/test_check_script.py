import os
import subprocess
from pathlib import Path

CHECK_SCRIPT = Path(__file__).parents[2] / "scripts" / "check.sh"


def _run_check(
    tmp_path: Path,
    pytest_output: str,
    *,
    skipped_count: int,
    require_integration: bool = False,
) -> subprocess.CompletedProcess[str]:
    fake_uv = tmp_path / "uv"
    fake_uv.write_text(
        "#!/usr/bin/env bash\n"
        'if [[ "$*" == *"pytest"* ]]; then\n'
        '  printf "%s\\n" "$FAKE_PYTEST_OUTPUT"\n'
        '  for arg in "$@"; do\n'
        '    if [[ "$arg" == --junitxml=* ]]; then\n'
        '      report="${arg#--junitxml=}"\n'
        '      printf \'<testsuites><testsuite skipped="%s"/></testsuites>\\n\' \\\n'
        '        "$FAKE_PYTEST_SKIPPED" > "$report"\n'
        "    fi\n"
        "  done\n"
        "fi\n"
    )
    fake_uv.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}:{env['PATH']}"
    env["FAKE_PYTEST_OUTPUT"] = pytest_output
    env["FAKE_PYTEST_SKIPPED"] = str(skipped_count)
    if require_integration:
        env["REQUIRE_INTEGRATION"] = "1"
    else:
        env.pop("REQUIRE_INTEGRATION", None)

    return subprocess.run(
        [str(CHECK_SCRIPT)],
        cwd=CHECK_SCRIPT.parents[1],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_normal_mode_prints_skipped_count_and_reasons_at_end(tmp_path: Path) -> None:
    result = _run_check(
        tmp_path,
        "\n".join(
            [
                "================ short test summary info ================",
                "SKIPPED [2] tests/conftest.py:31: integration tests require a reachable database",
                "================ 13 passed, 2 skipped in 0.50s ================",
            ]
        ),
        skipped_count=2,
    )

    assert result.returncode == 0
    final_summary = result.stdout.split("==> Test skip summary", maxsplit=1)[1]
    assert "Skipped tests: 2" in final_summary
    assert "SKIPPED [2]" in final_summary
    assert "integration tests require a reachable database" in final_summary


def test_required_integration_mode_fails_when_any_test_is_skipped(tmp_path: Path) -> None:
    result = _run_check(
        tmp_path,
        "\n".join(
            [
                "SKIPPED [1] tests/conftest.py:75: document tests require object storage",
                "================ 39 passed, 1 skipped in 0.50s ================",
            ]
        ),
        skipped_count=1,
        require_integration=True,
    )

    assert result.returncode != 0
    assert "REQUIRE_INTEGRATION=1" in result.stderr
    assert "1 test(s) were skipped" in result.stderr


def test_required_integration_mode_passes_when_no_test_is_skipped(tmp_path: Path) -> None:
    result = _run_check(
        tmp_path,
        "================ 40 passed in 0.50s ================",
        skipped_count=0,
        require_integration=True,
    )

    assert result.returncode == 0
    final_summary = result.stdout.split("==> Test skip summary", maxsplit=1)[1]
    assert "Skipped tests: 0" in final_summary


def test_required_mode_uses_structured_count_when_text_summary_is_absent(
    tmp_path: Path,
) -> None:
    result = _run_check(
        tmp_path,
        "SKIPPED [3] tests/conftest.py:31: integration services are unavailable",
        skipped_count=3,
        require_integration=True,
    )

    assert result.returncode != 0
    assert "3 test(s) were skipped" in result.stderr
