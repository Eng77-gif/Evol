# AlienEvo cho Minecraft Bedrock (MCPE) 26.50

Bản chuyển đổi của mod **AlienEvo 1.1.3** (Fabric/Java, tác giả Habb và Stephen; mod này cần Palladium và KubeJS)
sang **add-on Bedrock** (Behavior Pack + Resource Pack) chạy trên **Minecraft Bedrock / MCPE 26.50**.
Bản này gộp thêm alien, model, texture và animation từ 6 addon của AlienEvo:

| Addon | Tác giả | Thêm |
|---|---|---|
| Into The Omniverse 1.0.6 | AWildCanOfBeans | Echo Echo, Big Chill (Omniverse) |
| Omni Extras 1.0.7.3 | Hibiquill | Eye Guy, Upchuck (Perk), Upchuck (Murk), Armodrillo, Water Hazard, Ampfibian, Buzzshock |
| The Anur Trio 1.0.4 | AWildCanOfBeans | Benwolf, Frankenstrike |
| Wildvine 1.0.3 | Babish_q | Wildvine |
| Aliens Untapped 1.3.5 | Jaijorlon | Chamalien, Walkatrout, Ditto, Eatle |
| Chromastone 1.9 | godday | Model và animation mới của Chromastone |

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
| Chọn alien (vòng xoay như phim) | **Dùng** Omnitrix (bấm giữ / chuột phải) → đồng hồ mở ra, **hologram 3D xanh** của alien hiện lên trước mặt và người chơi đứng yên. **Quay góc nhìn sang trái/phải** (hoặc nút trái/phải) để xoay vòng chọn sang alien trước/sau. **Dùng lần nữa hoặc nhảy** để ấn lõi xuống và biến hình; **ngồi** để đóng. Tự đóng sau 20 giây không thao tác. **Ngồi + dùng** biến ngay thành alien đã chọn lần trước. |
| Menu đầy đủ | **Ngồi hai lần liên tiếp** (khi cầm/đeo Omnitrix) mở menu dạng danh sách: chọn alien, Playlist, Alien Codex, nhập mã. |
| Đeo Omnitrix | Để Omnitrix ở **tay trái (offhand)**: đồng hồ luôn hiện trên cổ tay. **Ngồi hai lần liên tiếp** để mở vòng chọn alien (khi là alien: mở menu kỹ năng). |
| Dùng kỹ năng | Khi đang là alien: **dùng Omnitrix** để tung kỹ năng đang chọn; **ngồi + dùng** để mở menu kỹ năng (chọn kỹ năng, hoặc *Detransform*). |
| Bay | Alien biết bay (Stinkfly, Ghostfreak, Jetray, Big Chill, Atomix, Dragonoid): **nhấn nhảy hai lần** khi đang ở trên không. Nhảy = lên, ngồi = xuống, đi tới = bay theo hướng nhìn. |
| Leo tường | Wildmutt, Grey Matter: đi thẳng vào tường. |
| Hẹn giờ | Mỗi lần biến hình kéo dài 5 phút (như bản gốc). Hết giờ thì Omnitrix sạc lại 2 phút 30 giây. **Master Control** bỏ giới hạn thời gian. |
| Nâng cấp | Đặt **Omnitrix Workbench**, cầm Omnitrix rồi bấm vào bàn: Prototype → Phase 1 → Phase 2 → Evolved (10k). Mỗi cấp mở khóa thêm alien; cấp 10k mở Master Control. |
| Tùy chỉnh màu đồng hồ | Cầm Omnitrix, bấm vào **Bàn chế tạo Omnitrix** → *Customize colours*. Đổi màu cho 9 bộ phận (đế chính, đế phụ, đế thứ ba, nút, lõi cạnh, lõi trên, vòng trong, vòng ngoài, ống) và màu phát sáng. Mỗi lần đổi tốn 1 Omni Crystal cùng màu; *Default* thì miễn phí. Màu được lưu theo người chơi và người chơi khác cũng thấy. |
| Công trình | Khi tạo **thế giới mới**, các công trình của mod tự sinh: tàu vũ trụ rơi (có Lõi Omnitrix), Galvan Pod, mỏ Galvan, tu viện Galvan, tháp, giếng, hầm nổ và pháo đài ngầm của Machine, cùng công trình của các addon (sọ Loboan, xác tàu Talpaedan, tàu Xylene, tháp Galvan đổ nát, phòng thí nghiệm bỏ hoang, nhà tù ngoài hành tinh). Có thể đặt thử bằng `/alienevo:structure <tên>`. |
| Giơ đồng hồ (góc nhìn thứ nhất) | Khi mở vòng xoay hoặc nhập mã, **tay trái giơ lên trước mặt** cho thấy đồng hồ như video, mặt đồng hồ xoay theo từng nấc. Mặt đồng hồ hiện **hình bóng (silhouette)** của alien đang chọn / đang biến (ảnh gốc của mod). |
| Mã Omnitrix | Mỗi người chơi có mã **Master Control** và **Self Destruct** 6 chữ số (riêng từng người). **Code Tablet** lộ 1 chữ số mỗi tablet. Nhập mã: ngồi 2 lần → *Enter code* → đồng hồ chuyển sang chế độ cài đặt, hiện `§e0§r 0 0 0 0 0` trên thanh hành động. **Quay góc nhìn trái/phải** (hoặc nút trái/phải) để vặn mặt đồng hồ đổi chữ số đang sáng, **nhảy / dùng** sang chữ số kế, **ngồi** để thoát. Mã được kiểm tra liên tục như bản gốc: đúng Master Control → bật (nhập lại thì tắt); đúng Self Destruct → đếm ngược 10 giây rồi nổ. |
| Mã biến hình (Aliens Untapped) | **Code Tablet (Transformation)** cho mã 6 số của một alien. Nhập mã đó trên đồng hồ → **thêm DNA** alien đó (mặt đồng hồ hiện hình bóng của nó); nhập lại → gỡ DNA. Có từ Machine Husk (10%). **Incomplete Code Tablet** (Galvan Pod 5%, Galvan Scientist cấp 5 đổi bằng Galvan Pod): đang là **Grey Matter**, cầm tablet tay phải và Galvan Circuit tay trái rồi dùng → Blank Code Tablet; với **Primus Link Circuit** (Machine Husk Priest 5%) → Code Tablet (Transformation). Blank tablet + Code Tablet trên bàn chế tạo → nhân đôi tablet. |
| Galvan Scientist | Dân Galvan nhỏ (3 kiểu da, mắt phát sáng) hiếm gặp trên mặt đất. Bấm vào để **giao dịch** bằng emerald: 4 cấp như bản gốc (Omni Shards, Omni Crystals, Galvan Scrap, quặng), mỗi cấp 2 giao dịch ngẫu nhiên; cấp cao đổi Galvan Scrap lấy Machine Key / Machine Urn. Sợ Machine. |
| Machine | **Machine Husk**, **Machine Husk Priest** và **Machine Drone** xuất hiện dưới lòng đất nơi tối và trong spawner của pháo đài Machine; rơi đồ theo loot table gốc. |
| Cây kỹ năng | Mỗi alien có sẵn 2 kỹ năng đầu. Kỹ năng còn lại bị khoá; mở bằng **điểm kỹ năng** (mỗi lần alien lên cấp được 1 điểm) trong menu kỹ năng. |
| Cấp độ alien | Hạ quái khi đang là alien để nhận XP (công thức gốc: 42,5% máu tối đa của quái). Mỗi cấp (tối đa 10) giảm 3% thời gian hồi chiêu. |

