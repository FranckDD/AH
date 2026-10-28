#!/bin/sh
# Planificateur : supercronic lit la crontab (fuseau TZ=Africa/Douala).
set -eu
exec supercronic -quiet "${CRONTAB:-/app/deploy/scheduler/crontab}"
