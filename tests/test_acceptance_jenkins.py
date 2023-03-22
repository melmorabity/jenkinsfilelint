# SPDX-FileCopyrightText: © 2023 Mohamed El Morabity
# SPDX-License-Identifier: GPL-3.0-or-later

from configparser import ConfigParser
import contextlib
from io import StringIO
import os
from tempfile import NamedTemporaryFile
from unittest import TestCase

import jenkinsfilelint.cli


class TestJenkinsDocker(TestCase):
    JENKINSFILELINT_CONFIG = "tests/fixtures/jenkinsfilelintrc"

    def test_ok(self) -> None:
        status = jenkinsfilelint.cli.main(
            [
                "tests/fixtures/Jenkinsfile",
                "--config",
                self.JENKINSFILELINT_CONFIG,
                "--profile",
                "jenkins",
            ]
        )
        self.assertEqual(status, 0)

    def test_ok_env(self) -> None:
        config_parser = ConfigParser()
        config_parser.read(self.JENKINSFILELINT_CONFIG)

        os.environ.update(
            {
                "JENKINS_URL": config_parser["jenkins"]["url"],
                "JENKINS_USERNAME": config_parser["jenkins"]["username"],
                "JENKINS_PASSWORD": config_parser["jenkins"]["password"],
            }
        )

        try:
            status = jenkinsfilelint.cli.main(
                [
                    "tests/fixtures/Jenkinsfile",
                    "--config",
                    self.JENKINSFILELINT_CONFIG,
                    "--profile",
                    "no-jenkins",
                ]
            )
        finally:
            os.environ.pop("JENKINS_URL")
            os.environ.pop("JENKINS_USERNAME")
            os.environ.pop("JENKINS_PASSWORD")

        self.assertEqual(status, 0)

    def test_bad_jenkinsfile(self) -> None:
        stdout = StringIO()
        with contextlib.redirect_stdout(stdout):
            status = jenkinsfilelint.cli.main(
                [
                    "tests/fixtures/Jenkinsfile",
                    "tests/fixtures/Jenkinsfile-bad",
                    "--config",
                    self.JENKINSFILELINT_CONFIG,
                    "--profile",
                    "jenkins",
                ]
            )

        self.assertEqual(status, 1)
        self.assertIn(
            "tests/fixtures/Jenkinsfile-bad:1:1: error: Missing required "
            'section "stages"\n'
            "tests/fixtures/Jenkinsfile-bad:8:5: error: Undefined section "
            '"stageS"\n',
            stdout.getvalue(),
        )

    def test_bad_binary_jenkinsfileself(self) -> None:
        with self.assertLogs(level="ERROR") as log_context:
            status = jenkinsfilelint.cli.main(
                [
                    "tests/fixtures/Jenkinsfile",
                    "/usr/bin/ls",
                    "--config",
                    self.JENKINSFILELINT_CONFIG,
                    "--profile",
                    "jenkins",
                ]
            )

        self.assertEqual(status, 1)
        self.assertIn(
            "ERROR:root:'utf-8' codec can't decode byte ",
            log_context.output[0],
        )

    def test_unreachable_jenkins(self) -> None:
        with self.assertLogs(level="ERROR") as log_context:
            status = jenkinsfilelint.cli.main(
                [
                    "tests/fixtures/Jenkinsfile",
                    "--config",
                    self.JENKINSFILELINT_CONFIG,
                    "--profile",
                    "no-jenkins",
                ]
            )

        self.assertEqual(status, 1)
        self.assertIn(
            "ERROR:root:HTTPConnectionPool(host='1.2.3.4', port=5678): Max "
            "retries exceeded with url:",
            log_context.output[0],
        )

    def test_no_crumb(self) -> None:
        with self.assertLogs(level="ERROR") as log_context:
            status = jenkinsfilelint.cli.main(
                [
                    "tests/fixtures/Jenkinsfile",
                    "--config",
                    self.JENKINSFILELINT_CONFIG,
                    "--profile",
                    "jenkins-no-crumb",
                ]
            )

        self.assertEqual(status, 1)
        self.assertIn(
            "ERROR:root:Unable to retrieve crumb from http://localhost:8080. "
            "Crumb issuer is probably blocked.",
            log_context.output[0],
        )

    def test_no_jenkinsfile(self) -> None:
        with self.assertLogs(level="ERROR") as log_context:
            status = jenkinsfilelint.cli.main(
                [
                    "tests/fixtures/Jenkinsfile-not-exists",
                    "--config",
                    self.JENKINSFILELINT_CONFIG,
                    "--profile",
                    "jenkins",
                ]
            )

        self.assertEqual(status, 1)
        self.assertIn(
            "ERROR:root:[Errno 2] No such file or directory: "
            "'tests/fixtures/Jenkinsfile-not-exists'",
            log_context.output[0],
        )

    def test_config_ko(self) -> None:
        with self.assertLogs(level="ERROR") as log_context:
            status = jenkinsfilelint.cli.main(
                [
                    "tests/fixtures/Jenkinsfile",
                    "--config",
                    "tests/fixtures/docker/jenkins/Dockerfile",
                    "--profile",
                    "jenkins",
                ]
            )

        self.assertEqual(status, 1)
        self.assertIn(
            "ERROR:root:File contains no section headers",
            log_context.output[0],
        )

    def test_invalid_config(self) -> None:
        with self.assertLogs(
            level="ERROR"
        ) as log_context, NamedTemporaryFile() as config_file:
            config_file.write(
                b"[jenkins]\nusername = username\npassword = password"
            )
            config_file.seek(0)

            status = jenkinsfilelint.cli.main(
                [
                    "tests/fixtures/Jenkinsfile",
                    "--config",
                    config_file.name,
                    "--profile",
                    "jenkins",
                ]
            )

        self.assertEqual(status, 1)
        self.assertIn(
            "ERROR:root:Missing `url` key for profile `jenkins` in "
            f"configuration file {config_file.name}",
            log_context.output[0],
        )

    def test_no_config(self) -> None:
        with self.assertLogs(level="ERROR") as log_context:
            status = jenkinsfilelint.cli.main(
                [
                    "tests/fixtures/Jenkinsfile",
                    "--config",
                    "tests/fixtures/jenkinsfilelintrc-not-exists",
                    "--profile",
                    "jenkins",
                ]
            )

        self.assertEqual(status, 1)
        self.assertIn(
            "ERROR:root:Unable to load configuration file "
            "tests/fixtures/jenkinsfilelintrc-not-exists",
            log_context.output[0],
        )

    def test_no_config_profile(self) -> None:
        profile = "profile-not-exists"
        with self.assertLogs(level="ERROR") as log_context:
            status = jenkinsfilelint.cli.main(
                [
                    "tests/fixtures/Jenkinsfile",
                    "--config",
                    self.JENKINSFILELINT_CONFIG,
                    "--profile",
                    profile,
                ]
            )

        self.assertEqual(status, 1)
        self.assertIn(
            f"ERROR:root:Missing profile `{profile}` in configuration file "
            f"{self.JENKINSFILELINT_CONFIG}",
            log_context.output[0],
        )

    def test_self_signed_cert_ko(self) -> None:
        with self.assertLogs(level="ERROR") as log_context:
            status = jenkinsfilelint.cli.main(
                [
                    "tests/fixtures/Jenkinsfile",
                    "--config",
                    self.JENKINSFILELINT_CONFIG,
                    "--profile",
                    "jenkins-https",
                ]
            )

        self.assertEqual(status, 1)
        self.assertIn(
            "certificate verify failed: self-signed certificate",
            log_context.output[0],
        )

    def test_self_signed_cert_ok(self) -> None:
        status = jenkinsfilelint.cli.main(
            [
                "tests/fixtures/Jenkinsfile",
                "--config",
                self.JENKINSFILELINT_CONFIG,
                "--profile",
                "jenkins-https",
                "--insecure",
            ]
        )

        self.assertEqual(status, 0)
