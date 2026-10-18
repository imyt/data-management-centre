#!/bin/sh
# Writes /config.json from the environment (ADR 0004 §4). Empty DMC_API_BASE_URL means the API is
# same-origin under /api/, which is what the proxy in default.conf.template serves.
set -eu
printf '{"apiBaseUrl": "%s"}\n' "${DMC_API_BASE_URL:-}" > /usr/share/nginx/html/config.json
