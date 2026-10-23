# UML phần game ôn tập (Edu_game)

Tài liệu này gồm 2 phần:
- **Phần A:** cách biến UML thành text rồi đưa vào Mermaid / PlantUML.
- **Phần B:** bộ 4 sơ đồ của phần game (use case, class, sequence, state) kèm đặc tả use case.

Đặt file này vào `docs/` trong repo. GitHub tự vẽ các khối ```` ```mermaid ```` khi mở file `.md`.

> Lưu ý trung thực: các sơ đồ dưới đây chưa được render thử trong lúc soạn. Hãy dán từng khối vào
> **mermaid.live** (Mermaid) hoặc **plantuml.com/plantuml** (PlantUML), kiểm tra, chụp ảnh làm bằng chứng.
> **Trạng thái đã đối chiếu code:** `FillBlankGame`, `MatchingGame`, `EnglishQuizGame` có thật; luồng hiện thực bằng `server.py` + `FLOW_STATE`, không có class `GameFlow` hay biến `GAME_ORDER`. Final Test được dựng bằng `games.final_test.build_final_quiz()` và chấm qua `EnglishQuizGame`, không có class `FinalTest` riêng. **Fill Blank được chốt dùng chọn phương án, không gõ đáp án.**

---

# PHẦN A. Biến UML thành text rồi đưa vào Mermaid

## A1. Ý tưởng

UML là sơ đồ (hình). "Viết UML bằng text" nghĩa là **mô tả sơ đồ bằng vài dòng chữ theo cú pháp riêng**,
rồi công cụ tự vẽ ra hình. Ba lý do nên làm vậy:

1. Agent (Copilot, Cursor, Claude) đọc text chính xác, còn ảnh thì phải đoán.
2. File text lưu được trong Git, xem được `git diff` khi sơ đồ thay đổi.
3. Sửa một dòng là sơ đồ đổi, không phải vẽ lại.

## A2. Quy trình 6 bước

```
(1) Thu thập thông tin  ->  (2) Chọn loại sơ đồ  ->  (3) Viết text
        |                                                 |
   từ Planning                                      (4) Dán vào công cụ xem
 (đối tượng, tính năng,                                   |
  quan hệ, API)                                    (5) Chỉnh cho đúng ý
                                                          |
                                                   (6) Lưu .mmd/.md + commit
