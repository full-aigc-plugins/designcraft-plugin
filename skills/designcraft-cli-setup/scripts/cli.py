#!/usr/bin/env python3
"""从当前独立技能安装/核验固定 CLI，然后按 argv 调用；不依赖 PATH 或兄弟技能。"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
sys.dont_write_bytecode=True
ALLOWED={'links', '-V', 'app', 'bench', '--version', 'run', 'perf', 'script', 'mcp', 'version', 'describe', 'commands'}
def setup_failure(runtime_home):
 """安装器缺失时也保留当前技能自身的恢复位置，不读取兄弟技能。"""
 return {'skill':'designcraft-cli-setup','bootstrapScript':str(Path(__file__).with_name('bootstrap.py').resolve()),'runtimeHome':str(Path(runtime_home).expanduser().absolute()),'automaticRetry':False}
def write_machine_result(path,result):
 """以原子 JSON 文件向组合调用者回传状态，不污染原生命令 stdout。"""
 target=Path(path).expanduser().absolute();target.parent.mkdir(parents=True,exist_ok=True);temporary=None
 try:
  with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=target.parent,prefix='.native-result-',delete=False) as stream:
   temporary=Path(stream.name);json.dump(result,stream,ensure_ascii=False,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
  os.replace(temporary,target)
 finally:
  if temporary is not None and temporary.exists():temporary.unlink()
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--runtime-home',default=os.environ.get('CRAFT_RUNTIME_HOME',str(Path.home()/'.local/share/craft-runtimes')))
 parser.add_argument('--archive',type=Path)
 parser.add_argument('--result-file',type=Path,help='写入版本化执行状态；不改变原生 stdout/stderr')
 parser.add_argument('--timeout',type=float,default=600,help='短命令等待秒数；MCP 长驻服务忽略此限制')
 parser.add_argument('arguments',nargs=argparse.REMAINDER)
 args=parser.parse_args();argv=args.arguments
 if argv[:1]==['--']:argv=argv[1:]
 if not argv or argv[0] not in ALLOWED:parser.error('unsupported_cli_subcommand: put the native subcommand first after --')
 installation_completed=False
 started_at=datetime.now(timezone.utc).isoformat();native_started=False
 try:
  path=Path(__file__).with_name('bootstrap.py');spec=importlib.util.spec_from_file_location('craft_bootstrap',path)
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  installed=module.install(json.loads(path.with_name('runtime.lock.json').read_text()),args.runtime_home,args.archive)
  installation_completed=True
  native_started=True
  timeout=None if argv[0]=='mcp' else args.timeout
  result=subprocess.run([installed['executable'],*argv],timeout=timeout)
  if args.result_file:
   write_machine_result(args.result_file,{'schemaVersion':1,'status':'NATIVE_EXIT_ZERO_REVIEW_REQUIRED' if result.returncode==0 else 'FAILED_OR_PARTIAL','reason':'native_exit' if result.returncode==0 else 'native_nonzero_exit','exitCode':result.returncode,'started':True,'startedAt':started_at,'finishedAt':datetime.now(timezone.utc).isoformat(),'terminationVerified':True,'descendantsTerminationVerified':False})
  return result.returncode
 except (ValueError,OSError,subprocess.SubprocessError,KeyboardInterrupt) as error:
  if isinstance(error,OSError):native_started=False
  unknown=isinstance(error,(subprocess.TimeoutExpired,KeyboardInterrupt))
  reply={'error':str(error),'result':'unknown' if unknown else 'failed'}
  if not installation_completed:reply['dependencySetup']=setup_failure(args.runtime_home)
  if args.result_file:
   interrupted=isinstance(error,KeyboardInterrupt);timed_out=isinstance(error,subprocess.TimeoutExpired)
   reason='user_interrupted' if interrupted else ('native_timeout' if timed_out else ('native_launch_failed' if isinstance(error,OSError) else ('native_execution_error' if native_started else 'runtime_setup_failed')))
   status='UNKNOWN' if interrupted or timed_out else ('FAILED_OR_PARTIAL' if native_started else 'NOT_STARTED')
   write_machine_result(args.result_file,{'schemaVersion':1,'status':status,'reason':reason,'exitCode':None,'started':native_started,'startedAt':started_at,'finishedAt':datetime.now(timezone.utc).isoformat(),'terminationVerified':False,'descendantsTerminationVerified':False,'stdout':getattr(error,'stdout',None).decode('utf-8',errors='replace') if isinstance(getattr(error,'stdout',None),bytes) else (getattr(error,'stdout',None) or ''),'stderr':getattr(error,'stderr',None).decode('utf-8',errors='replace') if isinstance(getattr(error,'stderr',None),bytes) else (getattr(error,'stderr',None) or '')})
  print(json.dumps(reply));return 1
if __name__=='__main__':raise SystemExit(main())
