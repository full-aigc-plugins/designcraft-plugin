"""当前独立技能的原生命令目录与计划入口。"""
import importlib.util
from pathlib import Path
p=Path(__file__).with_name("command_gateway.py")
spec=importlib.util.spec_from_file_location("craft_commands",p)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
if __name__=="__main__":raise SystemExit(module.main("designcraft",p.parent))
