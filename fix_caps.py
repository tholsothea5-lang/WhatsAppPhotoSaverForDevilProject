with open('docs/wps-script.js', 'r', encoding='utf-8') as f:
    s = f.read()

# Add albumCaps collection
old = '''      // Find folder name for each album: 1) album caption, 2) next text from same sender within 5 min, 3) No Caption_HHMM
      for (const [a, info] of albumToSender) {'''

new = '''      // Collect album captions
      const albumCaps = new Map();
      for (const a of albumKeys) {
        const lm = liveById.get(a) || allLiveById.get(a);
        const cap = getMsgBody(lm);
        if (cap && cap.trim()) albumCaps.set(a, cap.trim());
      }
      
      // Find folder name for each album: 1) album caption, 2) next text from same sender within 5 min, 3) No Caption_HHMM
      for (const [a, info] of albumToSender) {'''

if old in s:
    s = s.replace(old, new)
    print('ok')
else:
    print('no')

with open('docs/wps-script.js', 'w', encoding='utf-8') as f:
    f.write(s)