```

| Bước | Việc làm | Ví dụ |
|---|---|---|
| 1 | Liệt kê thông tin cần vẽ | "Người chơi chọn đáp án, giao diện gọi `check_one`" |
| 2 | Chọn loại sơ đồ theo câu hỏi cần trả lời | Hỏi "hàm nào gọi hàm nào" -> sequence |
| 3 | Viết text theo cú pháp (bảng ở A3) | `UI->>G: check_one(qid, idx)` |
| 4 | Dán vào mermaid.live | Thấy hình hiện ngay bên phải |
| 5 | Sửa lỗi cú pháp, đổi tên cho khớp code | So lại với tên hàm trong file `.py` |
| 6 | Lưu vào `docs/` và commit | `docs/04-sequence-choi-game.mmd` |

## A3. Chọn loại sơ đồ

| Câu hỏi cần trả lời | Loại UML | Công cụ |
|---|---|---|
| Ai dùng hệ thống, làm được gì? | Use case | **PlantUML** (Mermaid không có use case chuẩn) |
| Có class/hàm nào, liên hệ ra sao? | Class diagram | Mermaid `classDiagram` |
| Một thao tác đi qua hàm nào, theo thứ tự nào? | Sequence diagram | Mermaid `sequenceDiagram` |
| Hệ thống có những trạng thái nào, chuyển ra sao? | State diagram | Mermaid `stateDiagram-v2` |
| Các bảng dữ liệu liên quan nhau thế nào? | ERD | Mermaid `erDiagram` |

## A4. Bảng dịch "ký hiệu UML -> dòng text"

**Class diagram (Mermaid)**

| Ý muốn diễn đạt | Viết text |
|---|---|
| Khai báo class | `class EnglishQuizGame { }` |
| Hàm public | `+check_one(id, chosen)` |
| Thuộc tính | `+order list` |
| Hàm có kiểu trả về | `+result() dict` |
| Liên kết (A dùng B) | `A --> B` |
| Phụ thuộc (A chỉ đọc B) | `A ..> B : mô tả` |
| Kế thừa | `Cha <\|-- Con` |
| Gồm (thành phần) | `A *-- B` |

**Sequence diagram (Mermaid)**

| Ý muốn diễn đạt | Viết text |
|---|---|
| Người dùng | `actor P as Người ôn bài` |
| Thành phần hệ thống | `participant UI as Giao diện` |
| Gọi hàm | `UI->>G: check_one(qid, idx)` |
| Trả kết quả | `G-->>UI: đúng/sai` |
| Tự gọi chính mình | `S->>S: so sánh` |

**State diagram (Mermaid)**

| Ý muốn diễn đạt | Viết text |
|---|---|
| Trạng thái đầu / cuối | `[*] --> Game1`, `Summary --> [*]` |
| Chuyển trạng thái | `Game1 --> Game2 : xong game 1` |

## A5. Ví dụ biến câu mô tả thành text

**Mô tả bằng lời:**
> Người chơi chọn đáp án. Giao diện gửi cho game. Game trả đúng hoặc sai. Hết câu thì giao diện hỏi kết quả.

**Chuyển từng câu thành một dòng:**

```
Người chơi chọn đáp án.            ->  P->>UI: Chọn đáp án
Giao diện gửi cho game.            ->  UI->>G: check_one(qid, idx)
Game trả đúng hoặc sai.            ->  G-->>UI: đúng/sai
Hết câu thì giao diện hỏi kết quả. ->  UI->>G: result()
```

**Ghép lại thành sơ đồ hoàn chỉnh:**

````
```mermaid
sequenceDiagram
    actor P as Người ôn bài
    participant UI as Giao diện
    participant G as FillBlankGame
    P->>UI: Chọn đáp án
    UI->>G: check_one(qid, idx)
    G-->>UI: đúng/sai
    UI->>G: result()
```
````

Mẹo: mỗi câu mô tả chứa một "ai làm gì với ai" thì thành đúng một dòng.

## A6. Cách đưa vào Mermaid (3 cách)

| Cách | Làm thế nào | Dùng khi |
|---|---|---|
| **mermaid.live** | Mở https://mermaid.live, dán text vào ô bên trái, hình hiện bên phải. Bấm Actions để tải PNG/SVG | Kiểm tra nhanh, lấy ảnh dán vào báo cáo Word |
| **Trong file `.md` trên GitHub** | Bọc text trong khối ```` ```mermaid ```` ... ```` ``` ````; GitHub tự vẽ | Lưu tài liệu trong repo |
| **VS Code** | Cài extension hiển thị Mermaid trong Markdown Preview (tìm "Mermaid" trong Extensions), mở Preview | Viết và xem ngay trong editor |

Với file chỉ chứa sơ đồ, dùng đuôi `.mmd` và dán nội dung (không cần dòng ```` ```mermaid ````) vào mermaid.live.

**PlantUML (dùng cho use case):** dán code giữa `@startuml` và `@enduml` vào https://www.plantuml.com/plantuml,
hoặc dùng extension PlantUML trong VS Code. Lưu ý: Mermaid **không** vẽ được code PlantUML, hai công cụ riêng.

## A7. Dùng Agent để viết text, và những lỗi hay gặp

**Prompt mẫu:**
> Đây là mô tả luồng chơi game: [dán mô tả]. Hãy chuyển thành Mermaid `sequenceDiagram`, dùng đúng tên class/hàm
> trong `games/fill_blank.py`. Chỉ trả về code Mermaid, không giải thích.

Sau đó **bạn tự dán vào mermaid.live kiểm tra** và đối chiếu tên hàm với code thật; Agent có thể bịa tên hàm.

