<!-- markdownlint-disable -->
![Infrahub Logo](https://assets-global.website-files.com/657aff4a26dd8afbab24944b/657b0e0678f7fd35ce130776_Logo%20INFRAHUB.svg)
<!-- markdownlint-restore -->

# Infrahub by OpsMill

[Infrahub](https://github.com/opsmill/infrahub) by [OpsMill](https://opsmill.com) acts as a central hub to manage the data, templates and playbooks that powers your infrastructure. At its heart, Infrahub is built on 3 fundamental pillars:

- **A Flexible Schema**: A model of the infrastructure and the relation between the objects in the model, that's easily extensible.
- **Version Control**: Natively integrated into the graph database which opens up some new capabilities like branching, diffing, and merging data directly in the database.
- **Unified Storage**: By combining a graph database and git, Infrahub stores data and code needed to manage the infrastructure.

## Infrahub - Demo repository for IXPs

This repository is demoing the key Infrahub features for an example service provider with IXP peerings.

## Personal fork

If you want to be able to make change to this repository, it is recommended to create a fork of this repository.
Changes can be merged into the upstream repository using the pull request workflow.

## Using Github CodeSpaces

To have a consistent user experience, independent of hardware resources, we recommend the usage of Github CodeSpaces.

- Click the green `Code` button
- Switch to the `Codespaces` tab
- Click the `+ to the right of Codespaces` (or click the `...` button and select `New with options` to be able to select your region)

## Using the demo environment

### Installing dependencies on your PC

We recommend that you use a dedicated virtual environment.
The easiest way is to leverage `poetry`.

```sh
poetry install --no-root
```

### Prerequisites

Define and export the following environment variables:

```bash
export INFRAHUB_PRODUCTION=false
export INFRAHUB_IMAGE_NAME=infrahub
export INFRAHUB_SECURITY_SECRET_KEY=327f747f-efac-42be-9e73-999f08f86b92
export INFRAHUB_SDK_API_TOKEN=06438eb2-8019-4776-878c-0941b1f1d1ec
export INFRAHUB_SDK_TIMEOUT=20
export INFRAHUB_METRICS_PORT=8001
export INFRAHUB_DB_TYPE=neo4j
export INFRAHUB_SECURITY_INITIAL_ADMIN_TOKEN=06438eb2-8019-4776-878c-0941b1f1d1ec
export INFRAHUB_CONTAINER_REGISTRY=9r2s1098.c1.gra9.container-registry.ovh.net
export INFRAHUB_VERSION=0.13.0
export DATABASE_DOCKER_IMAGE="neo4j:5.19-community"
export CACHE_DOCKER_IMAGE="redis:7.2"
export MESSAGE_QUEUE_DOCKER_IMAGE="rabbitmq:3.12-management"
```

### Spin up IXP demo environment

```sh
invoke start
```

### Load the initial schema

```sh
invoke load-schema
```

### Load data into the environment

```sh
invoke load-data
```

### Stop the IXP demo environment

```sh
invoke stop
```

### Stop and destroy the IXP demo environment

```sh
invoke destroy
```
