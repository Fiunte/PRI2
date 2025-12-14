# Solr Docker Compose Setup

This setup uses Docker Compose to automatically launch a standalone Solr instance, create the `drugs` core, apply the schema, and load initial data.

## Prerequisites

1. **Docker & Docker Compose:** Must be installed and running.

2. **Required Files:**

   * `docker-compose.yml`

   * `fields.json`

   * `data.json`

## **Important!: Data File Check**

Your `data.json` file is very large and tracked by Git LFS. **The setup will fail if the file is an LFS pointer.**

* **Action:** Ensure `data.json` contains the full JSON data, not the pointer text (`version https://git-lfs...`).

* If you have Git LFS installed, run `git lfs pull` before starting.

## Quick Start

1. To launch and set up Solr:

  ```docker compose up```

(The setup container will automatically exit once data loading is complete.)

2. Access Solr Admin UI:

  `http://localhost:8983/solr`

## Cleanup

To stop and remove all containers, networks, and the indexed Solr data (recommended for clean restarts):

  ```docker compose down -v```
