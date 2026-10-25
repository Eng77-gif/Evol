#!/usr/bin/env bash
# Đóng gói addon thành dist/DauLaDaiLuc.mcaddon (mở file này trên điện thoại/PC để cài vào Minecraft).
set -euo pipefail
cd "$(dirname "$0")/.."
python3 tools/gen_assets.py
rm -rf dist && mkdir -p dist/tmp
(cd addon/DLDL_BP && zip -qr ../../dist/tmp/DLDL_BP.mcpack .)
(cd addon/DLDL_RP && zip -qr ../../dist/tmp/DLDL_RP.mcpack .)
(cd dist/tmp && zip -q ../DauLaDaiLuc.mcaddon DLDL_BP.mcpack DLDL_RP.mcpack)
rm -rf dist/tmp
echo "Đã tạo dist/DauLaDaiLuc.mcaddon"
