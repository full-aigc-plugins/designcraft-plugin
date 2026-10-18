#!/usr/bin/env python3
"""使用真实DesignCraft执行模板、逐条预览与数据合并；不实现排版引擎。"""
import argparse
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import shutil


def parse_rows(text):
    reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')),strict=True)
    fields=reader.fieldnames or []
    if len(fields)!=len(set(fields)) or not {'Name','Role'}<=set(fields):
        raise ValueError('CSV requires unique Name and Role columns, exact case')
    rows=list(reader)
    if not rows or len(rows)>200:raise ValueError('CSV requires 1..200 records')
    for row in rows:
        if None in row or any(value is None for value in row.values()):raise ValueError('ragged CSV row')
        if any(not row[k].strip() or len(row[k])>4096 or any(c in row[k] for c in '\r\n\0') for k in ['Name','Role']):
            raise ValueError('Name and Role must be nonempty single-line fields of at most4096 characters')
    return [{k:row[k] for k in ['Name','Role']} for row in rows]


def recipe(rows,event,size,family="Source Sans 3"):
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=['Name','Role']);writer.writeheader();writer.writerows(rows)
    steps=[]
    def add(command,params,purpose,capture=None):
        step={'command':command,'params':params,'purpose':purpose}
        if capture:step['capture']=capture
        steps.append(step)
    ref=lambda name:{'$ref':name}
    add('file.new',{'width':90/25.4*72,'height':54/25.4*72,'pages':1,'facingPages':False,'margins':12,'bleed':0,'title':'Editable badge template'},'仅新建90×54毫米胸牌模板，原生单位为点')
    add('data.source.select',{'name':'badges.csv','base64':base64.b64encode(stream.getvalue().encode()).decode(),'delimiter':'comma'},'选择实际UTF-8数据源，不用data.fields冒充','source')
    for name,text,rect,font in [('header',event,[18,16,237,36],9),('name','',[18,44,237,90],size),('role','',[18,98,237,128],11)]:
        add('frame.create',{'spread':0,'rect':rect,'content':'text','text':text},'创建独立可编辑文本框',name)
        if name in ('name','role'):
            field='Name' if name=='name' else 'Role'
            add('data.placeholder.add',{'field':field,'role':'text','story':ref(name+'.story'),'at':0},'在空故事中插入字段，不残留NAME示例字')
            text='<<'+field+'>>'
        add('text.select',{'story':ref(name+'.story'),'anchor':0,'focus':len(text.encode())},'选择完整UTF-8字节范围')
        add('type.char',{'attrs':{'fontFamily':family,'size':font}},'设置实际可编辑文字样式')
    for i,row in enumerate(rows,1):
        add('data.preview',{'record':i},'预览实际第'+str(i)+'条；record从1开始')
        add('document.inspect',{},'检查本条所有故事的溢出','preview'+str(i))
        add('preflight.run',{},'检查真实缺字和排版错误','check'+str(i))
        for field in ('name','role'):
            add('story.get',{'story':ref(field+'.story')},'核对完整字段，不用preview片段','preview'+str(i)+'_'+field)
    add('data.preview.stop',{},'退出预览恢复字段模板后再保存')
    add('document.inspect',{},'确认模板恢复可编辑占位符','template')
    for field in ('name','role'):
        add('story.get',{'story':ref(field+'.story')},'核对退出预览后完整占位符','template_'+field)
    return {'schema':'craft-scenario-playbooks/v1','application':'designcraft','id':'data-merge-badges','steps':steps,
            'check':'逐条完整文字、记录/页数、溢出、模板恢复、保存重开与实际PDF/PNG；长姓名先减字号但不低于14，仍溢出则停止。',
            'boundary':'新图模板；不是Scribus模板导入、多合一拼版或门禁凭证。既有工程须副本操作，不执行本脚本file.new覆盖用户文档。'}


def compile_steps(data):
    names={};out=[]
    def bind(v):
        if isinstance(v,dict):
            if set(v)=={'$ref'}:
                name,_,field=v['$ref'].partition('.')
                return '$'+str(names[name])+('.'+field if field else '')
            return {k:bind(x) for k,x in v.items()}
        return [bind(x) for x in v] if isinstance(v,list) else v
    for step in data['steps']:
        params=bind(step['params'])
        if step.get('capture'):names[step['capture']]=len(out)
        out.append({'command':step['command'],'params':params})
    return out,names


