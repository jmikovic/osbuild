#
# Test for the build root
#

import pathlib
import os
import sys
import tempfile
import unittest

from osbuild.buildroot import BuildRoot
from osbuild.monitor import LogMonitor, NullMonitor
from osbuild.pipeline import detect_host_runner
from .. import test


@unittest.skipUnless(test.TestBase.can_bind_mount(), "root-only")
class TestBuildRoot(test.TestBase):
    """Check BuildRoot"""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_basic(self):
        runner = detect_host_runner()
        libdir = os.path.abspath(os.curdir)
        var = pathlib.Path(self.tmp.name, "var")
        var.mkdir()

        monitor = NullMonitor(sys.stderr.fileno())
        with BuildRoot("/", runner, libdir, var) as root:

            r = root.run(["/usr/bin/true"], monitor)
            self.assertEqual(r.returncode, 0)

            # Test we can use `.run` multiple times
            r = root.run(["/usr/bin/true"], monitor)
            self.assertEqual(r.returncode, 0)

            r = root.run(["/usr/bin/false"], monitor)
            self.assertNotEqual(r.returncode, 0)

    def test_runner_fail(self):
        runner = "org.osbuild.nonexistantrunner"
        libdir = os.path.abspath(os.curdir)
        var = pathlib.Path(self.tmp.name, "var")
        var.mkdir()

        logfile = os.path.join(self.tmp.name, "log.txt")

        with BuildRoot("/", runner, libdir, var) as root, \
             open(logfile, "w") as log:

            monitor = LogMonitor(log.fileno())

            r = root.run(["/usr/bin/true"], monitor)

        self.assertEqual(r.returncode, 1)
        with open(logfile) as f:
            log = f.read()
        assert log
        assert r.output
        self.assertEqual(log, r.output)

    def test_output(self):
        runner = detect_host_runner()
        libdir = os.path.abspath(os.curdir)
        var = pathlib.Path(self.tmp.name, "var")
        var.mkdir()

        data = "42. cats are superior to dogs"

        monitor = NullMonitor(sys.stderr.fileno())
        with BuildRoot("/", runner, libdir, var) as root:

            r = root.run(["/usr/bin/echo", data], monitor)
            self.assertEqual(r.returncode, 0)

        self.assertIn(data, r.output.strip())

    @unittest.skipUnless(test.TestBase.have_test_data(), "no test-data access")
    def test_bind_mounts(self):
        runner = detect_host_runner()
        libdir = os.path.abspath(os.curdir)
        var = pathlib.Path(self.tmp.name, "var")
        var.mkdir()

        rw_data = pathlib.Path(self.tmp.name, "data")
        rw_data.mkdir()

        scripts = os.path.join(self.locate_test_data(), "scripts")

        monitor = NullMonitor(sys.stderr.fileno())
        with BuildRoot("/", runner, libdir, var) as root:

            ro_binds = [f"{scripts}:/scripts"]

            cmd = ["/scripts/mount_flags.py",
                   "/scripts",
                   "ro"]

            r = root.run(cmd, monitor, readonly_binds=ro_binds)
            self.assertEqual(r.returncode, 0)

            cmd = ["/scripts/mount_flags.py",
                   "/rw-data",
                   "ro"]

            binds = [f"{rw_data}:/rw-data"]
            r = root.run(cmd, monitor, binds=binds, readonly_binds=ro_binds)
            self.assertEqual(r.returncode, 1)

    @unittest.skipUnless(test.TestBase.have_test_data(), "no test-data access")
    @unittest.skipUnless(os.path.exists("/sys/fs/selinux"), "no SELinux")
    def test_selinuxfs_ro(self):
        # /sys/fs/selinux must never be writable in the container
        # because RPM and other tools must not assume the policy
        # of the host is the valid policy

        runner = detect_host_runner()
        libdir = os.path.abspath(os.curdir)
        var = pathlib.Path(self.tmp.name, "var")
        var.mkdir()

        scripts = os.path.join(self.locate_test_data(), "scripts")

        monitor = NullMonitor(sys.stderr.fileno())
        with BuildRoot("/", runner, libdir, var) as root:

            ro_binds = [f"{scripts}:/scripts"]

            cmd = ["/scripts/mount_flags.py",
                   "/sys/fs/selinux",
                   "ro"]

            r = root.run(cmd, monitor, readonly_binds=ro_binds)
            self.assertEqual(r.returncode, 0)
