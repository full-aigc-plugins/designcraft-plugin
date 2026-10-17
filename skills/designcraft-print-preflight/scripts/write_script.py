"""将手册命名引用编译为DesignCraft原生$N引用；不执行或实现排版业务。"""
import argparse
import json
from pathlib import Path


def compile_steps(recipe,existing=False,inputs=None,phase=None):
    if phase not in ('inspect','repair','export'):raise ValueError('Select inspect, repair or export phase explicitly')
    bindings={};out=[]
    def resolve(v):
        if isinstance(v,dict):
            if set(v)=={'$input'}:
                if inputs is None or v['$input'] not in inputs:raise ValueError('Missing input binding: '+v['$input'])
                return inputs[v['$input']]
            if set(v)=={'$ref'}:
                name,sep,field=v['$ref'].partition('.')
                if name not in bindings:raise ValueError('Unknown or forward return reference: '+v['$ref'])
                return '$'+str(bindings[name])+('.'+field if sep else '')
            return {k:resolve(x) for k,x in v.items()}
        if isinstance(v,list):return [resolve(x) for x in v]
        return v
    for step in recipe['steps']:
        if step.get('phase')!=phase:continue
        if existing and step.get('newDocumentOnly'):continue
        params=resolve(step['params']);name=step.get('capture')
        if name:
            if name in bindings:raise ValueError('Duplicate capture: '+name)
            bindings[name]=len(out)
        out.append({'command':step['command'],'params':params})
    return out,bindings


def main():
    p=argparse.ArgumentParser();p.add_argument('--recipes',type=Path,required=True);p.add_argument('--scene',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--existing',action='store_true');p.add_argument('--inputs',type=Path);p.add_argument('--phase',required=True,choices=['inspect','repair','export']);a=p.parse_args()
    data=json.loads(a.recipes.read_text(encoding='utf-8'))
    recipe=next(r for r in data.get('recipes',[data]) if r['id']==a.scene)
    inputs=json.loads(a.inputs.read_text(encoding='utf-8')) if a.inputs else None
    steps,_=compile_steps(recipe,a.existing,inputs,a.phase)
    with a.output.open('x',encoding='utf-8') as out:json.dump(steps,out,ensure_ascii=False,indent=2)


if __name__=='__main__':main()
