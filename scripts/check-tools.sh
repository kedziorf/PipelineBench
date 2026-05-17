#!/usr/bin/env bash
set -euo pipefail

missing=0

check_command() {
  local name="$1"
  local hint="$2"

  if command -v "$name" >/dev/null 2>&1; then
    printf "OK   %s: %s\n" "$name" "$("$name" --version 2>/dev/null | head -n 1 || true)"
  else
    printf "MISS %s\n     %s\n" "$name" "$hint"
    missing=1
  fi
}

check_kubectl() {
  if command -v kubectl >/dev/null 2>&1; then
    printf "OK   kubectl: %s\n" "$(kubectl version --client --short 2>/dev/null || kubectl version --client 2>/dev/null | head -n 1 || true)"
  else
    printf "MISS kubectl\n     Install kubectl: https://kubernetes.io/docs/tasks/tools/\n"
    missing=1
  fi
}

check_command docker "Install Docker Desktop and enable WSL2 integration: https://docs.docker.com/desktop/wsl/"
check_command kind "Install kind: https://kind.sigs.k8s.io/docs/user/quick-start/#installation"
check_kubectl
check_command helm "Install Helm: https://helm.sh/docs/intro/install/"
check_command python3 "Install Python 3.12+ in WSL."
check_command curl "Install curl, for example: sudo apt-get install -y curl"
check_command jq "Install jq, for example: sudo apt-get install -y jq"

if command -v python3 >/dev/null 2>&1; then
  python3 - <<'PY'
import sys
version = sys.version_info
if version < (3, 12):
    raise SystemExit(f"MISS python3 version >= 3.12 required, found {version.major}.{version.minor}.{version.micro}")
print(f"OK   python3 version is {version.major}.{version.minor}.{version.micro}")
PY
fi

if [ "$missing" -ne 0 ]; then
  echo "One or more required tools are missing. Install them, then rerun make check-tools."
  exit 1
fi

echo "All required tools were found."
