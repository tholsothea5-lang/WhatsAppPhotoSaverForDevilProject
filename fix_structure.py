with open('docs/wps-script.js', 'r', encoding='utf-8') as f:
    s = f.read()

# Change ZIP structure to Chat/DD-MM-YYYY/AKY Folder
old = '''        // Group by folder name (album group)
    const itemsByFolder = new Map();
    for (const it of S.items) {
      const key = it.folderName;
      if (!itemsByFolder.has(key)) itemsByFolder.set(key, []);
      itemsByFolder.get(key).push(it);
    }'''

new = '''        // Group by folder name (album group)
    const itemsByFolder = new Map();
    for (const it of S.items) {
      const key = it.folderName + '||' + (it.album || it.id);
      if (!itemsByFolder.has(key)) itemsByFolder.set(key, []);
      itemsByFolder.get(key).push(it);
    }'''

if old in s:
    s = s.replace(old, new)
    print('1')
else:
    print('0')

old2 = '''          if (!usedNames.has(folderKey)) usedNames.set(folderKey, new Set());
        const usedSet = usedNames.get(folderKey);
        
        // Number files as FolderName_001.jpg, FolderName_002.jpg
        let idx = 1;
        // Find next available number for this folder
        while (true) {
          const num = String(idx).padStart(3, '0');
          const baseName = `${folderNameClean}_${num}.${it.ext}`;
          if (!usedSet.has(baseName)) {
            usedSet.add(baseName);
            // Check if we need to add _1, _2 for duplicates? The spec says "add _1, _2 and so on to duplicate file names"
            // But we are naming sequentially as FolderName_001, 002 etc. The hash was in old naming to avoid duplicates.
            // New spec says: "Rename photos as FolderName_001.jpg, FolderName_002.jpg, and so on" - sequential per album folder
            zipAdd(zip, `${chatFolder}/${folderNameClean}/${baseName}`, data, when);
            break;
          }
          idx++;
        }'''

new2 = '''          if (!usedNames.has(folderKey)) usedNames.set(folderKey, new Set());
        const usedSet = usedNames.get(folderKey);
        
        // Number files as FolderName_001.jpg, FolderName_002.jpg
        let idx = 1;
        while (true) {
          const num = String(idx).padStart(3, '0');
          const baseName = `${folderNameClean}_${num}.${it.ext}`;
          if (!usedSet.has(baseName)) {
            usedSet.add(baseName);
            // Structure: [Chat Name]/[DD-MM-YYYY]/[AKY Folder]/photo_001.jpg
            zipAdd(zip, `${chatFolder}/${dmy(when)}/${folderNameClean}/${baseName}`, data, when);
            break;
          }
          idx++;
        }'''

if old2 in s:
    s = s.replace(old2, new2)
    print('2')
else:
    print('0b')

with open('docs/wps-script.js', 'w', encoding='utf-8') as f:
    f.write(s)
