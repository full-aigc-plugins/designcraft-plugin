import importlib.util
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class BrochureInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('brochure_input',ROOT/'scripts/brochure_input.py');cls.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.m)
    def data(self):return {'cover':{'heading':'工作套装','text':'经确认的介绍'},'products':[{'heading':'桌面收纳','sku':'SKU-1','variant':'蓝色','dimensions':[240,160,80],'price':'24.5','currency':'CNY','description':'示例描述','image':'素材/收纳.png'},{'heading':'文件袋','sku':'SKU-2','variant':'橙色','dimensions':[320,240,45],'price':'39.50','currency':'CNY','description':'第二项描述','image':'素材/文件袋.png'}],'contact':{'heading':'下一步','text':'核对供货情况'},'footer':'校样'}
    def template(self):return json.loads((ROOT/'references/craft-steps.json').read_text())
    def test_products_and_utf8(self):
        result=self.m.build_recipe(self.data(),self.template());self.assertEqual(result['pages'][1]['heading'],'桌面收纳');self.assertIn('CNY 24.50',result['pages'][1]['text']);frames={s['capture']:s['params']['text'] for s in result['steps'] if s.get('capture') and s['command']=='frame.create' and s['params']['content']=='text'}
        for s in result['steps']:
            if s['command']=='text.select':self.assertEqual(s['params']['focus'],len(frames[s['params']['story']['$ref'].split('.')[0]].encode('utf-8')))
    def test_does_not_mutate_template(self):
        t=self.template();original=json.dumps(t);self.m.build_recipe(self.data(),t);self.assertEqual(json.dumps(t),original)
    def test_exactly_two_products(self):
        d=self.data();d['products'].pop()
        with self.assertRaises(ValueError):self.m.build_recipe(d,self.template())
    def test_unsafe_paths(self):
        for path in ['../a.png','C:\\a.png','/a.png','a/../b.png','\\\\host\\share.png']:
            d=self.data();d['products'][0]['image']=path
            with self.assertRaises(ValueError):self.m.build_recipe(d,self.template())
    def test_invalid_price(self):
        for amount in ['NaN','-1','1.234',True,24.5]:
            d=self.data();d['products'][0]['price']=amount
            with self.assertRaises(ValueError):self.m.build_recipe(d,self.template())
    def test_invalid_dimensions(self):
        for v in [True,0,float('inf'),-2]:
            d=self.data();d['products'][0]['dimensions'][0]=v
            with self.assertRaises(ValueError):self.m.build_recipe(d,self.template())
    def test_explicit_font(self):
        d=self.data();d['fontFamily']='LXGW WenKai';r=self.m.build_recipe(d,self.template());self.assertEqual([s['params']['chars']['fontFamily'] for s in r['steps'] if s['command']=='style.paragraph.create'],['LXGW WenKai']*3)
    def test_bad_font_name(self):
        d=self.data();d['fontFamily']='bad\nname'
        with self.assertRaises(ValueError):self.m.build_recipe(d,self.template())
    def test_single_line_heading(self):
        d=self.data();d['cover']['heading']='a\nb'
        with self.assertRaises(ValueError):self.m.build_recipe(d,self.template())
if __name__=='__main__':unittest.main()
