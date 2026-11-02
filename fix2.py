with open('docs/wps-script.js','r',encoding='utf-8') as f:
    s=f.read()

# In download: use album+folder as key for grouping AND for filename numbering
old = '''      // Group by folder name + album/id so each album goes to its own folder
    const itemsByFolder = new Map();
    for (const it of S.items) {
      const key = it.folderName + '|' + (it.album || it.id);
      if (!itemsByFolder.has(key)) itemsByFolder.set(key, []);
      itemsByFolder.get(key).push(it);
    }'''
new = '''      // Group by folder name + album/id so each album goes to its own folder (keep separate even if unnamed)
    const itemsByFolder = new Map();
    for (const it of S.items) {
      const key = it.folderName + '||' + (it.album || it.id);
      if (!itemsByFolder.has(key)) itemsByFolder.set(key, []);
      itemsByFolder.get(key).push(it);
    }'''
if old in s:
    s = s.replace(old, new)
    print('g1')
else:
    print('ng1')

old2 = "        const folderKey = folderNameClean + '|' + (it.album || it.id);"
new2 = "        const folderKey = folderNameClean + '||' + (it.album || it.id);"
if old2 in s:
    s = s.replace(old2, new2)
    print('g2')
else:
    print('ng2')

# For unnamed folders, ensure different names per album
old3 = '''          // Not in album - look for next text from same sender within 5 minutes
          const mTs = Number(m.t) || 0;
          let foundText = '';
          for (let i = 0; i < allChatMsgs.length; i++) {
            const tm = allChatMsgs[i];
            const tmTs = Number(tm.t) || 0;
            if (tmTs <= mTs) continue;
            if (tmTs - mTs > 300) break;
            const tmid = String(tm.id || '');
            const tlm = allLiveById.get(tmid);
            const tSender = getMsgSender(tm, chatId, tlm);
            const tSenderKey = getMsgAuthorKey(tm) || getMsgAuthorKey(tlm) || '';
            const sKey = getMsgAuthorKey(m) || getMsgAuthorKey(lm) || '';
            const same = (sKey && tSenderKey && sKey === tSenderKey) || (sender && tSender && sender === tSender);
            if (!same) continue;
            if (isTextOnlyMsg(tlm || tm)) {
              const body = getMsgBody(tlm || tm);
              if (body && body.trim()) { foundText = body.trim(); break; }
            }
          }
          if (foundText) {
            folderName = foundText;
            isUnnamed = false;
          } else {
            const d = new Date(mTs * 1000);
            const dt = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
            folderName = `Unnamed_${safe(sender,30)}_${dt}`;
            isUnnamed = true;
          }'''
new3 = '''          // Not in album - look for next text from same sender within 5 minutes
          const mTs = Number(m.t) || 0;
          let foundText = '';
          for (let i = 0; i < allChatMsgs.length; i++) {
            const tm = allChatMsgs[i];
            const tmTs = Number(tm.t) || 0;
            if (tmTs <= mTs) continue;
            if (tmTs - mTs > 300) break;
            const tmid = String(tm.id || '');
            const tlm = allLiveById.get(tmid);
            const tSender = getMsgSender(tm, chatId, tlm);
            const tSenderKey = getMsgAuthorKey(tm) || getMsgAuthorKey(tlm) || '';
            const sKey = getMsgAuthorKey(m) || getMsgAuthorKey(lm) || '';
            const same = (sKey && tSenderKey && sKey === tSenderKey) || (sender && tSender && sender === tSender);
            if (!same) continue;
            if (isTextOnlyMsg(tlm || tm)) {
              const body = getMsgBody(tlm || tm);
              if (body && body.trim()) { foundText = body.trim(); break; }
            }
          }
          if (foundText) {
            folderName = foundText;
            isUnnamed = false;
          } else {
            const d = new Date(mTs * 1000);
            const dt = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
            folderName = `Unnamed_${safe(sender,30)}_${dt}`;
            isUnnamed = true;
          }'''
# keep as-is, will handle differently

with open('docs/wps-script.js','w',encoding='utf-8') as f:
    f.write(s)
print('done')
