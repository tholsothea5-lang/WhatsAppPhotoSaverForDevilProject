with open('docs/wps-script.js','r',encoding='utf-8') as f:
    s=f.read()

old = '''          if (foundText) {
            folderName = foundText;
            isUnnamed = false;
          } else {
            noCapCounter++;
            folderName = `No caption_${noCapCounterGlobal} (photo album ${noCapCounterGlobal})`;
            isUnnamed = true;
          }'''
new = '''          if (foundText) {
            folderName = foundText;
            isUnnamed = false;
          } else {
            noCapCounterGlobal++;
            folderName = `No caption_${noCapCounterGlobal} (photo album ${noCapCounterGlobal})`;
            isUnnamed = true;
          }'''
if old in s:
    s = s.replace(old, new)
    print('ok')
else:
    print('no')

with open('docs/wps-script.js','w',encoding='utf-8') as f:
    f.write(s)