### Danh sách alien

| Tier | Alien |
|---|---|
| Prototype | Heatblast, Wildmutt, Diamondhead, XLR8, Grey Matter, Four Arms, Stinkfly, Ripjaws, Upgrade, Ghostfreak |
| Phase 1 | Cannonbolt, Swampfire, Echo Echo, Humungousaur, Eye Guy, Upchuck (Perk), Water Hazard, Benwolf, Wildvine, Walkatrout, Ditto |
| Phase 2 | Jetray, Big Chill, Chromastone, Atomix, Upchuck (Murk), Armodrillo, Ampfibian, Buzzshock, Frankenstrike, Chamalien |
| Evolved (10k) | Dragonoid, Astro Bot, Eatle, Echo Echo (Omniverse), Big Chill (Omniverse) |

Tổng cộng 36 alien, 79 kỹ năng. Mỗi alien dùng đúng model và texture lấy từ mod gốc hoặc addon. Alien có hiệu ứng bị động riêng
(sức mạnh, tốc độ, kháng lửa/băng/điện, thở dưới nước…) và từ 2 đến 4 kỹ năng (cầu lửa, gai pha lê, dậm đất, ném đá tảng,
tia mắt, nuốt và nhả năng lượng, khoan đất, vòi nước, sét, tiếng hú siêu âm, tàng hình, ăn khối…).

