# Khung báo cáo tuần 1

Dùng lớp Elsevier cas-sc chính thức, nguồn:
https://ctan.org/pkg/els-cas-templates

Các file cas-sc.cls, cas-common.sty, cas-model2-names.bst là bản upstream, giữ nguyên. Xem ELSEVIER_README.txt và manifest.txt; gói đầy đủ: https://mirrors.ctan.org/macros/latex/contrib/els-cas-templates.zip

## Biên dịch

Upload toàn bộ thư mục report lên Overleaf, chọn **XeLaTeX**, main document **main.tex**. Hoặc trên máy có TeX Live/MiKTeX và font DejaVu:

```
cd report
xelatex -interaction=nonstopmode -halt-on-error main.tex
xelatex -interaction=nonstopmode -halt-on-error main.tex
```

Đây là KHUNG, chưa phải báo cáo hoàn chỉnh. Các đoạn [Cần bổ sung] chỉ rõ phần của từng người. Không có số liệu thực nghiệm AWS giả định. main.pdf là bản xem trước đã biên dịch.
