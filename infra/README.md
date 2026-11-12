# EC2 Windows cho thực nghiệm JSSP

Môi trường mục tiêu: Windows Server 2025 Base, x86-64, EC2 r6i.xlarge (4 vCPU, 32 GiB RAM). Mỗi solver chạy 1 luồng, mỗi cấu hình tối đa 600 giây, chạy tuần tự trên cùng VM. Ghi lại AMI, phiên bản Windows/Python/solver và commit thực tế trong báo cáo.

VM được tạo thủ công trong AWS Console. Không cần triển khai CloudFormation cho máy đã có. Template Ubuntu cũ `ec2-jssp.yaml` được loại bỏ bằng `scripts/cleanup_obsolete.ps1`.

## Kết nối và cài đặt

1. Trong EC2 Console, chọn instance đang Running, dùng Connect > RDP client để lấy thông tin kết nối Windows. Security group cho phép TCP 3389 từ IP của người thực hiện.
2. Trên VM, cài Git và Python 64-bit. Python 3.12 là môi trường kiểm thử ban đầu. Clone repo nhóm; không chép `.venv` từ laptop sang VM.
3. Cài CPLEX Optimization Studio 22.2.0 bản Windows đầy đủ bằng bộ cài được cấp phép. Ghi lại thư mục gốc chứa cả `cplex` và `cpoptimizer`. Không dùng bộ cài Linux `.bin`.
4. Trong PowerShell ở thư mục repo, chạy lệnh sau. Thay đường dẫn ví dụ bằng thư mục Studio thực tế trên EC2 (thư mục chứa cả `cplex` và `cpoptimizer`):

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1 -CplexStudioDir "C:\Program Files\IBM\ILOG\CPLEX_Studio2220"
```

Script tạo môi trường mới bằng Python 3.12 nếu chưa có `.venv`, cài `requirements.txt` rồi nâng cấp runtime CPLEX. Gurobi và CPLEX phải được kiểm tra trong chính `.venv` dùng để chạy thực nghiệm. Đường dẫn cài trên laptop không tự tồn tại trên EC2.

## Gurobi WLS

Chép `gurobi.lic` vào `%USERPROFILE%` trên VM. Không commit file này. Nếu để nơi khác, đặt `GRB_LICENSE_FILE` tới đường dẫn file đó. WLS cần Internet. Kiểm tra:

```powershell
.\.venv\Scripts\python.exe scripts/check_solvers.py --full --solvers gurobi
```

## CPLEX MIP và CP Optimizer

`pip install cplex` cung cấp runtime Community. `setup.ps1 -CplexStudioDir ...` gọi `docplex config --upgrade` để sử dụng runtime Studio đã cài, rồi thử bài MIP 1101 biến. Có phiên bản trong banner không đủ chứng minh đã hết giới hạn.

CPLEX MIP dùng package `cplex`. CPLEX CP dùng `docplex.cp` và `cpoptimizer.exe`. Script thêm `<Studio>\cpoptimizer\bin\x64_win64` vào PATH của tài khoản hiện tại nếu file tồn tại. Mở lại PowerShell/VS Code sau khi chạy script.

Kiểm tra CP Optimizer độc lập với adapter JSSP:

```powershell
Get-Command cpoptimizer.exe
.\.venv\Scripts\python.exe -c "from docplex.cp.model import CpoModel; m=CpoModel(); x=m.integer_var(0,1); m.add(x==1); s=m.solve(Workers=1,TimeLimit=10); assert s.is_solution(); print('CP Optimizer OK')"
```

Adapter `src/cp/cplex_cp.py` của nhóm phải dùng executable tìm qua PATH hoặc cấu hình theo máy; không gán cứng đường dẫn ổ D của một thành viên. Nếu adapter còn stub thì phải ghép phần triển khai của nhóm trước khi chạy JSSP bằng CPLEX CP. Bài kiểm tra CP nhỏ ở trên chỉ xác nhận kết nối engine.

Kiểm tra runtime CPLEX MIP đầy đủ và thử adapter JSSP:

```powershell
.\.venv\Scripts\python.exe scripts/check_solvers.py --full --solvers cplex
.\.venv\Scripts\python.exe -m src.common.run la21 --method MIP --solver cplex --time-limit 30
# Chỉ chạy sau khi đã ghép adapter CPLEX CP của nhóm.
.\.venv\Scripts\python.exe -m src.common.run la21 --method CP --solver cplex --time-limit 30
```

FEAS/NOSOL do hết thời gian không tự chứng minh lỗi license. Nếu ERR, đọc log để xác định lỗi; lỗi giới hạn kích thước cho thấy runtime chưa đáp ứng yêu cầu. Không cài lại package `cplex` sau khi nâng cấp runtime; nếu phải cài lại, chạy lại bước nâng cấp và kiểm tra.

## Chạy và kết thúc phiên

Trước tiên thử batch E2 và CP-SAT trên `ft06` trong 30 giây mỗi cấu hình:

```powershell
.\.venv\Scripts\python.exe -m src.common.batch --instances ft06 --methods SAT CP --encodings E2 --cp-solvers cpsat --time-limit 30 --csv results/smoke.csv
```

Sau khi các adapter và solver đều hoạt động, ví dụ chạy E2, CP-SAT, CPLEX CP, Gurobi MIP và CPLEX MIP trên ba instance:

```powershell
.\.venv\Scripts\python.exe -m src.common.batch --instances ft06 la01 la02 --methods SAT CP MIP --encodings E2 --cp-solvers cpsat cplex --mip-solvers gurobi cplex --time-limit 600 --csv results/aws.csv
```

Danh sách ba instance trên chỉ là ví dụ; thay bằng danh sách đã thống nhất trong kế hoạch. Dùng cùng commit, dependency và bộ cận. Chạy lại đúng lệnh và CSV sẽ bỏ qua task hoàn tất theo cơ chế resume; không đổi cấu hình hay mã nguồn giữa một lượt resume. Nếu thay đổi, dùng tên CSV mới.

Giữ thư mục `results` gồm CSV, manifest và logs để đối chiếu. Không chạy nhiều batch cùng lúc hoặc tác vụ nặng khác trên VM khi đo.

Chạy batch trong PowerShell trên EC2, dùng cùng `data/bounds.json` đã chốt. Không tính lại cận giữa các phương pháp. Disconnect RDP khi cần rời máy; không Sign out hoặc Stop khi đang chạy. Kết quả hoàn tất được ghi sau từng task. Sau khi chạy xong, lưu kết quả rồi Stop instance trong AWS Console. Khi Start lại, kiểm tra public IP mới để kết nối; dữ liệu đã lưu trên EBS được giữ lại.

## Nội dung cập nhật trong kế hoạch tuần 2

- Tạo VM Windows Server 2025 Base r6i.xlarge và cài CPLEX Optimization Studio 22.2.0 bằng bộ cài Windows đầy đủ.
- Cấu hình Python CPLEX MIP bằng runtime Studio; cấu hình DOcplex CP tìm `cpoptimizer.exe` qua PATH. Kiểm thử trước khi thực nghiệm chính thức.

Đây là hướng dẫn cấu hình; không phải bằng chứng đã cài hoặc chạy thành công trên VM.

## Tài liệu tham khảo

- IBM Academic / SkillsBuild: https://academic.ibm.com/a2mt/
- CPLEX Python API và nâng cấp runtime: https://www.ibm.com/docs/en/icos/22.1.2?topic=rnco2-cplex-python-api-now-installed-using-pip-conda
- Cấu hình DOcplex CP: https://ibmdecisionoptimization.github.io/docplex-doc/cp/_modules/docplex/cp/config.html
