"""Import-level health checks for the package scaffold."""

import unittest

import spectraderm
from spectraderm.health import package_health


class PackageHealthTests(unittest.TestCase):
    def test_package_import_and_health_check(self) -> None:
        self.assertEqual(spectraderm.__version__, "0.1.0")
        self.assertEqual(package_health()["status"], "ok")