| Lỗi thường gặp | Cách sửa |
|---|---|
| Hình không hiện, báo lỗi cú pháp | Kiểm tra dòng đầu có đúng `classDiagram`, `sequenceDiagram`, `stateDiagram-v2` |
| Lỗi do ký tự đặc biệt trong nhãn | Bỏ hoặc đổi ký tự lạ; thử đặt nhãn trong dấu nháy kép |
| Tên có khoảng trắng | Dùng alias: `participant UI as Giao diện` |
| Sơ đồ khác code | Sửa tên cho đúng code, đừng để code chạy khác sơ đồ |

---

# PHẦN B. Bộ UML của phần game

## B1. Use case (PlantUML, ký hiệu chuẩn UML)

```plantuml
@startuml
left to right direction
actor "Người ôn bài" as P

rectangle "Hệ thống game ôn tập" {
  usecase "Chơi game điền chỗ trống" as UC1
  usecase "Chơi game nối từ" as UC2
  usecase "Chơi game trắc nghiệm" as UC3
  usecase "Làm bài kiểm tra cuối" as UC4
  usecase "Xem điểm" as UC5
  usecase "Ôn lại câu sai" as UC6
  usecase "Chấm điểm" as UCa
  usecase "Kiểm tra game trước đã xong" as UCb
}

P --> UC1
P --> UC2
P --> UC3
P --> UC4
P --> UC5
P --> UC6

UC1 .> UCa : <<include>>
UC2 .> UCa : <<include>>
UC3 .> UCa : <<include>>
UC4 .> UCa : <<include>>
UC2 .> UCb : <<include>>
UC3 .> UCb : <<include>>
UC4 .> UCb : <<include>>
UC6 .> UC5 : <<extend>>
@enduml
```

**Phiên bản Mermaid để GitHub tự vẽ** (chỉ tương đương về ý nghĩa, không phải ký hiệu UML chuẩn):

```mermaid
flowchart LR
    P[Người ôn bài]
    P --> U1((Chơi điền chỗ trống))
    P --> U2((Chơi nối từ))
    P --> U3((Chơi trắc nghiệm))
    P --> U4((Làm bài kiểm tra cuối))
    P --> U5((Xem điểm))
    P --> U6((Ôn lại câu sai))
    U1 -. include .-> V1((Chấm điểm))
    U2 -. include .-> V1
    U3 -. include .-> V1
    U4 -. include .-> V1
    U2 -. include .-> V2((Kiểm tra game trước đã xong))
    U3 -. include .-> V2
    U4 -. include .-> V2
    U6 -. extend .-> U5
```

### Đặc tả use case "Chơi game điền chỗ trống"

| Mục | Nội dung |
|---|---|
| Tác nhân | Người ôn bài |
| Tiền điều kiện | Có các `items` Fill Blank hợp lệ (ít nhất 2 đáp án phân biệt, mỗi `sentence` có một `___`); game này là bước đầu, không yêu cầu hoàn thành game trước |
| Luồng chính | 1. Server tạo 2–4 lựa chọn từ các đáp án trong bộ câu hỏi. 2. Hệ thống hiển thị câu có chỗ trống. 3. Người chơi **chọn** một phương án. 4. Server chấm theo `qid`/`idx` và phản hồi đúng/sai. 5. Hết câu thì hiện `score/total`. |
| Luồng thay thế | Dữ liệu sai cấu trúc: hiện lỗi thân thiện. Bấm kết thúc khi chưa trả lời hết: nhắc trả lời hết. |
| Hậu điều kiện | Có thể lấy kết quả `{score, total, wrong}` sau khi trả lời hết các câu; server cập nhật `FLOW_STATE` khi gọi `/api/fill_blank/result` của ván chính |

### Đặc tả use case "Làm bài kiểm tra cuối" (đã tích hợp demo)

