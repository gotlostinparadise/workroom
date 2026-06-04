from __future__ import annotations

from importlib import metadata
from pathlib import Path

import kernel


WORKROOM_ROOT = Path(__file__).resolve().parents[1]
KERNEL_ROOT = (WORKROOM_ROOT.parent / "Kernel").resolve()


def assert_external_kernel_dependency(testcase) -> None:
    kernel_file = Path(kernel.__file__).resolve()
    testcase.assertNotIn(WORKROOM_ROOT, [kernel_file, *kernel_file.parents])
    if KERNEL_ROOT in [kernel_file, *kernel_file.parents]:
        return

    distribution = metadata.distribution("kernel")
    direct_url = distribution.read_text("direct_url.json") or ""
    testcase.assertTrue(
        str(KERNEL_ROOT) in direct_url or "file:../Kernel" in direct_url,
        direct_url,
    )
