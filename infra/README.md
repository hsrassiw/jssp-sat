# Tạo VM và cài solver đầy đủ

Chưa có VM được triển khai tự động từ gói này. Cần thao tác trong tài khoản AWS của Lâm và bộ cài CPLEX Studio Linux x86-64 được cấp phép.

## 1. Tạo máy

AWS CloudFormation > Create stack > With new resources > Upload a template file > chọn `infra/ec2-jssp.yaml`.
Điền AMI Ubuntu Server 24.04 LTS x86_64 của region đang chọn, VPC, public subnet cùng VPC, key pair đã có và IPv4 của bạn dạng a.b.c.d/32. Template tạo r6i.xlarge (4 vCPU, 32 GiB), EBS gp3 40 GiB mã hóa, public IP và security group chỉ mở SSH từ IP đó. Đây là tài nguyên trả phí; xem giá ở region trước khi Create stack. Không có IAM role/quyền AWS cho VM.

Khi stack CREATE_COMPLETE, lấy PublicIp ở Outputs. SSH từ PowerShell (thay đường dẫn key và địa chỉ thực tế):

```powershell
ssh -i "D:\keys\jssp.pem" ubuntu@PUBLIC_IP
```

UserData cài Python/git/tmux. Trên VM chờ xong:

```bash
sudo cloud-init status --wait
python3.12 --version
```

Clone repo nhóm (dùng URL thật), cd repo và chép gói cập nhật. Chạy `bash setup.sh`. Không cần cổng HTTP, RDS hay NAT Gateway cho bài này.

## 2. Gurobi

Copy license WLS của chính bạn vào `~/gurobi.lic` trên VM, hoặc đặt biến `GRB_LICENSE_FILE` là đường dẫn tuyệt đối. WLS cần mạng; license gắn máy cũ không tự trở thành license cho VM. Không đưa license vào Git.

```bash
chmod 600 ~/gurobi.lic
source .venv/bin/activate
python scripts/check_solvers.py --full --solvers gurobi
```

`--full` thử 2101 biến để phát hiện runtime giới hạn kích thước, không chỉ import/khởi tạo Model.

## 3. CPLEX đầy đủ

Tải IBM ILOG CPLEX Optimization Studio Linux x86-64 bản đầy đủ từ tài khoản academic/entitlement của bạn, chép `.bin` lên VM. Chạy bộ cài và chọn thư mục cài đặt:

```bash
bash TEN_BO_CAI.linux_x86_64.bin -i console
```

Với CPLEX 22.1.2 trở lên, Python API được cài qua pip rồi nâng cấp runtime bằng bộ Studio đầy đủ (IBM đã thay đổi quy trình; hướng dẫn không dùng pip trong kế hoạch cũ không còn áp dụng nguyên văn). Dùng phiên bản package KHỚP Studio. Ví dụ nếu cài Studio 22.2.0:

```bash
source .venv/bin/activate
python -m pip install 'cplex==22.2.0.1' docplex setuptools
# Thay đường dẫn dưới bằng thư mục Studio bạn đã cài thực tế.
docplex config --upgrade /DUONG_DAN/CPLEX_Studio2220
python scripts/check_solvers.py --full --solvers cplex
```

Hoặc đặt `CPLEX_STUDIO_DIR` và `CPLEX_PY_VERSION` rồi chạy lại setup.sh. Không chạy pip reinstall cplex sau upgrade vì có thể thay lại runtime Community.

Nếu dùng Studio cũ có thư mục cplex/python/VERSION/PLATFORM, dùng API và Python tương thích theo tài liệu bản đó; không dùng lệnh version 22.2.0.1 ở trên.

Để CP Optimizer của Quang tìm executable, thêm thư mục thực tế vào PATH, không sửa đường dẫn máy cá nhân vào code:

```bash
export PATH="/DUONG_DAN/CPLEX_Studio2220/cpoptimizer/bin/x86-64_linux:$PATH"
command -v cpoptimizer
```

Kiểm tra bản đầy đủ bằng bài lớn:

```bash
python -m src.common.run la21 --method MIP --solver cplex --time-limit 30
python -m src.common.run la21 --method CP --solver cplex --time-limit 30
```

FEAS/NOSOL do hết 30 giây không đồng nghĩa lỗi license. ERR có lỗi giới hạn kích thước thì runtime chưa được nâng cấp đúng. Lệnh CP chỉ chạy sau khi ghép adapter của Quang.

## 4. Thực nghiệm

Dùng cùng một commit, cùng data/bounds.json đã chốt và một VM. Batch mặc định chạy tuần tự, mỗi solver đặt 1 luồng. Dùng tmux để SSH ngắt không giết batch. Không chạy tác vụ khác trên VM trong lúc đo.

```bash
tmux new -s jssp
python -m src.common.batch --instances ft06 la01 la02 --methods SAT CP MIP --csv results/aws.csv
```

Sau khi tải đủ CSV, manifest và logs về, stop VM nếu cần dùng lại; EBS vẫn có phí. Chỉ delete stack sau khi đã sao lưu vì EBS sẽ bị xóa khi terminate.

Nguồn chính thức:
- https://aws.amazon.com/ec2/instance-types/r6i/
- https://www.ibm.com/docs/en/icos/22.1.2?topic=rnco2-cplex-python-api-now-installed-using-pip-conda
- https://www.ibm.com/docs/en/icos/22.1.1?topic=cplex-setting-up-python-api
