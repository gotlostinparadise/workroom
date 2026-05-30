from __future__ import annotations

from importlib import metadata
from pathlib import Path

import kernel


WORKROOM_ROOT = Path("/home/bm/Work/Projects/AGENTS/Agency/Workroom").resolve()
KERNEL_ROOT = Path("/home/bm/Work/Projects/AGENTS/Agency/Kernel").resolve()


def assert_external_kernel_dependency(testcase) -> None:
    kernel_file = Path(kernel.__file__).resolve()
    testcase.assertNotIn(WORKROOM_ROOT, [kernel_file, *kernel_file.parents])
    if KERNEL_ROOT in [kernel_file, *kernel_file.parents]:
        return

    distribution = metadata.distribution("kernel")
    direct_url = distribution.read_text("direct_url.json") or ""
    testcase.assertIn("/home/bm/Work/Projects/AGENTS/Agency/Kernel", direct_url)
