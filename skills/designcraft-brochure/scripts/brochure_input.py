#!/usr/bin/env python3
"""将确认的两产品数据写入既有四页配方；不执行引擎或改写输入。"""
import argparse
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import re


def text(value,limit,multiline=False):
    if not isinstance(value,str) or not value.strip() or len(value)>limit:
        raise ValueError('required text missing or too long')
    if any(ord(c)<32 and not (multiline and c=='\n') for c in value):
        raise ValueError('unsupported control character')
    value.encode('utf-8')
    return value


def picture(value):
    value=text(value,1024).replace('\\','/')
    if value.startswith('/') or ':' in value or any(p in ('','..','.') for p in value.split('/')):
        raise ValueError('image must be a workspace-relative path without traversal')
    return value


def build_recipe(data,template):
    """绑定四页文字/图片，重新计算UTF-8选择范围；保留原配方及独立打包步骤。"""
    if not isinstance(data,dict) or not isinstance(template,dict) or template.get('id')!='brochure':
        raise ValueError('expected brochure input and template')
    cover=data.get('cover');contact=data.get('contact');products=data.get('products')
    if not isinstance(cover,dict) or not isinstance(contact,dict) or not isinstance(products,list) or len(products)!=2:
        raise ValueError('provide cover, exactly two products and contact')
    pages=[{'heading':text(cover.get('heading'),80),'text':text(cover.get('text'),1200,True)}]
    for product in products:
        if not isinstance(product,dict):raise ValueError('product must be an object')
        dims=product.get('dimensions')
        if not isinstance(dims,list) or len(dims)!=3 or any(isinstance(x,bool) or not isinstance(x,int) or not 1<=x<=100000 for x in dims):
            raise ValueError('dimensions must contain three positive integer millimetres')
        price=product.get('price');currency=product.get('currency')
        if not isinstance(price,str) or not re.fullmatch(r'[0-9]{1,9}(?:\.[0-9]{1,2})?',price):
            raise ValueError('price must be a nonnegative decimal string with at most two places')
        if not isinstance(currency,str) or not re.fullmatch('[A-Z]{3}',currency):raise ValueError('currency must be three uppercase letters')
        body='\n'.join([text(product.get('sku'),80)+' / '+text(product.get('variant'),80),' x '.join(map(str,dims))+' mm',currency+' '+format(Decimal(price),'.2f'),text(product.get('description'),500,True)])
        pages.append({'heading':text(product.get('heading'),80),'text':body,'image':picture(product.get('image'))})
    pages.append({'heading':text(contact.get('heading'),80),'text':text(contact.get('text'),1200,True)})
    footer=text(data.get('footer','Review copy'),60);result=deepcopy(template)
    family=text(data['fontFamily'],100) if 'fontFamily' in data else None
    if len(result.get('pages',[]))!=4:raise ValueError('template must have four pages')
    frames={};images={}
    for index,(page,new) in enumerate(zip(result['pages'],pages)):
        page.update(new);key=page['key'];frames.update({key+'_heading':page['heading'],key+'_copy':page['text'],key+'_footer':f'{index+1} / 4  |  {footer}'})
        if 'image' in page:images[key+'_image']=page['image']
    for step in result['steps']:
        params=step['params']
        if step['command']=='file.new':params['title']=pages[0]['heading']+' / product brochure'
        elif step['command']=='style.paragraph.create' and family:params.setdefault('chars',{})['fontFamily']=family
        elif step['command']=='frame.create' and step.get('capture') in frames:params['text']=frames[step['capture']]
        elif step['command']=='text.select':
            ref=params.get('story',{}).get('$ref','').split('.')[0]
            if ref in frames:params.update(anchor=0,focus=len(frames[ref].encode('utf-8')))
        elif step['command']=='file.place':
            ref=params.get('frame',{}).get('$ref','').split('.')[0]
            if ref in images:params['path']=images[ref]
    result['argumentPolicy']='Generated from confirmed input; preflight overset, image links/PPI and each page before delivery. No layout or facts acceptance inferred.'
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try:
        recipe=build_recipe(json.loads(a.input.read_text(encoding='utf-8')),json.loads((Path(__file__).resolve().parents[1]/'references/craft-steps.json').read_text(encoding='utf-8')))
        with a.output.open('x',encoding='utf-8') as f:json.dump(recipe,f,ensure_ascii=True,indent=2);f.write('\n')
    except (ValueError,OSError) as error:p.exit(2,str(error)+'\n')
if __name__=='__main__':main()
