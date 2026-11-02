with open('docs/wps-script.js','r',encoding='utf-8') as f:
    s=f.read()

# Track unnamed album numbers
old = '''      // For each album, find next text from same sender within 5 minutes for each album
      for (const [a, info] of albumToSender) {
        const albumTs = info.ts;
        let foundFolder = '';
        // Look through timeline after album
        for (let i = 0; i < allChatMsgs.length; i++) {
          const m = allChatMsgs[i];
          const mTs = Number(m.t) || 0;
          if (mTs <= albumTs) continue;
          if (mTs - albumTs > 300) break; // 5 minutes = 300 seconds
          const mid = String(m.id || '');
          const lm = allLiveById.get(mid);
          // Check if same sender
          const mSenderKey = getMsgAuthorKey(m) || getMsgAuthorKey(lm) || '';
          const mSender = getMsgSender(m, chatId, lm);
          const sameSender = (info.senderKey && mSenderKey && info.senderKey === mSenderKey) || 
                             (info.sender && mSender && info.sender === mSender);
          if (!sameSender) continue;
          if (isTextOnlyMsg(lm || m) || (getMsgBody(lm || m) && !m.isMediaMsg && m.type !== 'image' && m.type !== 'video')) {
            const body = getMsgBody(lm || m);
            if (body && body.trim()) {
              foundFolder = body.trim();
              break;
            }
          }
        }
        if (foundFolder) {
          albumFolderMap.set(a, { folderName: foundFolder, isUnnamed: false, sender: info.sender });
        } else {
          const d = new Date(albumTs * 1000);
          const dt = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
          const short = String(a).replace(/[^a-zA-Z0-9]/g,'').slice(-6) || 'x';
          albumFolderMap.set(a, { folderName: `Unnamed_${safe(info.sender, 30)}_${dt}_${short}`, isUnnamed: true, sender: info.sender });
        }
      }'''
new = '''      // For each album, find next text from same sender within 5 minutes for each album
      let noCapCounter = 0;
      for (const [a, info] of albumToSender) {
        const albumTs = info.ts;
        let foundFolder = '';
        // Look through timeline after album
        for (let i = 0; i < allChatMsgs.length; i++) {
          const m = allChatMsgs[i];
          const mTs = Number(m.t) || 0;
          if (mTs <= albumTs) continue;
          if (mTs - albumTs > 300) break; // 5 minutes = 300 seconds
          const mid = String(m.id || '');
          const lm = allLiveById.get(mid);
          // Check if same sender
          const mSenderKey = getMsgAuthorKey(m) || getMsgAuthorKey(lm) || '';
          const mSender = getMsgSender(m, chatId, lm);
          const sameSender = (info.senderKey && mSenderKey && info.senderKey === mSenderKey) || 
                             (info.sender && mSender && info.sender === mSender);
          if (!sameSender) continue;
          if (isTextOnlyMsg(lm || m) || (getMsgBody(lm || m) && !m.isMediaMsg && m.type !== 'image' && m.type !== 'video')) {
            const body = getMsgBody(lm || m);
            if (body && body.trim()) {
              foundFolder = body.trim();
              break;
            }
          }
        }
        if (foundFolder) {
          albumFolderMap.set(a, { folderName: foundFolder, isUnnamed: false, sender: info.sender });
        } else {
          noCapCounter++;
          albumFolderMap.set(a, { folderName: `No caption_${noCapCounter} (photo album ${noCapCounter})`, isUnnamed: true, sender: info.sender });
        }
      }'''
if old in s:
    s = s.replace(old, new)
    print('b1')
else:
    print('nb1')

old2 = '''          if (foundText) {
            folderName = foundText;
            isUnnamed = false;
          } else {
            const d = new Date(mTs * 1000);
            const dt = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
            const short = String(id).replace(/[^a-zA-Z0-9]/g,'').slice(-6) || 'x';
            folderName = `Unnamed_${safe(sender,30)}_${dt}_${short}`;
            isUnnamed = true;
          }'''
new2 = '''          if (foundText) {
            folderName = foundText;
            isUnnamed = false;
          } else {
            noCapCounter++;
            folderName = `No caption_${noCapCounter} (photo album ${noCapCounter})`;
            isUnnamed = true;
          }'''
if old2 in s:
    s = s.replace(old2, new2)
    print('b2')
else:
    print('nb2')

with open('docs/wps-script.js','w',encoding='utf-8') as f:
    f.write(s)
print('done')
