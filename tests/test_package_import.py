from __future__ import annotations

import unittest
from pathlib import Path

import agency_workroom
import kernel


class PackageImportTests(unittest.TestCase):
    def test_imports_use_external_kernel_dependency(self) -> None:
        self.assertEqual("agency_workroom", agency_workroom.__name__)
        kernel_file = Path(kernel.__file__).resolve()
        self.assertIn(
            Path("/home/bm/Work/Projects/AGENTS/Agency/Kernel/src/kernel").resolve(),
            [kernel_file.parent, *kernel_file.parents],
        )


if __name__ == "__main__":
    unittest.main()
