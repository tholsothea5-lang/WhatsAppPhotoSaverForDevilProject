with open('docs/wps-script.js','r',encoding='utf-8') as f:
    s=f.read()

# Add counter scope and use it
old = '''      // For each album, find next text from same sender within 5 minutes for each album
      let noCapCounter = 0;
      for (const [a, info] of albumToSender) {'''
new = '''      // For each album, find next text from same sender within 5 minutes for each album
      let noCapCounterGlobal = 0;
      for (const [a, info] of albumToSender) {'''
if old in s:
    s = s.replace(old, new)
    print('c1')
else:
    print('nc1')

old2 = "          noCapCounter++;"
new2 = "          noCapCounterGlobal++;"
s = s.replace(old2, new2)

old3 = "            folderName = `No caption_${noCapCounter} (photo album ${noCapCounter})`;"
new3 = "            folderName = `No caption_${noCapCounterGlobal} (photo album ${noCapCounterGlobal})`;"
s = s.replace(old3, new3)

old4 = "          albumFolderMap.set(a, { folderName: `No caption_${noCapCounter} (photo album ${noCapCounter})`, isUnnamed: true, sender: info.sender });"
new4 = "          albumFolderMap.set(a, { folderName: `No caption_${noCapCounterGlobal} (photo album ${noCapCounterGlobal})`, isUnnamed: true, sender: info.sender });"
s = s.replace(old4, new4)

with open('docs/wps-script.js','w',encoding='utf-8') as f:
    f.write(s)
print('done')
