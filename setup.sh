#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SFINCS_BIN_PATH="$(realpath "$SCRIPT_DIR/flood_adapt/system/linux-64/sfincs/bin/sfincs")"
FIAT_BIN_PATH="$(realpath "$SCRIPT_DIR/flood_adapt/system/linux-64/fiat/fiat")"
export SFINCS_BIN_PATH FIAT_BIN_PATH

echo "Set SFINCS_BIN_PATH to $SFINCS_BIN_PATH"
echo "Set FIAT_BIN_PATH to $FIAT_BIN_PATH"
