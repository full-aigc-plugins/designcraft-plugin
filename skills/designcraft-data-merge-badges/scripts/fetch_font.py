#!/usr/bin/env python3
"""获取固定OFL任务字体和许可证，校验摘要，不安装系统字体。"""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

def fetch(directory):
    source=Path(__file__).resolve().parents[1]/'references/font-source.json'
    data=json.loads(source.read_text(encoding='utf-8'));dest=Path(directory).resolve();dest.mkdir(parents=True,exist_ok=True)
    for row in data['files']:
        target=dest/Path(row['path']).name
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest()!=row['sha256']:raise FileExistsError('refuse different existing font asset')
        else:
            blob=urlopen(row['url'],timeout=180).read()
            if hashlib.sha256(blob).hexdigest()!=row['sha256']:raise ValueError('font asset digest mismatch')
            with target.open('xb') as out:out.write(blob)
    return {'fontFile':str(dest/'NotoSansCJKsc-Regular.otf'),'family':data['family'],'license':str(dest/'LICENSE'),'result':'PASS','scope':'task-local font asset only'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',required=True);a=p.parse_args();print(json.dumps(fetch(a.directory),ensure_ascii=True))
