(function () {
  // Extract all http(s) links from the current page
  const links = Array.from(document.querySelectorAll('a'))
    .map(a => a.href)
    .filter(href => href && href.startsWith('http'));

  console.log("Extracted URLs:", links);

  // Send the list of URLs to the popup
  chrome.runtime.sendMessage({ type: "urlList", urls: links });
})();
(function () {
  // Add highlight style
  const style = document.createElement('style');
  style.textContent = `
    .safe-surf-highlight {
      background: #ffd6d6;
      border-radius: 5px;
      box-shadow: 0 2px 8px rgba(79,140,255,0.15);
      transition: background 0.2s;
    }
  `;
  document.head.appendChild(style);

  // Extract and highlight all http(s) links
  const links = Array.from(document.querySelectorAll('a'))
    .filter(a => a.href && a.href.startsWith('http'));

  links.forEach(a => a.classList.add('safe-surf-highlight'));

  console.log("Extracted URLs:", links.map(a => a.href));

  // Send the list of URLs to the popup
  chrome.runtime.sendMessage({ type: "urlList", urls: links.map(a => a.href) });
})();