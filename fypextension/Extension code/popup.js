document.addEventListener('DOMContentLoaded', () => {
    const scanBtn = document.getElementById('scanBtn');
    const resultsEl = document.getElementById('results');
    const safeEl = document.getElementById('safeUrls');
    const malEl = document.getElementById('maliciousUrls');
    const reportBtn = document.getElementById('viewReportBtn');
    
    // Dashboard Button Logic
    const dashboardBtn = document.getElementById('dashboardBtn');
    if (dashboardBtn) {
        dashboardBtn.addEventListener('click', () => {
            chrome.tabs.create({ url: 'dashboard.html' });
        });
    }
  
    let lastScanDetails = [];
  
    scanBtn.addEventListener('click', async () => {
      resultsEl.innerText = 'Scanning...';
      safeEl.innerText = 'Benign: -';
      malEl.innerText = 'Threats: -';
      
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      
      chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ["content.js"]
      });
    });
  
    chrome.runtime.onMessage.addListener(async (message, sender, sendResponse) => {
      if (message.type === "urlList") {
        const urls = message.urls;
        resultsEl.innerText = `${urls.length} Found`;
        
        if (urls.length === 0) return;
  
        try {
          resultsEl.innerText = `Analyzing...`;
          
          const response = await fetch("http://127.0.0.1:8000/predict", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ urls: urls })
          });
  
          const data = await response.json();
          lastScanDetails = data.details; 
  
          // Math Fix (Handles missing keys safely)
          const benignCount = (data.summary.Benign || 0) + (data.summary.Defacement || 0);
          const threatCount = (data.summary.Phishing || 0) + (data.summary.Malware || 0);
  
          safeEl.innerText = `Benign: ${benignCount}`;
          safeEl.style.color = "green";
          
          malEl.innerText = `Threats: ${threatCount}`;
          malEl.style.color = threatCount > 0 ? "#e53e3e" : "green"; 
  
          resultsEl.innerText = `${urls.length} (Done)`;
          
        } catch (error) {
          console.error(error);
          resultsEl.innerText = "Error";
          malEl.innerText = "Backend Offline?";
        }
      }
    });
  
    // --- CLEAN REPORT GENERATION ---
    reportBtn.addEventListener('click', () => {
      if (lastScanDetails.length === 0) {
        alert("Please scan a page first.");
        return;
      }

      let reportHTML = `
        <html>
          <head>
            <title>Safe Surf Report</title>
            <style>
              body { font-family: 'Segoe UI', sans-serif; padding: 20px; }
              h2 { color: #333; }
              table { border-collapse: collapse; width: 100%; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
              th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
              th { background-color: #f8f9fa; }
              
              .status-Benign { color: green; font-weight: bold; background-color: #e8f5e9; }
              .status-Defacement { color: green; font-weight: bold; background-color: #e8f5e9; } /* Defacement shown as Safe color */
              .status-Phishing { color: #e67e22; font-weight: bold; background-color: #fae5d3; }
              .status-Malware { color: #c0392b; font-weight: bold; background-color: #f9e79f; }
              
              .model-votes { font-size: 0.9em; color: #555; }
            </style>
          </head>
          <body>
            <h2>🛡️ Safe Surf Analysis</h2>
            <table>
              <tr>
                <th>URL</th>
                <th>Final Verdict</th>
                <th>AI Consensus</th>
              </tr>
      `;

      lastScanDetails.forEach(item => {
        // CLEANER FUNCTION: Removes "(w=1)" and "(Manual List)"
        let modelString = Object.entries(item.models)
          .map(([k, v]) => {
            const cleanValue = v.replace(/\s*\(.*?\)/g, "").trim(); // Regex removes (...)
            return `<b>${k}:</b> ${cleanValue}`;
          })
          .join(" | ");

        reportHTML += `
          <tr>
            <td style="word-break: break-all; max-width: 350px;">${item.url}</td>
            <td class="status-${item.status}">${item.status}</td>
            <td class="model-votes">${modelString}</td>
          </tr>
        `;
      });

      reportHTML += `</table></body></html>`;

      const win = window.open("", "Report", "width=900,height=600");
      win.document.write(reportHTML);
    });
});