### Model 3D

![Xem trước 36 alien](docs/aliens_preview.png)

Ảnh trên được dựng bằng `tools/render.py` từ chính file của Resource Pack, đúng như game sẽ vẽ ở tư thế nghỉ.

- Model GeckoLib được gắn vào khung xương người chơi (đầu, thân, tay, chân), nên alien cử động theo người chơi.
- Bộ phận chỉ xuất hiện khi dùng kỹ năng (kiếm và khiên của Diamondhead, gai và chùy của Upgrade, vỏ của Cannonbolt)
  được ẩn khi nghỉ và chỉ bật ra cùng animation kỹ năng.
- Kích thước alien lấy từ kỹ năng `size_change` trong power của bản Java, ví dụ Grey Matter ×0.25, Four Arms ×2,
  Humungousaur ×2.8. Mức lớn nhất là ×3 để camera vẫn dùng được.
- Ở góc nhìn thứ nhất, tay phải của alien thay cho tay của Steve.

### Animation

Animation GeckoLib của mod và các addon đã được chuyển sang animation Bedrock:

- **Animation lặp** (đuôi, cánh, thở, bay lơ lửng…) chạy liên tục trên model alien.
- **Animation kỹ năng** (cắn, bắn tia mắt, cuộn tròn, hóa lỏng, gai tay, hú, khoan, trượt…) chạy khi dùng kỹ năng tương ứng.
- **Texture động**: lửa của Heatblast cháy nhấp nháy (8 khung hình như bản Java).
- **Animation di chuyển**: alien tự đổi tư thế khi bay (Stinkfly, Jetray, Big Chill, Dragonoid), bơi (Ripjaws, Walkatrout)
  và chạy nhanh (Benwolf). Tay chân alien luôn cử động theo người chơi khi đi, chạy, nhảy.
- **Omnitrix 3D trên cổ tay**: khi cầm Omnitrix, đồng hồ GeckoLib hiện trên cổ tay trái (góc nhìn thứ ba). Khi dùng,
  mặt đồng hồ bật lên, xoay tới alien đã chọn rồi đập xuống trước khi biến hình như bản Java.
Xem chi tiết trong **Alien Codex** (nằm trong menu Omnitrix).

### Lệnh (cần quyền OP / cheat)

```
/alienevo:transform <alien> [người chơi]   biến hình ngay
/alienevo:detransform [người chơi]         trở lại người
/alienevo:unlock <alien|all> [người chơi]  mở khóa DNA alien bất kể tier
/alienevo:mastercontrol <true|false>       bật/tắt Master Control
/alienevo:recharge [người chơi]            sạc Omnitrix ngay
/alienevo:unlockskills <true|false>        mở toàn bộ kỹ năng của mọi alien
/alienevo:structure <tên>                  đặt một công trình tại chỗ đứng
/alienevo:revealcode [người chơi]          hiện mã Master Control / Self Destruct
```

## Khác biệt so với bản Java

Bedrock không hỗ trợ một số thứ mà Palladium/GeckoLib làm được, nên những phần sau đã được đơn giản hóa:

- **Công trình**: 14 file `.nbt` của Java được chuyển sang `.mcstructure` (bảng ánh xạ khối Java→Bedrock của minecraft-data,
  bản Bedrock 1.26.30). Các công trình ghép bằng jigsaw (tàu rơi, pháo đài Machine) được ghép sẵn thành một khối.
  Spawner Husk trong công trình được đổi sang Machine Husk; chữ trên biển và hoa văn cờ bị mất.
