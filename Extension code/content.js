(function () {
  console.log("Safe Surf: Starting Scan...");

  // 1. Setup the Highlight Style (Only adds it if missing)
  if (!document.getElementById('safe-surf-style')) {
    const style = document.createElement('style');
    style.id = 'safe-surf-style';
    style.textContent = `
      .safe-surf-highlight {
        border: 2px solid #4f8cff !important;
        background-color: rgba(79, 140, 255, 0.1) !important;
        transition: all 0.2s;
      }
    `;
    document.head.appendChild(style);
  }

  // 2. ALWAYS Extract Links (This was the missing part on the 2nd click!)
  const links = Array.from(document.querySelectorAll('a'))
    .filter(a => a.href && a.href.startsWith('http'));

  // 3. Highlight them
  links.forEach(a => a.classList.add('safe-surf-highlight'));

  // 4. Send Results to Popup
  const urlList = links.map(a => a.href);
  console.log(`Found ${urlList.length} links. Sending to popup...`);
  
  chrome.runtime.sendMessage({ type: "urlList", urls: urlList });

})();