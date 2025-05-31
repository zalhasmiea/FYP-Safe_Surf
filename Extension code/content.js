(function () {
  // Extract all http(s) links from the current page
  const links = Array.from(document.querySelectorAll('a'))
    .map(a => a.href)
    .filter(href => href && href.startsWith('http'));

  console.log("Extracted URLs:", links);

  // Send the list of URLs to the popup
  chrome.runtime.sendMessage({ type: "urlList", urls: links });
})();