def build(cli,csv_path,out,event='CRAFT LAB / OPEN DAY',font_file=None,family=None):
    csv_path=Path(csv_path).resolve();original=csv_path.read_bytes();rows=parse_rows(original.decode('utf-8-sig'))
    if not event.strip() or len(event)>200:raise ValueError('event title required, at most200 characters')
    font_file=Path(font_file).resolve() if font_file else None
    if font_file and (not font_file.is_file() or font_file.suffix.lower() not in ('.otf','.ttf','.ttc')):raise ValueError('font file required')
    family=family or ('Noto Sans CJK SC' if font_file else 'Source Sans 3')
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);calls=[]
    if font_file:
        fonts=out/'Document Fonts';fonts.mkdir();shutil.copy2(font_file,fonts/font_file.name)
        if (font_file.parent/'LICENSE').is_file():shutil.copy2(font_file.parent/'LICENSE',fonts/'OFL.txt')
    def run(steps,label,source=None,save=None):
        script=out/(label+'.json');script.write_text(json.dumps(steps,ensure_ascii=True),encoding='utf-8')
        args=[str(cli),'script',str(script)]+(['--in',str(source)] if source else [])+(['--save',str(save)] if save else [])
        result=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',timeout=180);calls.append({'argv':args,'exitCode':result.returncode})
        (out/(label+'-stdout.json')).write_text(result.stdout,encoding='utf-8');(out/(label+'-stderr.txt')).write_text(result.stderr,encoding='utf-8')
        value=json.loads(result.stdout)
        if result.returncode or value.get('error'):raise RuntimeError(str(value.get('error',result.stderr)))
        return value['results']
    seed=out/'seed.designcraft'
    run([recipe(rows,event,22,family)['steps'][0]],'seed',save=seed)
    for size in (22,18,14):
        data=recipe(rows,event,size,family);steps,names=compile_steps({'steps':data['steps'][1:]});template=out/f'template-{size}.designcraft';results=run(steps,f'preview-{size}',source=seed,save=template)
        overflow=False
        for i,row in enumerate(rows,1):
            overflow|=any(s['overset'] for s in results[names['preview'+str(i)]]['stories'])
            issues=results[names['check'+str(i)]]['issues']
            if any(issue['kind']=='missingGlyphs' for issue in issues):raise ValueError('missing glyphs; supply licensed font in Document Fonts and correct family')
            for field in ('name','role'):
                if results[names['preview'+str(i)+'_'+field]]['text']!=row[field.title()]:raise AssertionError('field text changed')
        for field in ('name','role'):
            if results[names['template_'+field]]['text']!='<<'+field.title()+'>>':raise AssertionError('preview did not restore template')
        if not overflow:
            if any(results[names['check'+str(i)]]['errors'] for i in range(1,len(rows)+1)):raise ValueError('preflight errors remain')
            break
    else:raise ValueError('text remains overset at14pt; draft templates retained, redesign or obtain shorter authorized content')
    merged=out/'badges.designcraft';pdf=out/'badges.pdf'
    results=run([{'command':'data.merge','params':{}},{'command':'document.inspect','params':{}},{'command':'preflight.run','params':{}},{'command':'file.exportPdf','params':{'path':str(pdf)}}],'merge',source=template,save=merged)
    merge,info=results[:2]
    if results[2]['errors']:raise AssertionError('merged preflight errors')
    if results[3]['pages']!=len(rows):raise AssertionError('PDF page count mismatch')
    if merge['records']!=len(rows) or merge['pages']!=len(rows) or merge['oversetStories'] or merge['missingImages']:raise AssertionError('merge count or overflow mismatch')
    info=run([{'command':'document.inspect','params':{}}],'reopen',source=merged)[0]
    if info['pageCount']!=len(rows) or any(s['overset'] for s in info['stories']):raise AssertionError('reopened document count or overflow changed')
    requests=[{'command':'story.get','params':{'story':s['id']}} for s in info['stories']];stories=run(requests,'reopen-stories',source=merged)
    by_id={s['id']:s['text'] for s in stories}
    for spread,row in zip(info['spreads'],rows):
        texts=[by_id[i['story']] for i in spread['items'] if 'story' in i]
        if sorted(texts)!=sorted([event,row['Name'],row['Role']]):raise AssertionError('reopened record text/assignment changed')
    if csv_path.read_bytes()!=original:raise AssertionError('input CSV changed')
    if not pdf.read_bytes().startswith(b'%PDF'):raise AssertionError('missing PDF')
    args=[str(cli),'run','--in',str(merged),'--scale','3','--all-pages',str(out/'pages')]
    rendered=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',timeout=180);calls.append({'argv':args,'exitCode':rendered.returncode})
    if rendered.returncode or len(list((out/'pages').glob('*.png')))!=len(rows):raise AssertionError('page render missing')
    result={'result':'PASS','records':len(rows),'pages':info['pageCount'],'nameSize':size,'fontFamily':family,'preflight':'PASS','inputSha256':hashlib.sha256(original).hexdigest(),'output':str(merged),'nativeProcesses':len(calls),'calls':calls,'scope':'native editable merge and full-text readback, not host synchronization or print certification'}
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=True,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cli',required=True);p.add_argument('--csv',required=True);p.add_argument('--output-dir',required=True);p.add_argument('--event',default='CRAFT LAB / OPEN DAY');p.add_argument('--font-file');p.add_argument('--font-family');a=p.parse_args()
    print(json.dumps(build(a.cli,a.csv,a.output_dir,a.event,a.font_file,a.font_family),ensure_ascii=True))
