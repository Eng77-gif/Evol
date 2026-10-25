# Đấu La Đại Lục — Addon Minecraft Bedrock (PE) 26.50

Addon theo chủ đề *Đấu La Đại Lục*: thức tỉnh võ hồn, săn hồn thú, hấp thu hồn hoàn, thi triển hồn kỹ và dung hợp hồn cốt.

## Cài đặt
1. Tải `dist/DauLaDaiLuc.mcaddon`, mở bằng Minecraft (hoặc giải nén vào `behavior_packs` / `resource_packs`).
2. Tạo/sửa thế giới → bật **cả Behavior Pack và Resource Pack** "Đấu La Đại Lục".
3. Yêu cầu Minecraft Bedrock 1.21.120 trở lên (đã nhắm tới 26.50), Script API `@minecraft/server` 2.4.0 — không cần bật Beta APIs.

## Cách chơi
| Vật phẩm | Công dụng | Cách có |
|---|---|---|
| Thủy Tinh Thức Tỉnh | Thức tỉnh ngẫu nhiên 1 võ hồn + tiên thiên hồn lực 1–10 | Tặng khi vào game; chế: 4 thạch anh tím quanh 1 kim cương |
| Võ Hồn Lệnh | Dùng = thi triển hồn kỹ đang chọn; ngồi + dùng = menu | Tặng khi vào game; chế: 3 vàng, 1 lưu ly, 1 gậy |
| Hồn Hoàn 10 → 100.000 năm | Hấp thu làm hồn hoàn (mở hồn kỹ mới) | Rơi từ hồn thú |
| Hồn Cốt | Hiệu ứng vĩnh viễn (6 bộ phận) | Hồn thú vạn năm (8%), 10 vạn năm (35%) |
| Tiên Thảo | Hồi đầy hồn lực, tăng mạnh kinh nghiệm | Phá cỏ (1%), hồn thú ≥ 1.000 năm (15%) |

**Võ hồn** (mỗi võ hồn có 9 hồn kỹ riêng): Lam Ngân Thảo, Hạo Thiên Chùy, Thất Bảo Lưu Ly Tháp, Bạch Hổ, Tà Hỏa Phượng Hoàng, Lam Điện Bá Vương Long.

**Tu luyện**: giết quái, hoặc ngồi (sneak) đứng yên để minh tưởng. Cứ mỗi 10 cấp là một bình cảnh — phải hấp thu hồn hoàn mới đột phá.
Danh hiệu: Hồn Sĩ → Hồn Sư → Đại Hồn Sư → Hồn Tôn → Hồn Tông → Hồn Vương → Hồn Đế → Hồn Thánh → Hồn Đấu La → Phong Hào Đấu La → Thần (cấp 100).

**Hồn thú**: 30% zombie, skeleton, nhện, sói, gấu, enderman, ravager, hoglin, blaze… xuất hiện thành hồn thú với niên hạn ngẫu nhiên (thuộc tính tăng theo niên hạn; hồn thú ≥ 1.000 năm có vòng hào quang màu). Nhìn vào quái khi cầm Võ Hồn Lệnh để xem niên hạn.

**Giới hạn hồn hoàn** (như nguyên tác): hoàn 1 ≤ 100 năm, hoàn 2–3 ≤ 1.000 năm, hoàn 4–6 ≤ 10.000 năm, hoàn 7–9 ≤ 100.000 năm. Vượt 1 bậc có 30% thành công (Tiên Thiên Mãn Hồn Lực: 50%), thất bại sẽ bị trọng thương.

**Lệnh**: `/dld:hoso` (mở hồ sơ), `/dld:pvp` (OP – bật hồn kỹ đánh người chơi), `/dld:reset` (OP), `/dld:setlevel <cấp>` (OP).

## Phát triển
- `addon/DLDL_BP` — behavior pack (item, công thức, script `scripts/main.js`, dữ liệu `scripts/data.js`).
- `addon/DLDL_RP` — resource pack (texture, hạt hồn hoàn, tên tiếng Việt).
- `tools/gen_assets.py` sinh item JSON/texture/hạt; `tools/build.sh` đóng gói `.mcaddon`.
