document.addEventListener('DOMContentLoaded', () => {
  const scanBtn = document.getElementById('scanBtn');
  const resultsEl = document.getElementById('results');

  scanBtn.addEventListener('click', async () => {
    // TODO: Inject content script and retrieve URL summary.
    resultsEl.innerHTML = '<p class="placeholder">Scanning... (functionality coming soon)</p>';
  });
});
