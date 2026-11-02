with open('docs/wps-script.js','r',encoding='utf-8') as f:
    s=f.read()

old = "      // Group by folder name (album group)\n    const itemsByFolder = new Map();\n    for (const it of S.items) {\n      const key = it.folderName;\n      if (!itemsByFolder.has(key)) itemsByFolder.set(key, []);\n      itemsByFolder.get(key).push(it);\n    }"
new = "      // Group by folder name + album/id so each album goes to its own folder\n    const itemsByFolder = new Map();\n    for (const it of S.items) {\n      const key = it.folderName + '|' + (it.album || it.id);\n      if (!itemsByFolder.has(key)) itemsByFolder.set(key, []);\n      itemsByFolder.get(key).push(it);\n    }"
if old in s:
    s = s.replace(old, new)
    print('replaced1')
else:
    print('no1')

old2 = "        const folderKey = folderNameClean;"
new2 = "        const folderKey = folderNameClean + '|' + (it.album || it.id);"
if old2 in s:
    s = s.replace(old2, new2)
    print('replaced2')
else:
    print('no2')

with open('docs/wps-script.js','w',encoding='utf-8') as f:
    f.write(s)
