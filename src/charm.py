#!/usr/bin/env python3
"""ClusterAgentCharm."""
import logging
from pathlib import Path

from ops.charm import CharmBase
from ops.framework import StoredState
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus, WaitingStatus

from cluster_agent_ops import ClusterAgentOps


logger = logging.getLogger()

# Create a sentinel value. For more information about sentinel values and their
# purpose, see the PEP (with some excellent examples and rationale) here:
# https://peps.python.org/pep-0661/
unset = object()


class ClusterAgentCharm(CharmBase):
    """Facilitate Cluster-agent lifecycle."""

    stored = StoredState()

    def __init__(self, *args):
        """Initialize and observe."""
        super().__init__(*args)

        self.stored.set_default(installed=False)
        self.stored.set_default(config_available=False)
        self.stored.set_default(user_created=False)

        self.cluster_agent_ops = ClusterAgentOps(self)

        event_handler_bindings = {
            self.on.install: self._on_install,
            self.on.upgrade_charm: self._on_upgrade,
            self.on.start: self._on_start,
            self.on.config_changed: self._on_config_changed,
            self.on.remove: self._on_remove,
            self.on.upgrade_action: self._on_upgrade_action,
            self.on.clear_cache_dir_action: self._on_clear_cache_dir_action,
            self.on.show_version_action: self._on_show_version_action,
        }
        for event, handler in event_handler_bindings.items():
            self.framework.observe(event, handler)

    def _on_install(self, event):
        """Install cluster-agent."""
        self.unit.set_workload_version(Path("version").read_text().strip())

        try:
            self.cluster_agent_ops.install()
            self.stored.installed = True
        except Exception as e:
            logger.error(f"## Error installing agent: {e}")
            self.stored.installed = False
            self.unit.status = BlockedStatus("Error installing cluster-agent")
            event.defer()
            return
        # Log and set status
        logger.debug("cluster-agent installed")
        self.unit.status = WaitingStatus("cluster-agent installed")

    def _on_upgrade(self, event):
        """Perform upgrade operations."""
        self.unit.set_workload_version(Path("version").read_text().strip())

    def _on_show_version_action(self, event):
        """Show the info and version of ovs-cluster-agent."""
        info = self.cluster_agent_ops.get_version_info()
        event.set_results({"ovs-cluster-agent": info})

    def _on_start(self, event):
        """
        Start cluster-agent.

        Check that we have the needed configuration values and whether the
        cluster agent user is created in the slurmctld node, if so
        start the cluster-agent otherwise defer the event.
        """
        if not self.stored.config_available:
            event.defer()
            return

        logger.info("## Starting Cluster agent")
        self.cluster_agent_ops.start_agent()
        self.unit.status = ActiveStatus("cluster agent started")

    def _on_config_changed(self, event):
        """
        Handle changes to the charm config.

        If all the needed settings are available in the charm config, create the
        environment settings for the charmed app. Also, store the config values in the
        stored state for the charm.

        Note the use of the sentinel ``unset`` value here. This allows us to
        distinguish between *unset* values and values that were *explicitly* set to
        falsey or null values. For more information about sentinel values, see
        `PEP-661 <https://peps.python.org/pep-0661/>_`.
        """

        settings_to_map = {
            "base-api-url": True,
            "base-slurmrestd-url": True,
            "slurm-restd-version": False,
            "slurmrestd-jwt-key-path": False,
            "slurmrestd-jwt-key-string": False,
            "slurmrestd-use-key-path": True,
            "sentry-dsn": False,
            "oidc-domain": True,
            "oidc-audience": True,
            "oidc-client-id": True,
            "oidc-client-secret": True,
            "slurm-user-mapper": False,
            "ldap-domain": False,
            "ldap-username": False,
            "ldap-password": False,
            "ldap-auth-type": False,
            "x-slurm-user-name": True,
        }

        if not self.model.config.get(
            "slurmrestd-jwt-key-path", None
        ) and not self.model.config.get("slurmrestd-jwt-key-string", None):
            logger.warn(
                "Either slurmrestd-jwt-key-path or slurmrestd-jwt-key-string must be configured"
            )
            event.defer()

        if self.model.config.get(
            "slurmrestd-jwt-key-path", None
        ) and self.model.config.get("slurmrestd-jwt-key-string", None):
            logger.warn(
                "ALERT! Both slurmrestd-jwt-key-path and slurmrestd-jwt-key-string were configured. "
                "Prioritizing the slurmrestd-jwt-key-string config."
            )
            self.model.config.update({"slurmrestd-use-key-path": False})

        env_context = dict()

        for setting, is_required in settings_to_map.items():
            value = self.model.config.get(setting, unset)

            # If any config value is not yet available, defer
            if value is unset:
                if is_required:
                    event.defer()
                    return
            else:
                env_context[setting] = value

                mapped_key = setting.replace("-", "_")
                store_value = getattr(self.stored, mapped_key, unset)
                if store_value != value:
                    setattr(self.stored, mapped_key, value)

        self.cluster_agent_ops.configure_env_defaults(env_context)
        self.stored.config_available = True

        logger.info("## Restarting Cluster agent")
        self.cluster_agent_ops.restart_agent()
        self.unit.status = ActiveStatus("cluster agent restarted")

    def _on_remove(self, event):
        """Remove directories and files created by cluster-agent charm."""
        self.cluster_agent_ops.remove()

    def _on_upgrade_action(self, event):
        version = event.params["version"]
        try:
            self.cluster_agent_ops.upgrade(version)
            event.set_results({"upgrade": "success"})
            self.unit.status = ActiveStatus(f"Updated to version {version}")
        except Exception:
            self.unit.status = BlockedStatus(f"Error updating to version {version}")
            event.fail()

    def _on_clear_cache_dir_action(self, event):
        try:
            result = self.cluster_agent_ops.clear_cache_dir()
            event.set_results({"cache-clear": "success"})
            self.unit.status = ActiveStatus(result)
        except Exception:
            self.unit.status = BlockedStatus("Error clearing cache")
            event.fail()


if __name__ == "__main__":
    main(ClusterAgentCharm)
