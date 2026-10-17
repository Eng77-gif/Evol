# AlienEvo cho Minecraft Bedrock (MCPE) 26.50

Bản chuyển đổi của mod **AlienEvo 1.1.3** (Fabric/Java, tác giả Habb và Stephen; mod này cần Palladium và KubeJS)
sang **add-on Bedrock** (Behavior Pack + Resource Pack) chạy trên **Minecraft Bedrock / MCPE 26.50**.

Bedrock không chạy được file `.jar` của Java, nên mod được viết lại theo hệ thống add-on của Bedrock:
model GeckoLib → attachable của Bedrock, Palladium/KubeJS → Script API (`@minecraft/server` 2.10.0, `@minecraft/server-ui` 2.2.0).

## Cài đặt

1. Tải [`dist/AlienEvo.mcaddon`](dist/AlienEvo.mcaddon) về máy và mở file (hoặc giải nén vào thư mục `games/com.mojang`).
2. Khi tạo thế giới (hoặc trong cài đặt thế giới), bật **cả hai** pack: `AlienEvo BP` và `AlienEvo RP`.
3. Không cần bật thử nghiệm (Experiments): add-on chỉ dùng API ổn định của bản 26.50.

> Resource Pack ghi đè `player.entity.json` để ẩn thân người chơi khi đã biến hình. Nếu dùng chung với add-on khác cũng sửa
> người chơi, hãy đặt AlienEvo RP lên trên cùng.

## Cách chơi

| Việc | Cách làm |
|---|---|
| Tìm nguyên liệu | Tìm **Galvan Pod** (khối kim loại) trên mặt đất hoặc chôn dưới đá. Bấm vào pod để mở: rơi ra Galvan Scrap, Omni Shards/Crystals, Galvan Circuit. Hiếm hơn có **Prototype Omnitrix Core**, Code Tablet, đôi khi có luôn Omnitrix. |
| Chế tạo Omnitrix | `Galvan Circuit` ở 4 góc, `Galvan Plate` ở 4 cạnh, `Prototype Omnitrix Core` ở giữa (công thức gốc). |
| Chọn alien | Dùng (bấm giữ / chuột phải) Omnitrix → hiện vòng chọn alien. Bấm **ngồi + dùng** để biến ngay thành alien đã chọn lần trước. |
| Dùng kỹ năng | Khi đang là alien: **dùng Omnitrix** để tung kỹ năng đang chọn; **ngồi + dùng** để mở menu kỹ năng (chọn kỹ năng, hoặc *Detransform*). |
| Bay | Alien biết bay (Stinkfly, Ghostfreak, Jetray, Big Chill, Atomix, Dragonoid): **nhấn nhảy hai lần** khi đang ở trên không. Nhảy = lên, ngồi = xuống, đi tới = bay theo hướng nhìn. |
| Leo tường | Wildmutt, Grey Matter: đi thẳng vào tường. |
| Hẹn giờ | Mỗi lần biến hình kéo dài 5 phút (như bản gốc). Hết giờ thì Omnitrix sạc lại 2 phút 30 giây. **Master Control** bỏ giới hạn thời gian. |
| Nâng cấp | Đặt **Omnitrix Workbench**, cầm Omnitrix rồi bấm vào bàn: Prototype → Phase 1 → Phase 2 → Evolved (10k). Mỗi cấp mở khóa thêm alien; cấp 10k mở Master Control. |
| Code Tablet | *Master Control*: dùng để mở Master Control. *Self Destruct*: đếm ngược 10 giây rồi nổ lớn (phá khối). |
| Cấp độ alien | Hạ quái khi đang là alien để nhận XP (công thức gốc: 42,5% máu tối đa của quái). Mỗi cấp (tối đa 10) giảm 3% thời gian hồi chiêu. |

### Danh sách alien

| Tier | Alien |
|---|---|
| Prototype | Heatblast, Wildmutt, Diamondhead, XLR8, Grey Matter, Four Arms, Stinkfly, Ripjaws, Upgrade, Ghostfreak |
| Phase 1 | Cannonbolt, Swampfire, Echo Echo, Humungousaur |
| Phase 2 | Jetray, Big Chill, Chromastone, Atomix |
| Evolved (10k) | Dragonoid, Astro Bot |

Mỗi alien dùng đúng model và texture lấy từ mod gốc. Alien có hiệu ứng bị động riêng (sức mạnh, tốc độ, kháng lửa hoặc kháng băng,
thở dưới nước…) và từ 2 đến 4 kỹ năng (cầu lửa, phun lửa, gai pha lê, dậm đất, ném đá tảng, chất nhờn, tia năng lượng, cuộn tròn, thét siêu âm…).
Xem chi tiết trong **Alien Codex** (nằm trong menu Omnitrix).

### Lệnh (cần quyền OP / cheat)

```
/alienevo:transform <alien> [người chơi]   biến hình ngay
/alienevo:detransform [người chơi]         trở lại người
/alienevo:unlock <alien|all> [người chơi]  mở khóa DNA alien bất kể tier
/alienevo:mastercontrol <true|false>       bật/tắt Master Control
/alienevo:recharge [người chơi]            sạc Omnitrix ngay
```

## Khác biệt so với bản Java

Bedrock không hỗ trợ một số thứ mà Palladium/GeckoLib làm được, nên những phần sau đã được đơn giản hóa:

- **Không có cấu trúc (structure)**: file `.nbt` của Java không đọc được trên Bedrock. Thay vào đó, Galvan Pod được rải sẵn khi sinh thế giới
  (cần **thế giới mới** hoặc vùng chưa khám phá). Pod cho cùng loại loot với bản gốc.
- **Không có phím tắt riêng**: các phím của Palladium được thay bằng thao tác dùng Omnitrix, menu, và nhấn nhảy hai lần.
- **Model alien không có animation riêng**: alien cử động theo động tác của người chơi. Không có animation tấn công riêng của GeckoLib.
  Kích thước alien được mô phỏng bằng cách co giãn khung xương người chơi; hitbox thì không đổi.
- **Không có tùy chỉnh màu**: không có Color Module và palette màu. Alien dùng màu mặc định của bản *Prototype*.
- Mob Machine/Galvan villager, villager profession và trade của bản gốc không được chuyển.
- `palladium:raw_titanium` không có trên Bedrock nên được thay bằng `iron_ingot` trong các công thức.

## Cấu trúc repo

```
packs/AlienEvo_BP/   Behavior Pack (item, block, recipe, entity, feature, scripts/)
packs/AlienEvo_RP/   Resource Pack (texture, model, attachable, sound, lang)
tools/build_packs.py Script chuyển đổi: đọc file .jar → sinh lại texture/model/sound/item/block/recipe rồi đóng gói .mcaddon
dist/AlienEvo.mcaddon File cài đặt
```

Muốn build lại từ file jar gốc thì chạy lệnh sau (cần Python 3 và Pillow):

```
python3 tools/build_packs.py AlienEvo-1.1.3-fabric.jar
```

Code gameplay nằm trong `packs/AlienEvo_BP/scripts/` và được viết tay. Script build không ghi đè các file này.

## Bản quyền

Toàn bộ tài nguyên (model, texture, âm thanh) thuộc về tác giả gốc của AlienEvo (Habb và Stephen; giấy phép *All Rights Reserved*).
Bản chuyển đổi này chỉ dành cho mục đích cá nhân. Không phân phối lại nếu chưa được tác giả gốc cho phép.
