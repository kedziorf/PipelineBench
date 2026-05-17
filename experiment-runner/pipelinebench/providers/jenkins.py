from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from html import escape
from typing import Any
from urllib.parse import urlparse

import requests

from pipelinebench.config import CISystemSettings, PipelineBenchConfig
from pipelinebench.providers.base import CICDProvider

LOGGER = logging.getLogger(__name__)


@dataclass
class JenkinsProvider(CICDProvider):
    config: PipelineBenchConfig
    system: CISystemSettings

    def __post_init__(self) -> None:
        self.base_url = os.getenv("JENKINS_URL", "http://localhost:8080").rstrip("/")
        self.user = os.getenv("JENKINS_USER", "admin")
        self.token = os.getenv("JENKINS_API_TOKEN", "")
        self.job_name = os.getenv("JENKINS_JOB_NAME", "pipelinebench-sample")
        self.session = requests.Session()
        if self.token:
            self.session.auth = (self.user, self.token)

    def deploy(self) -> None:
        LOGGER.info("Ensuring Jenkins benchmark job exists")
        self.wait_until_ready()
        if not self.token:
            LOGGER.warning("JENKINS_API_TOKEN is not set; skipping automatic Jenkins job creation")
            return
        self._ensure_job()

    def wait_until_ready(self) -> None:
        deadline = time.time() + self.config.experiment.timeout_seconds
        while time.time() < deadline:
            try:
                response = self.session.get(f"{self.base_url}/login", timeout=10)
                if response.status_code < 500:
                    LOGGER.info("Jenkins responded with status %s", response.status_code)
                    return
            except requests.RequestException as exc:
                LOGGER.info("Waiting for Jenkins: %s", exc)
            time.sleep(5)
        raise TimeoutError("Jenkins did not become ready before timeout")

    def trigger_pipeline(self, run_id: int) -> str:
        if not self.token:
            raise RuntimeError("Set JENKINS_API_TOKEN to trigger Jenkins jobs through the API")

        queue_before = self._latest_queue_id()
        url = f"{self.base_url}/job/{self.job_name}/buildWithParameters"
        headers = {}
        crumb = self._get_crumb()
        if crumb:
            headers[crumb["crumbRequestField"]] = crumb["crumb"]
        response = self.session.post(url, data={"RUN_ID": str(run_id)}, headers=headers, timeout=20)
        if response.status_code not in {200, 201, 302}:
            raise RuntimeError(f"Failed to trigger Jenkins job: HTTP {response.status_code} {response.text[:300]}")

        location = response.headers.get("Location")
        if location and "/queue/item/" in location:
            return location.rstrip("/").split("/")[-1]
        return str(self._wait_for_new_queue_id(queue_before))

    def wait_for_pipeline(self, pipeline_id: str) -> str:
        executable = self._wait_for_executable(pipeline_id)
        build_number = executable["number"]
        build_url = self._external_url(executable["url"])
        deadline = time.time() + self.config.experiment.timeout_seconds

        while time.time() < deadline:
            data = self._get_json(f"{build_url}api/json")
            if not data.get("building", False):
                return str(data.get("result") or "UNKNOWN")
            time.sleep(5)

        raise TimeoutError(f"Jenkins build {build_number} timed out")

    def collect_logs(self, pipeline_id: str, output_path: str) -> None:
        executable = self._wait_for_executable(pipeline_id)
        console_url = f"{self._external_url(executable['url'])}consoleText"
        response = self.session.get(console_url, timeout=30)
        response.raise_for_status()
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(response.text)

    def cleanup(self) -> None:
        LOGGER.info("Jenkins provider cleanup is limited to benchmark-generated records in the MVP")

    def _get_json(self, url: str) -> dict[str, Any]:
        response = self.session.get(url, timeout=20)
        response.raise_for_status()
        return response.json()

    def _ensure_job(self) -> None:
        jenkinsfile = (self.config.base_dir.parent / "pipelines" / "jenkins" / "Jenkinsfile").read_text(
            encoding="utf-8"
        )
        config_xml = self._job_config_xml(jenkinsfile)
        headers = {"Content-Type": "application/xml"}
        crumb = self._get_crumb()
        if crumb:
            headers[crumb["crumbRequestField"]] = crumb["crumb"]

        job_url = f"{self.base_url}/job/{self.job_name}/api/json"
        existing = self.session.get(job_url, timeout=20)
        if existing.status_code == 404:
            response = self.session.post(
                f"{self.base_url}/createItem",
                params={"name": self.job_name},
                data=config_xml,
                headers=headers,
                timeout=30,
            )
        else:
            response = self.session.post(
                f"{self.base_url}/job/{self.job_name}/config.xml",
                data=config_xml,
                headers=headers,
                timeout=30,
            )
        if response.status_code not in {200, 201, 302}:
            raise RuntimeError(f"Could not create/update Jenkins job: HTTP {response.status_code} {response.text[:300]}")

    def _get_crumb(self) -> dict[str, str] | None:
        response = self.session.get(f"{self.base_url}/crumbIssuer/api/json", timeout=20)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def _job_config_xml(self, script: str) -> str:
        return f"""<?xml version='1.1' encoding='UTF-8'?>
<flow-definition plugin="workflow-job">
  <actions/>
  <description>PipelineBench Jenkins benchmark job</description>
  <keepDependencies>false</keepDependencies>
  <properties>
    <hudson.model.ParametersDefinitionProperty>
      <parameterDefinitions>
        <hudson.model.StringParameterDefinition>
          <name>RUN_ID</name>
          <description>PipelineBench run id</description>
          <defaultValue>0</defaultValue>
          <trim>false</trim>
        </hudson.model.StringParameterDefinition>
      </parameterDefinitions>
    </hudson.model.ParametersDefinitionProperty>
  </properties>
  <definition class="org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition" plugin="workflow-cps">
    <script>{escape(script)}</script>
    <sandbox>true</sandbox>
  </definition>
  <triggers/>
  <disabled>false</disabled>
</flow-definition>
"""

    def _external_url(self, url: str) -> str:
        parsed = urlparse(url)
        if parsed.hostname in {"pipelinebench-jenkins", "pipelinebench-jenkins.pipelinebench-jenkins"}:
            return f"{self.base_url}{parsed.path}"
        return url

    def _latest_queue_id(self) -> int:
        data = self._get_json(f"{self.base_url}/queue/api/json")
        ids = [int(item["id"]) for item in data.get("items", []) if "id" in item]
        return max(ids, default=0)

    def _wait_for_new_queue_id(self, queue_before: int) -> int:
        deadline = time.time() + 60
        while time.time() < deadline:
            latest = self._latest_queue_id()
            if latest > queue_before:
                return latest
            time.sleep(1)
        raise TimeoutError("Could not find Jenkins queue item for triggered build")

    def _wait_for_executable(self, queue_id: str) -> dict[str, Any]:
        deadline = time.time() + 120
        queue_url = f"{self.base_url}/queue/item/{queue_id}/api/json"
        while time.time() < deadline:
            data = self._get_json(queue_url)
            executable = data.get("executable")
            if executable:
                return executable
            time.sleep(2)
        raise TimeoutError(f"Jenkins queue item {queue_id} did not start")
