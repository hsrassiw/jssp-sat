"""Worker riêng cho một lượt chạy; chỉ batch.py gọi module này."""
import argparse
import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from src.common.result import Config
from src.common.run import run_one
from src.sat import strategies


def partial_path(output):
    return Path(str(output)+'.partial')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--request',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();request=json.loads(Path(a.request).read_text(encoding='utf-8'))
    cfg=Config(**request['config'])

    def save_partial(res):
        # ghi file tạm rồi đổi tên, bị giết giữa chừng cũng không hỏng file
        tmp=Path(str(partial_path(a.output))+'.tmp')
        tmp.write_text(json.dumps(asdict(res),ensure_ascii=False),encoding='utf-8')
        os.replace(tmp,partial_path(a.output))
    strategies.save_progress=save_partial

    result=run_one(request['source'],cfg,max(0.0,request['deadline']-time.perf_counter()),
                   bounds_file=request['bounds_file'])
    Path(a.output).write_text(json.dumps(asdict(result),ensure_ascii=False),encoding='utf-8')


if __name__=='__main__':main()
