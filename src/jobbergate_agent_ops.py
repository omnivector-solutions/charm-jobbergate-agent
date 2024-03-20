"""
JobbergateAgentOps.
"""
import logging
import subprocess
from pathlib import Path
from shutil import copy2, rmtree
from typing import Any, Dict, Optional

logger = logging.getLogger()


class JobbergateAgentOps:
    """Track and perform jobbergate-agent ops."""

    _PACKAGE_NAME = "jobbergate-agent"
    _SYSTEMD_SERVICE_NAME = "jobbergate-agent"
    _SYSTEMD_BASE_PATH = Path("/usr/lib/systemd/system")
    _SYSTEMD_SERVICE_ALIAS = f"{_PACKAGE_NAME}.service"
    _SYSTEMD_SERVICE_FILE = _SYSTEMD_BASE_PATH / _SYSTEMD_SERVICE_ALIAS
    _VENV_DIR = Path("/srv/jobbergate-agent-venv")
    _ENV_DEFAULTS = _VENV_DIR / ".env"
    _PIP_CMD = _VENV_DIR.joinpath("bin", "pip").as_posix()
    _PYTHON_CMD = Path("/opt/python/python3.12/bin/python3.12")
    _CACHE_DIR = Path("/var/cache/jobbergate-agent")

    def __init__(self, charm):
        """Initialize jobbergate-agent-ops."""
        self._charm = charm

    def install(self):
        """Install jobbergate-agent and setup ops."""
        # Create the virtualenv and ensure pip is up to date.
        self._create_venv_and_ensure_latest_pip()
        # Install additional dependencies.
        self._install_extra_deps()
        # Install jobbergate-agent
        self._install_jobbergate_agent()
        # Clear cached data
        self.clear_cache_dir()
        # Provision the jobbergate-agent systemd service.
        self._setup_systemd()

    def upgrade(self, version: str):
        """Upgrade the jobbergate-agent python package."""
        # Clear cached data
        self.clear_cache_dir()
        self._upgrade_jobbergate_agent(version)

    def get_version_info(self):
        """Show version and info about jobbergate-agent."""
        cmd = [self._PIP_CMD, "show", self._PACKAGE_NAME]

        out = subprocess.check_output(cmd, env={}).decode().strip()

        return out

    def configure_env_defaults(self, config_context: Dict[str, Any], header: Optional[str] = None):
        """
        Map charm configs found in the config_context to app settings.

        Map the settings found in the charm's config.yaml to the expected
        settings for the application (including the prefix). Write all settings to the
        configured dot-env file. If the file exists, it should be replaced.
        """
        prefix = "JOBBERGATE_AGENT_"
        with open(self._ENV_DEFAULTS, "w") as env_file:
            if header:
                print(header, file=env_file)
            for key, value in config_context.items():
                mapped_key = key.replace("-", "_").upper()
                print(f"{prefix}{mapped_key}={value}", file=env_file)

            print(f"{prefix}CACHE_DIR={self._CACHE_DIR}", file=env_file)

        # Clear cached data
        self.clear_cache_dir()

    def systemctl(self, operation: str):
        """
        Run systemctl operation for the service.
        """
        cmd = [
            "systemctl",
            operation,
            self._SYSTEMD_SERVICE_NAME,
        ]
        try:
            subprocess.call(cmd)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running {' '.join(cmd)} - {e}")

    def remove(self):
        """
        Remove the things we have created.
        """
        # Stop and disable the systemd service.
        self.systemctl("stop")
        self.systemctl("disable")
        # Remove files and dirs created by this charm.
        if self._SYSTEMD_SERVICE_FILE.exists():
            self._SYSTEMD_SERVICE_FILE.unlink()
        subprocess.call(["systemctl", "daemon-reload"])
        rmtree(self._VENV_DIR.as_posix())

    def _create_venv_and_ensure_latest_pip(self):
        """Create the virtualenv and upgrade pip."""

        # Create the virtualenv
        create_venv_cmd = [
            self._PYTHON_CMD,
            "-m",
            "venv",
            self._VENV_DIR.as_posix(),
        ]
        logger.debug(f"## Creating virtualenv: {create_venv_cmd}")
        subprocess.call(create_venv_cmd, env=dict())
        logger.debug("## jobbergate-agent virtualenv created")

        # Ensure we have the latest pip
        upgrade_pip_cmd = [
            self._PIP_CMD,
            "install",
            "--upgrade",
            "pip",
        ]
        logger.debug(f"## Updating pip: {upgrade_pip_cmd}")
        subprocess.call(upgrade_pip_cmd, env=dict())
        logger.debug("## Pip upgraded")

    def _setup_systemd(self):
        """Provision the jobbergate-agent systemd service."""
        copy2(
            "./src/templates/jobbergate-agent.service",
            self._SYSTEMD_SERVICE_FILE.as_posix(),
        )

        subprocess.call(["systemctl", "daemon-reload"])
        subprocess.call(["systemctl", "enable", "--now", self._SYSTEMD_SERVICE_ALIAS])

    def _install_extra_deps(self):
        """Install additional dependencies."""
        # Install uvicorn and pyyaml
        cmd = [self._PIP_CMD, "install", "uvicorn", "pyyaml"]
        logger.debug(f"## Installing exra dependencies: {cmd}")
        try:
            subprocess.call(cmd, env=dict())
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running {' '.join(cmd)} - {e}")
            raise e

    def _install_jobbergate_agent(self):
        """Install the jobbergate-agent package."""
        cmd = [
            self._PIP_CMD,
            "install",
            "-U",
            self._PACKAGE_NAME,
        ]
        subprocess.call("echo {}".format(cmd).split())
        logger.debug(f"## Installing jobbergate: {cmd}")
        try:
            subprocess.call(cmd, env=dict())
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running {' '.join(cmd)} - {e}")
            raise e

    def _install_jobbergate_addon(self, addon: str):
        """Install the extra packages as jobbergate addons."""
        cmd = [
            self._PIP_CMD,
            "install",
            "-U",
            addon,
        ]
        subprocess.call("echo {}".format(cmd).split())
        logger.debug(f"## Installing jobbergate-addons: {cmd}")
        try:
            subprocess.call(cmd, env=dict())
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running {' '.join(cmd)} - {e}")
            raise e

    def _upgrade_jobbergate_agent(self, version: str):
        """Upgrade the jobbergate-agent python package."""
        cmd = [
            self._PIP_CMD,
            "install",
            "-U",
            f"{self._PACKAGE_NAME}=={version}",
        ]

        try:
            subprocess.call(cmd, env=dict())
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running {' '.join(cmd)} - {e}")
            raise e

    def clear_cache_dir(self) -> str:
        """Clear the cache dir. jobbergate-agent will recreate it on the next run."""

        if self._CACHE_DIR.exists():
            logger.debug(f"Clearing cache dir {self._CACHE_DIR.as_posix()}")
            rmtree(self._CACHE_DIR, ignore_errors=True)
            return "Cache cleared"
        else:
            logger.debug(
                f"Cache dir {self._CACHE_DIR.as_posix()} doesn't exist. Skipping."
            )
            return "Cache dir doesn't exist. Skipping."

    def start_agent(self):
        """Starts the jobbergate-agent"""
        self.systemctl("start")

    def stop_agent(self):
        """Stops the jobbergate-agent"""
        self.systemctl("stop")

    def restart_agent(self):
        """Restart the jobbergate-agent"""
        self.systemctl("restart")
