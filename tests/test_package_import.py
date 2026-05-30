from __future__ import annotations

import unittest

import agency_workroom
from tests.kernel_dependency_assertions import assert_external_kernel_dependency


class PackageImportTests(unittest.TestCase):
    def test_imports_use_external_kernel_dependency(self) -> None:
        self.assertEqual("agency_workroom", agency_workroom.__name__)
        assert_external_kernel_dependency(self)


if __name__ == "__main__":
    unittest.main()
