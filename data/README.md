# Dữ liệu tuần 1

- 82 instance gốc (ft, la, orb, abz, swv, yn): https://people.brunel.ac.uk/~mastjjb/jeb/orlib/files/jobshop1.txt
- 80 instance ta01–ta80: bản OR-Library-format tại https://github.com/tamy0612/JSPLIB (instances/).
- Trang mô tả nguồn: https://people.brunel.ac.uk/~mastjjb/jeb/orlib/jobshopinfo.html
- Ngày tải: 2026-10-31 (Asia/Ho_Chi_Minh). SHA-256 từng file trong checksums.csv.
- reference_metadata.json giữ metadata của JSPLIB tại thời điểm tải, không cam kết là BKS mới nhất.
- bks.csv: bks là optimum nếu nguồn có chứng nhận; nếu chưa có, dùng bounds.upper. Cột reference_status phân biệt OPTIMAL / UPPER_BOUND. Không dùng một cận trên để kết luận solver đã chứng minh tối ưu.
- Các cặp máy/thời gian giữ nguyên từ nguồn, máy đánh số từ 0. orb07 chứa một bước thời gian 0; parser cho phép thời gian không âm.

Mỗi file: dòng đầu n_jobs n_machines; mỗi dòng sau là một job gồm các cặp machine duration.

Tách lại bản OR-Library tổng hợp:

```powershell
python scripts/import_orlibrary.py DUONG_DAN/jobshop1.txt --output data
```

Chạy bằng tên `la01` hoặc đường dẫn `data/la01.txt`. Riêng `ft06` dùng dữ liệu nhúng theo khung cũ; dùng `data/ft06.txt` để thử parser.

Các instance chưa có mốc số trong snapshot metadata: ta71, ta72, ta73, ta74, ta75, ta76, ta77, ta78, ta79, ta80. Không tự điền giá trị hoặc dùng kết quả heuristic làm BKS.
