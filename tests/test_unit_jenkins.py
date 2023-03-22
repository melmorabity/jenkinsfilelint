# SPDX-FileCopyrightText: © 2023 Mohamed El Morabity
# SPDX-License-Identifier: GPL-3.0-or-later

import base64
import contextlib
from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest import TestCase
import unittest.mock
from unittest.mock import MagicMock

from requests import ConnectTimeout
from requests_mock import Mocker
from urllib3.exceptions import InsecureRequestWarning

from jenkinsfilelint.exceptions import JenkinsError
from jenkinsfilelint.jenkins import Jenkins


class TestJenkins(TestCase):
    JENKINS_URL = "https://example.net"
    JENKINS_USERNAME = "username"
    JENKINS_PASSWORD = "password"

    def setUp(self) -> None:
        self.urllib3_disable_warnings = unittest.mock.patch(
            "jenkinsfilelint.jenkins.urllib3.disable_warnings"
        )

        self.requests_mock = Mocker()
        self.requests_mock.start()

        # Set valid Jenkins crumb by default
        self.requests_mock.get(
            f"{self.JENKINS_URL}/{Jenkins._CRUMB_PATH}",
            text="Jenkins-Crumb:0123456789abcdef",
        )

    def tearDown(self) -> None:
        self.requests_mock.stop()

    def test_crumb_failure(self) -> None:
        # Override Jenkins crumb retrieving
        self.requests_mock.get(
            f"{self.JENKINS_URL}/{Jenkins._CRUMB_PATH}", exc=ConnectTimeout
        )

        with self.assertRaises(JenkinsError) as context, Jenkins(
            self.JENKINS_URL
        ):
            pass

        self.assertEqual(type(context.exception.args[0]), ConnectTimeout)

    def test_bad_crumb(self) -> None:
        # Override Jenkins crumb retrieving
        self.requests_mock.get(
            f"{self.JENKINS_URL}/{Jenkins._CRUMB_PATH}", text="XXXXXXXX"
        )

        with self.assertRaises(JenkinsError), Jenkins(self.JENKINS_URL):
            pass

    def test_auth(self) -> None:
        with Jenkins(
            self.JENKINS_URL,
            username=self.JENKINS_USERNAME,
            password=self.JENKINS_PASSWORD,
        ):
            pass

        history = self.requests_mock.request_history[0]
        auth = base64.b64encode(
            f"{self.JENKINS_USERNAME}:{self.JENKINS_PASSWORD}".encode()
        )
        self.assertEqual(
            history.headers.get("Authorization"), "Basic " + auth.decode()
        )

    def test_no_auth(self) -> None:
        with Jenkins(self.JENKINS_URL):
            pass

        history = self.requests_mock.request_history[0]
        self.assertFalse(history.headers.get("Authorization"))

    def test_lint_ok(self) -> None:
        jenkins_response = {"status": "ok", "data": {"result": "success"}}
        self.requests_mock.post(
            f"{self.JENKINS_URL}/{Jenkins._VALIDATOR_PATH}",
            json=jenkins_response,
        )

        stdout = StringIO()
        with contextlib.redirect_stdout(
            stdout
        ), NamedTemporaryFile() as path, Jenkins(self.JENKINS_URL) as jenkins:
            result = jenkins.lint(Path(path.name))

        self.assertTrue(result)
        self.assertFalse(stdout.getvalue())

    def test_lint_ko_syntax(self) -> None:
        jenkins_response = {
            "status": "ok",
            "data": {
                "result": "failure",
                "errors": [
                    {
                        "error": [
                            "Expected a stage @ line 4, column 5.",
                            "No stages specified @ line 3, column 3.",
                        ]
                    }
                ],
            },
        }
        self.requests_mock.post(
            f"{self.JENKINS_URL}/{Jenkins._VALIDATOR_PATH}",
            json=jenkins_response,
        )

        stdout = StringIO()
        with contextlib.redirect_stdout(
            stdout
        ), NamedTemporaryFile() as path, Jenkins(self.JENKINS_URL) as jenkins:
            result = jenkins.lint(Path(path.name))

        self.assertFalse(result)
        self.assertTrue(stdout.getvalue())
        for message in (
            f"{path.name}:4:5: error: Expected a stage",
            f"{path.name}:3:3: error: No stages specified",
        ):
            self.assertIn(message, stdout.getvalue())

    def test_lint_ko_not_jenkinsfile(self) -> None:
        jenkins_response = {
            "status": "ok",
            "data": {
                "result": "failure",
                "errors": [
                    {"error": "unexpected token: default @ line 1, column 2."}
                ],
            },
        }
        self.requests_mock.post(
            f"{self.JENKINS_URL}/{Jenkins._VALIDATOR_PATH}",
            json=jenkins_response,
        )

        stdout = StringIO()
        with contextlib.redirect_stdout(
            stdout
        ), NamedTemporaryFile() as path, Jenkins(self.JENKINS_URL) as jenkins:
            result = jenkins.lint(Path(path.name))

        self.assertFalse(result)
        self.assertTrue(stdout.getvalue())
        self.assertIn(
            f"{path.name}:1:2: error: unexpected token", stdout.getvalue()
        )

    def test_lint_ko_no_pipeline(self) -> None:
        jenkins_response = {
            "status": "ok",
            "data": {
                "result": "failure",
                "errors": [
                    {
                        "error": "Jenkinsfile content 'node {\n\t"
                        "stage('Build') {\n\t\techo \"Building...\"\n\t}\n}"
                        "\n\n ' did not contain the 'pipeline' step"
                    }
                ],
            },
        }
        self.requests_mock.post(
            f"{self.JENKINS_URL}/{Jenkins._VALIDATOR_PATH}",
            json=jenkins_response,
        )

        stdout = StringIO()
        with contextlib.redirect_stdout(
            stdout
        ), NamedTemporaryFile() as path, Jenkins(self.JENKINS_URL) as jenkins:
            result = jenkins.lint(Path(path.name))

        self.assertFalse(result)
        self.assertTrue(stdout.getvalue())
        self.assertIn(
            f"{path.name}:1:1: error: Jenkinsfile did not contain the "
            "'pipeline' step",
            stdout.getvalue(),
        )

    def test_lint_file_not_exists(self) -> None:
        with self.assertRaises(JenkinsError) as context:
            Jenkins(self.JENKINS_URL).lint(Path("/no/file/here"))

        self.assertTrue(isinstance(context.exception.args[0], OSError))

    def test_lint_file_not_text(self) -> None:
        with NamedTemporaryFile() as path:
            path.write(b"\x80")
            path.seek(0)
            with self.assertRaises(JenkinsError) as context:
                Jenkins(self.JENKINS_URL).lint(Path(path.name))

        self.assertTrue(
            isinstance(context.exception.args[0], UnicodeDecodeError)
        )

    @unittest.mock.patch("jenkinsfilelint.jenkins.urllib3.disable_warnings")
    def test_lint_insecure(self, disable_warnings_patch: MagicMock) -> None:
        with Jenkins(
            self.JENKINS_URL,
            username=self.JENKINS_USERNAME,
            password=self.JENKINS_PASSWORD,
            insecure=False,
        ):
            pass

        disable_warnings_patch.assert_not_called()

        with Jenkins(
            self.JENKINS_URL,
            username=self.JENKINS_USERNAME,
            password=self.JENKINS_PASSWORD,
            insecure=True,
        ):
            pass

        disable_warnings_patch.assert_called_once_with(InsecureRequestWarning)
