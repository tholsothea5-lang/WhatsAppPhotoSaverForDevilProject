with open('docs/wps-script.js','r',encoding='utf-8') as f:
    s=f.read()

# For album unnamed
old = '''        if (foundFolder) {
          albumFolderMap.set(a, { folderName: foundFolder, isUnnamed: false, sender: info.sender });
        } else {
          const d = new Date(albumTs * 1000);
          const dt = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
          albumFolderMap.set(a, { folderName: `Unnamed_${safe(info.sender, 30)}_${dt}`, isUnnamed: true, sender: info.sender });
        }'''
new = '''        if (foundFolder) {
          albumFolderMap.set(a, { folderName: foundFolder, isUnnamed: false, sender: info.sender });
        } else {
          const d = new Date(albumTs * 1000);
          const dt = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
          const short = String(a).replace(/[^a-zA-Z0-9]/g,'').slice(-6) || 'x';
          albumFolderMap.set(a, { folderName: `Unnamed_${safe(info.sender, 30)}_${dt}_${short}`, isUnnamed: true, sender: info.sender });
        }'''
if old in s:
    s = s.replace(old, new)
    print('a1')
else:
    print('na1')

# For non-album
old2 = '''          if (foundText) {
            folderName = foundText;
            isUnnamed = false;
          } else {
            const d = new Date(mTs * 1000);
            const dt = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
            folderName = `Unnamed_${safe(sender,30)}_${dt}`;
            isUnnamed = true;
          }'''
new2 = '''          if (foundText) {
            folderName = foundText;
            isUnnamed = false;
          } else {
            const d = new Date(mTs * 1000);
            const dt = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
            const short = String(id).replace(/[^a-zA-Z0-9]/g,'').slice(-6) || 'x';
            folderName = `Unnamed_${safe(sender,30)}_${dt}_${short}`;
            isUnnamed = true;
          }'''
if old2 in s:
    s = s.replace(old2, new2)
    print('a2')
else:
    print('na2')

with open('docs/wps-script.js','w',encoding='utf-8') as f:
    f.write(s)
print('done')
