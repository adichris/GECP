#!/usr/bin/env bash
# Daily housekeeping for an alwaysdata scheduled task:
#   bash ~/gecp/current/deploy/alwaysdata/remote/maintenance.sh
set -euo pipefail
. "$(dirname "$0")/lib.sh"

[ -L "$CURRENT" ] || die "No current release"
log "Clearing expired sessions"
manage "$CURRENT" clearsessions
log "Pruning expired community rate limits"
manage "$CURRENT" cleanup_community_limits
