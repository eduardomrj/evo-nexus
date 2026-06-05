#!/bin/bash
# Starts google workspace-mcp with credentials from .env
set -a
source "$(dirname "$0")/../.env"
set +a
exec uvx workspace-mcp --single-user "$@"
