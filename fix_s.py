with open('docs/wps-script.js','r',encoding='utf-8') as f:
    s = f.read()

old = "            zipAdd(zip, `${chatFolder}/${folderNameClean}/${baseName}`, data, when);"
new = "            zipAdd(zip, `${chatFolder}/${dmy(when)}/${folderNameClean}/${baseName}`, data, when);"
if old in s:
    s = s.replace(old, new)
    print('ok')
else:
    print('no')
with open('docs/wps-script.js','w',encoding='utf-8') as f:
    f.write(s)
