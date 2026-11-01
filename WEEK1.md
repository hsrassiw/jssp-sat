# Bàn giao tuần 1 — thành viên 3

## Đã triển khai

- Parser một instance, BOM UTF-8, comment, kiểm tra kích thước/máy/thời gian không âm.
- 162 instance có nguồn và checksum (82 OR-Library + ta01–ta80 từ JSPLIB).
- verify kiểm tra kích thước, giờ bắt đầu nguyên không âm, thứ tự job, không chồng máy. Giữ quy ước ràng buộc thứ tự cặp bước của repo, kể cả bước thời gian 0.
- LB = max(tổng thời gian từng job, tải từng máy).
- ES = tổng tiền tố; LS = horizon - tổng hậu tố, đúng mục 3.2 paper.
- UB: Algorithm 1, mục 3.1 paper được gửi (Nguyen et al., bản compiled 20/10/2026), bỏ công suất. Chọn đều ngẫu nhiên trong các job chưa xong, chèn sớm nhất kể cả khoảng trống giữa các bước, nhiều lượt trong 5 giây, giữ lịch tốt nhất.
- seed=0 mặc định; trials=N là chế độ số lượt cố định dành cho test. Chế độ 5 giây có thể cho UB khác nhau giữa các máy/lần chạy dù cùng seed, do số lượt khác nhau. Trước benchmark chính thức, tuần 2 cần chốt/lưu một bộ lb0/ub0/lịch chung cho từng instance rồi dùng lại cho mọi phương pháp; chưa có cache chính thức trong bản tuần 1.
- run.py chỉ thay dòng gọi upper_bound để thời gian tiền xử lý không chủ động vượt ngân sách còn lại. Tổng time_s vẫn bao gồm tiền xử lý.
- Khung LaTeX cas-sc, có preview PDF; chưa viết kết quả nghiên cứu.

## Cách ghép vào repo đang clone

Giải nén vào thư mục tạm, rồi copy các mục trong gói lên repo hiện tại. Gói không có .git, venv hay license. Không xóa repo hiện tại. Chạy từ thư mục gốc repo:

```powershell
python -m pytest -q
python -m src.common.run data/ft06.txt --method SAT --encoding E2 --strategy incremental --solver cadical
```

Lệnh SAT cần trả OPT,55,55. UB mặc định mất khoảng 5 giây là có chủ ý. Cấu hình Python 3.12 trong README của nhóm vẫn là môi trường dự kiến; test ở môi trường khác không chứng minh tương thích mọi solver.

## Kiểm tra riêng UB

```powershell
python -c "from src.common.data import ft06; from src.common.bounds import upper_bound; from src.common.verify import verify; u,s=upper_bound(ft06()); print('UB:',u,'errors:',verify(ft06(),s))"
```

## Chưa thuộc phạm vi tuần 1

MILP Gurobi/CPLEX, script benchmark hàng loạt có resume, triển khai VM và chạy thực nghiệm chính thức. Các stub solver được giữ nguyên.

## Kiểm chứng trong môi trường làm việc

- 191 test pass (bao gồm 8 test SAT cũ), khoảng 13.44 giây.
- Template biên dịch thành PDF 2 trang bằng XeLaTeX và đã xem hình render cả hai trang.
- Đây là kiểm tra chức năng cục bộ, không phải số liệu benchmark AWS để đưa vào báo cáo.
- Hướng dẫn AWS tham khảo: https://docs.aws.amazon.com/cost-management/latest/userguide/create-cost-budget.html . Xác minh email nhận cảnh báo khi AWS yêu cầu.

Kiểm tra bằng Python 3.12.14: ft06 trả OPT,55,55; lb0=47, ub0=55, 2 lần gọi SAT. Đây là kết quả một lần chạy; greedy theo thời gian có thể thay đổi.
