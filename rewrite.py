with open('docs/wps-script.js','r',encoding='utf-8') as f:
    s=f.read()

# Update album folder logic
old = '''      // For each album, find next text from same sender within 5 minutes for each album
      let noCapCounterGlobal = 0;
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
          noCapCounterGlobal++;
          albumFolderMap.set(a, { folderName: `No caption_${noCapCounterGlobal} (photo album ${noCapCounterGlobal})`, isUnnamed: true, sender: info.sender });
        }
      }'''

new = '''      // For each album, find next text from same sender within 5 minutes for each album
      for (const [a, info] of albumToSender) {
        const albumTs = info.ts;
        // 1) Check if album has caption
        let albumCaption = albumCaps.get(a) || '';
        if (!albumCaption) {
          const lm = allLiveById.get(a);
          albumCaption = getMsgBody(lm);
        }
        if (albumCaption && albumCaption.trim()) {
          albumFolderMap.set(a, { folderName: albumCaption.trim(), isUnnamed: false, sender: info.sender });
          continue;
        }
        // 2) Look for next text from same sender within 5 minutes
        let foundFolder = '';
        for (let i = 0; i < allChatMsgs.length; i++) {
          const m = allChatMsgs[i];
          const mTs = Number(m.t) || 0;
          if (mTs <= albumTs) continue;
          if (mTs - albumTs > 300) break;
          const mid = String(m.id || '');
          const lm = allLiveById.get(mid);
          const mSenderKey = getMsgAuthorKey(m) || getMsgAuthorKey(lm) || '';
          const mSender = getMsgSender(m, chatId, lm);
          const sameSender = (info.senderKey && mSenderKey && info.senderKey === mSenderKey) || (info.sender && mSender && info.sender === mSender);
          if (!sameSender) continue;
          if (isTextOnlyMsg(lm || m)) {
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
          // 3) Use No Caption_HHMM with album upload time
          const d = new Date(albumTs * 1000);
          const hhmm = String(d.getHours()).padStart(2,'0') + String(d.getMinutes()).padStart(2,'0');
          albumFolderMap.set(a, { folderName: `No Caption_${hhmm}`, isUnnamed: true, sender: info.sender });
        }
      }'''

if old in s:
    s = s.replace(old, new)
    print('replaced')
else:
    print('not found')

with open('docs/wps-script.js','w',encoding='utf-8') as f:
    f.write(s)
