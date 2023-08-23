# charm-jobbergate-agent

# Usage

Follow the steps below to get started.

### Build the charm

Running the following command will produce a .charm file, `jobbergate-agent.charm`

```bash
charmcraft build
```

### Create the jobbergate-agent charm config

`jobbergate-agent.yaml`

```yaml
jobbergate-agent:
  api-key: "<backend api-key>"
  backend-url: "<backend-url>"
  aws-access-key-i: "<aws-access-key-i>"
  aws-secret-access-key: "<aws-secret-access-key>"
```

e.g.

```yaml
jobbergate-agent:
  backend-url: https://armada-k8s-staging.omnivector.solutions
  api-key: GJGXBnzhyt8zKiVV5s9sW9pONOBa4sTW2VUd0VPK
  aws-access-key-id: ABCDEFGHIJKLMN
  aws-secret-access-key: g3iyVyBPo93k8RwBNCW4r6T7tst0TaO5+928i4vt
```

### Deploy the charm

Using the built charm and the defined config, run the command to deploy the charm.

```bash
juju deploy ./jobbergate-agent.charm \
    --config ./jobbergate-agent.yaml \
    --series centos7
```

### Release the charm

To make a new release of the jobbergate-agent charm:

1. Update the CHANGELOG.rst file, moving the changes under the Unreleased section to the new version section. Always keep an `Unreleased` section at the top.
2. Create a new commit with the title `Release x.y.z`
3. Create a new annotated Git tag, adding a summary of the changes in the tag message:

  ```bash
  git tag --annotate --sign x.y.z
  ```

4. Push the new tag to GitHub:

  ```bash
  git push --tags
  ```

### Charm Actions

The jobbergate-agent charm exposes additional functionality to facilitate jobbergate-agent
package upgrades.

To upgrade the jobbergate-agent to a new version or release:

```bash
juju run-action jobbergate-agent/leader upgrade version="7.7.7"
```

This will result in the jobbergate-agent package upgrade to 7.7.7.

```bash
juju run-action jobbergate-agent/leader upgrade version="7.7.7"
```

Manually triggers the cleaning of jobbergate-agent's cache dir:

```bash
juju run-action jobbergate-agent/leader clear-cache-dir
```

#### License

* MIT (see `LICENSE` file in this directory for full preamble)