| Mục | Nội dung |
|---|---|
| Tác nhân | Người ôn bài |
| Tiền điều kiện | Đã hoàn thành cả 3 game |
| Luồng chính | 1. Dùng câu của ba game trong cùng chương, tối đa 30; nếu vượt thì lấy ngẫu nhiên đều, không ép tỷ lệ. 2. Fill Blank/Matching chuyển thành Quiz với 2–4 lựa chọn; Quiz gốc giữ bốn lựa chọn. 3. Chấm theo `score` = số câu đúng; điểm thang 10 = `10 × score / total`. 4. Hiện kết quả và danh sách câu sai có `source_game`/`source_id`. |
| Luồng thay thế | Chưa xong game nào: nút bị khóa. |
| Hậu điều kiện | Kết quả được giữ trong bộ nhớ của server demo và dùng cho trang tổng kết; trạng thái chưa được lưu lâu dài. |

## B2. Class diagram (Mermaid) — phần **đã có trong code**

Sơ đồ tập trung vào ba class game thật. `server.py` là module điều phối, không phải class `GameFlow`. `MatchingGame.check()` trả kết quả ngay, không có `MatchingGame.result()` trong bản hiện tại.

```mermaid
classDiagram
    class FillBlankGame {
        +public_view() dict
        +check_one(qid, idx) dict
        +result() dict
    }
    class MatchingGame {
        +public_view() dict
        +check(pairs) dict
    }
    class EnglishQuizGame {
        +public_view() dict
        +check_one(qid, idx) dict
        +result() dict
    }
```

**Phần thiết kế chưa triển khai:** class `GameFlow` và danh sách `GAME_ORDER`. Final Test được dựng bởi `games.final_test.build_final_quiz()` rồi chấm qua `EnglishQuizGame`; không có class `FinalTest` riêng.

## B3. Sequence diagram: chơi **Fill Blank hiện tại** (Mermaid)

```mermaid
sequenceDiagram
    actor P as Người ôn bài
    participant UI as web/fill_blank.html
    participant S as server.py
    participant G as FillBlankGame

    P->>UI: Mở Fill Blank
    UI->>S: POST /api/fill_blank/new
    S->>G: FillBlankGame(items)
    G-->>S: public_view() với lựa chọn đã xáo
    S-->>UI: game_id, questions và options (không đánh dấu đúng)
    UI-->>P: Câu có chỗ trống, 2–4 lựa chọn
    P->>UI: Chọn một phương án
    UI->>S: POST /api/fill_blank/check (game_id, qid, idx)
    S->>G: check_one(qid, idx)
    G-->>S: ok, correct_idx, correct_text
    S-->>UI: Phản hồi sau khi chấm
    P->>UI: Hoàn thành tất cả câu
    UI->>S: POST /api/fill_blank/result
    S->>G: result()
    G-->>S: score, total, wrong, review
    S->>S: FLOW_STATE.fill_blank_done = true (ván chính)
    S-->>UI: Kết quả, nút Tiếp tục
```

## B4. State diagram: trạng thái mở khóa (Mermaid)

**Hiện tại:** server dùng các cờ trong `FLOW_STATE` để mở khóa ba game, Final Test và tổng kết.

```mermaid
stateDiagram-v2
    [*] --> FillBlank
    FillBlank --> Matching : result() đã hoàn thành
    Matching --> Quiz : check() đã hoàn thành
    Quiz --> FinalTest : result() đã hoàn thành
    FinalTest --> Summary : result() đã hoàn thành
    Summary --> [*]
```

Danh sách cấu hình `GAME_ORDER` và random thứ tự là **định hướng giai đoạn 2**, chưa có trong code. Trạng thái server hiện là biến toàn cục phù hợp demo một người dùng, không phải session đa người dùng.

---

## Checklist trước khi nộp

- [ ] Mỗi khối Mermaid/PlantUML đã dán vào công cụ và hiển thị đúng
- [ ] Tên class và hàm trong sơ đồ khớp với code thật (hoặc ghi rõ "dự kiến")
- [ ] Đã chụp ảnh từng sơ đồ làm bằng chứng
- [ ] Các file lưu trong `docs/` và đã commit
- [ ] Báo cáo ghi rõ thứ tự game: giai đoạn 1 tuần tự, giai đoạn 2 random