- **Không có phím tắt riêng**: các phím của Palladium được thay bằng thao tác dùng Omnitrix, menu, và nhấn nhảy hai lần.
- **Animation**: tay chân alien vẫn cử động theo động tác của người chơi; animation GeckoLib (đuôi, cánh, kỹ năng) được thêm lên trên.
  Một số animation của bản Java gắn với trạng thái riêng của Palladium (đổi dạng, tư thế đứng yên đặc biệt) chưa được dùng.
  Kích thước alien được mô phỏng bằng cách co giãn khung xương người chơi; hitbox thì không đổi.
- **Ditto** không tách thành bản sao thật; kỹ năng *Clone Swarm* mô phỏng các bản sao tấn công kẻ địch xung quanh.
- **Tùy chỉnh màu** chỉ áp dụng cho đồng hồ; alien vẫn dùng màu mặc định của bản *Prototype*.
- **Galvan Scientist** là một entity riêng (Bedrock không cho thêm nghề cho dân làng vanilla); bảng giao dịch giữ nguyên giá/số lượt/XP của bản gốc. Vài giao dịch dùng vật phẩm chỉ có ở addon khác không có trong gói (`aeo:completed_core_blueprint`, `untapped:broken_code_tablet`) bị bỏ.
- **Nhập mã**: bản Java dùng 3 phím (đổi vị trí, tăng, giảm chữ số); ở Bedrock vặn bằng cách quay góc nhìn / nút trái phải, nhảy để sang chữ số kế. Tư thế giơ tay góc nhìn thứ nhất dựa trên tư thế cầm bản đồ tay trái của Bedrock nên góc tay có thể hơi khác video. Tablet biến hình chọn alien ngẫu nhiên khi đọc lần đầu (bản Java ghi sẵn alien trong NBT). Primus Link Circuit rơi từ Machine Husk Priest vì mob Volaticus Biopsis chưa được chuyển.
- **Hologram**: là một thực thể nhỏ bay trước mặt người chơi (Bedrock không vẽ được hình nổi gắn trên đồng hồ ở góc nhìn thứ nhất); dùng model alien tô xanh, không dùng 32 model hologram riêng của bản Java (chỉ có cho một phần alien).
- **Giao diện**: các màn hình riêng của Palladium (power screen, thanh kỹ năng có ảnh nền riêng) không thể tạo lại trên Bedrock nếu không sửa JSON UI của game; dùng form của Script API (vòng chọn alien, menu kỹ năng, Codex, Workbench) với icon và màu như bản gốc.
- `palladium:raw_titanium` không có trên Bedrock nên được thay bằng `iron_ingot` trong các công thức.

## Cấu trúc repo

```
packs/AlienEvo_BP/   Behavior Pack (item, block, recipe, entity, feature, scripts/)
packs/AlienEvo_RP/   Resource Pack (texture, model, attachable, sound, lang)
tools/build_packs.py Script chuyển đổi: đọc file .jar → sinh lại texture/model/sound/item/block/recipe rồi đóng gói .mcaddon
dist/AlienEvo.mcaddon File cài đặt
```

Muốn build lại từ các file jar gốc thì chạy lệnh sau (cần Python 3 và Pillow):

```
python3 tools/build_packs.py AlienEvo-1.1.3-fabric.jar IntoTheOmniverse-v1.0.6.jar omni-extras1.0.7.3.jar \
    anur-v1.0.4.jar Wildvine1.0.3.jar AliensUntapped-1.3.5.jar chromastone-1.9_FIX_JAR.jar
python3 tools/validate.py   # kiểm tra mọi tham chiếu giữa các file của pack
```

Code gameplay nằm trong `packs/AlienEvo_BP/scripts/` và được viết tay. Script build không ghi đè các file này.

## Bản quyền

Toàn bộ tài nguyên (model, texture, animation, âm thanh) thuộc về tác giả gốc của AlienEvo (Habb và Stephen) và tác giả
các addon nêu ở trên (giấy phép *All Rights Reserved*).
Bản chuyển đổi này chỉ dành cho mục đích cá nhân. Không phân phối lại nếu chưa được tác giả gốc cho phép.
