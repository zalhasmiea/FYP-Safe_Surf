document.addEventListener('DOMContentLoaded', () => {
  const scanBtn = document.getElementById('scanBtn');
  const resultsEl = document.getElementById('results');

  scanBtn.addEventListener('click', async () => {
    resultsEl.innerHTML = '<p class="placeholder">Scanning...</p>';
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ["content.js"]
    });
  });

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "urlList") {
      resultsEl.innerHTML =`<div><strong>Found ${message.urls.length}</strong></div>`;
    }
  });
});