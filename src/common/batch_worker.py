"""Worker riêng cho một lượt chạy; chỉ batch.py gọi module này."""
import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path
from src.common.result import Config
from src.common.run import run_one


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--request',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();request=json.loads(Path(a.request).read_text(encoding='utf-8'))
    cfg=Config(**request['config'])
    result=run_one(request['source'],cfg,max(0.0,request['deadline']-time.perf_counter()),
                   bounds_file=request['bounds_file'])
    Path(a.output).write_text(json.dumps(asdict(result),ensure_ascii=False),encoding='utf-8')


if __name__=='__main__':main()
