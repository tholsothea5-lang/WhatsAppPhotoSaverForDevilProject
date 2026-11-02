import re

with open('docs/wps-script.js', 'r', encoding='utf-8') as f:
    s = f.read()

old = r'''      // Find next text from same sender within 5 minutes for each album
      for \(const \[a, info\] of albumToSender\) \{
        const albumTs = info\.ts;
        let foundFolder = '';
        // Look through timeline after album
        for \(let i = 0; i < allChatMsgs\.length; i\+\+\) \{
          const m = allChatMsgs\[i\];
          const mTs = Number\(m\.t\) \|\| 0;
          if \(mTs <= albumTs\) continue;
          if \(mTs - albumTs > 300\) break; // 5 minutes = 300 seconds
          const mid = String\(m\.id \|\| ''\);
          const lm = allLiveById\.get\(mid\);
          // Check if same sender
          const mSenderKey = getMsgAuthorKey\(m\) \|\| getMsgAuthorKey\(lm\) \|\| '';
          const mSender = getMsgSender\(m, chatId, lm\);
          const sameSender = \(info\.senderKey && mSenderKey && info\.senderKey === mSenderKey\) \|\| 
                             \(info\.sender && mSender && info\.sender === mSender\);
          if \(!sameSender\) continue;
          if \(isTextOnlyMsg\(lm \|\| m\) \|\| \(getMsgBody\(lm \|\| m\) && !m\.isMediaMsg && m\.type !== 'image' && m\.type !== 'video'\)\) \{
            const body = getMsgBody\(lm \|\| m\);
            if \(body && body\.trim\(\)\) \{
              foundFolder = body\.trim\(\);
              break;
            \}
          \}
        \}
        if \(foundFolder\) \{
          albumFolderMap\.set\(a, \{ folderName: foundFolder, isUnnamed: false, sender: info\.sender \}\);
        \} else \{
          const d = new Date\(albumTs \* 1000\);
          const dt = `\$\{d\.getFullYear\(\)\}-\$\{pad\(d\.getMonth\(\)\+1\)\}-\$\{pad\(d\.getDate\(\)\)\}_\$\{pad\(d\.getHours\(\)\)\}\$\{pad\(d\.getMinutes\(\)\)\}\$\{pad\(d\.getSeconds\(\)\)\}`;
          const short = String\(a\)\.replace\(/\[\^a-zA-Z0-9\]/g,''\)\.slice\(-6\) \|\| 'x';
          albumFolderMap\.set\(a, \{ folderName: `Unnamed_\$\{safe\(info\.sender, 30\)\}_\$\{dt\}_\$\{short\}`, isUnnamed: true, sender: info\.sender \}\);
        \}
      \}'''

new = '''      // Find folder name for each album: 1) album caption, 2) next text from same sender within 5 min, 3) No Caption_HHMM
      for (const [a, info] of albumToSender) {
        const albumTs = info.ts;
        // 1) Check album caption from hydrated models first
        let albumCaption = albumCaps.get(a) || '';
        if (!albumCaption) {
          const lm = allLiveById.get(a);
          albumCaption = getMsgBody(lm) || '';
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

m = re.search(old, s)
if m:
    s2 = s.replace(m.group(0), new)
    with open('docs/wps-script.js', 'w', encoding='utf-8') as f:
        f.write(s2)
    print('replaced')
else:
    print('not found')
