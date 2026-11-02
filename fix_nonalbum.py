with open('docs/wps-script.js', 'r', encoding='utf-8') as f:
    s = f.read()

old = '''        } else {
          // Not in album - look for next text from same sender within 5 minutes
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
            noCapCounterGlobal++;
            folderName = `No caption_${noCapCounterGlobal} (photo album ${noCapCounterGlobal})`;
            isUnnamed = true;
          }
        }'''

new = '''        } else {
          // Not in album - look for next text from same sender within 5 minutes
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
            const hhmm = String(d.getHours()).padStart(2,'0') + String(d.getMinutes()).padStart(2,'0');
            folderName = `No Caption_${hhmm}`;
            isUnnamed = true;
          }
        }'''

if old in s:
    s = s.replace(old, new)
    print('replaced')
else:
    print('not found')

with open('docs/wps-script.js', 'w', encoding='utf-8') as f:
    f.write(s)
