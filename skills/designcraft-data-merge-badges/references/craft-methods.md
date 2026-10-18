# 参数与已复现边界

先file.new创建新文档，再data.source.select `{name:"badges.csv",base64:UTF8_CSV的Base64,delimiter:"comma"}`；真实返回fields/records必须与输入相符。data.fields读取或显示字段，不会选择实际数据源。

frame.create `{spread:0,rect:[18,44,237,90],content:"text",text:""}`返回`{id,story}`。data.placeholder.add `{field:"Name",role:"text",story:实际story,at:0}`在空故事插入`<<Name>>`；end不会替换本例已有NAME文字。随后text.select `{story:实际story,anchor:0,focus:8}`再type.char `{attrs:{fontFamily:"Noto Sans CJK SC",size:22}}`；Role相同，另用11pt。标题的focus取UTF-8字节数。

data.preview `{record:1}`预览首条；story.get `{story:实际story}`核对全文，document.inspect `{}`核对每个故事overset，preflight.run `{}`的missingGlyphs/missingFont均不能忽略。data.preview.stop `{}`后再story.get应恢复占位符。保存模板后data.merge `{}`，不把单条预览永久写成模板；返回records、pages、oversetStories均需核对。

原生file.open会载入工程旁Document Fonts；file.new会重置该环境。执行器先保存空白seed，重开加载任务字体后创建内容，不再执行file.new。脚本原生$N绑定来自编译后的命令索引，MCP用每步实际返回值。字号降级仅处理姓名；角色或标题仍溢出则停止，不能通过改小姓名掩盖其他字段问题。

file.exportPdf `{path:新路径}`默认全部页，页号选项从1开始。原生CLI `run --in 合并工程 --scale 3 --all-pages 新目录`逐页导出PNG。本流程不承诺IDML/Scribus互导、图像字段、多记录拼版、PDF/X或商业印刷合格。

## 当前Web运行时字体适配

已实测原生Noto侧车字体没有随open_document自动加载到Web。先data.preview.stop，再font.replace `{family:"Noto Sans CJK SC",toFamily:"LXGW WenKai",toStyle:"Regular",redefineStyles:true}`替换本例三处模板文字；font.list `{}`必须显示missing:false、source:bundled，逐条preview后preflight.run应为零错误，再保存模板和merge。该替换用于无品牌指定字体的合成样例，字体外观已改变，不宣称与原生Noto版像素相同。
