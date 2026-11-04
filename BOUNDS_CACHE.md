# Cận cố định cho thực nghiệm

## Thay đổi

- `src/common/prepare_bounds.py`: tính mỗi instance một lần, lưu sau từng bài; lần sau bỏ qua bài đã có. `--overwrite` mới tính lại.
- `src/common/bounds_cache.py`: đọc/kiểm tra cache và ghi file an toàn.
- `src/common/run.py`: chỉ đọc lb0/ub0 từ cache, không gọi greedy hay tính LB nữa. Thiếu cận hoặc khác dữ liệu thì ERR, không tự tạo cận mới.
- `data/bounds.json`: cận chung + lịch UB hợp lệ + SHA-256 nội dung instance + seed + thời gian tiền xử lý. Không dùng BKS để tạo cận.
- `tests/test_bounds_cache.py`: kiểm tra dùng lại cận giữa SAT/CP/MIP, phát hiện sai dữ liệu/lịch, resume, overwrite, không tính lại ngầm.

## Sử dụng

Gói này đã chứa cận cho tất cả 162 instance hiện có. Chép nội dung gói vào repo hiện tại. Cả nhóm cần dùng đúng cùng phiên bản `data/bounds.json`.

Nếu cần tạo cận trên máy của bạn (lệnh mặc định bỏ qua bài đã có):

```powershell
python -m src.common.prepare_bounds
```

Tính thêm một bài mới:

```powershell
python -m src.common.prepare_bounds data/new_instance.txt
```

Chủ động tạo lại TOÀN BỘ cận (162 bài x 5 giây, khoảng 13.5 phút cộng overhead):

```powershell
python -m src.common.prepare_bounds --overwrite
```

Sau khi chốt cận, không overwrite giữa các lượt benchmark. Nếu đổi cận, chạy lại toàn bộ cấu hình liên quan để so sánh công bằng.

Chạy solver như trước:

```powershell
python -m src.common.run data/ft06.txt --method SAT --encoding E2 --strategy incremental --solver cadical
```

Có thể chọn bộ cận riêng qua `--bounds-file data/bounds.json`. Hàm `run_one` thêm tham số keyword `bounds_file`, các cách gọi cũ vẫn tương thích.

## Quy ước thời gian mới

`time_s` vẫn đo từ đọc instance đến kết thúc, bao gồm đọc/kiểm tra cache và giải, nhưng KHÔNG bao gồm greedy đã chạy offline. Thời gian chuẩn bị riêng nằm ở `preprocess_time_s` trong JSON; không trừ 5 giây khỏi deadline của solver nữa. Quy ước này khác kế hoạch cũ tính tiền xử lý trong từng lần chạy: ghi rõ trong báo cáo và dùng nhất quán cho tất cả phương pháp. Không gộp CSV cũ và CSV mới để so sánh thời gian.

Bộ cận kèm gói được tạo bằng 8 tiến trình độc lập, mỗi instance có ngân sách greedy 5 giây; đây chỉ là chuẩn bị dữ liệu, không phải đo hiệu năng solver. Chất lượng UB có thể khác khi tạo lại tuần tự. Giá trị sau khi lưu là cố định cho mọi phương pháp. Thời gian chuẩn bị trên môi trường này không dùng làm số liệu thực nghiệm AWS.

Không chạy đồng thời hai lệnh prepare ghi chung một file. Cache phân biệt nội dung instance bằng hash, chấp nhận cùng dữ liệu qua tên hoặc đường dẫn; hai instance khác nội dung nhưng cùng tên bị từ chối nếu không overwrite.

## Kiểm tra trên Windows

```powershell
$testTemp = Join-Path $env:TEMP ("jssp-tests-" + [guid]::NewGuid().ToString("N"))
python -m pytest -q --basetemp="$testTemp"
```

Kiểm chứng: 202 test pass; đã kiểm tra hash và lịch UB của toàn bộ 162 instance.
