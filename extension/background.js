chrome.action.onClicked.addListener(async (tab) => {
  if (!tab.url || !tab.url.includes('web.whatsapp.com')) {
    chrome.tabs.create({ url: 'https://web.whatsapp.com' });
    return;
  }
  await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    files: ['content.js']
  });
});
