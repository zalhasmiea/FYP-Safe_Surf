document.getElementById('checkBtn').addEventListener('click', async () => {
    const urlInput = document.getElementById('urlInput').value.trim();
    const resultArea = document.getElementById('result-area');
    const verdictEl = document.getElementById('verdict');
    const breakdownEl = document.getElementById('breakdown');
    const cardEl = document.getElementById('resultCard');
  
    if (!urlInput) {
      alert("Please enter a URL first!");
      return;
    }
  
    // Show Loading
    resultArea.style.display = "block";
    verdictEl.innerText = "Analyzing...";
    verdictEl.style.color = "#333";
    breakdownEl.innerText = "Running 5 AI Models...";
    cardEl.className = "card"; 
  
    try {
      const response = await fetch("http://127.0.0.1:8000/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ urls: [urlInput] })
      });
  
      const data = await response.json();
      const result = data.details[0]; 
  
      // Display Result
      verdictEl.innerText = result.status.toUpperCase();
      
      // Color Logic
      if (result.status === "Benign") {
        cardEl.className = "card safe";
        verdictEl.style.color = "green";
      } else if (result.status === "Phishing") {
        cardEl.className = "card phishing";
        verdictEl.style.color = "#e67e22"; 
      } else if (result.status === "Defacement") {
        cardEl.className = "card defacement"; // Optional: styled like Benign or Warning
        verdictEl.style.color = "#d68910";
      } else { 
        cardEl.className = "card malware";
        verdictEl.style.color = "#c0392b"; 
      }
  
      // CLEAN DISPLAY: Remove (w=...) and (Manual List)
      const modelString = Object.entries(result.models)
        .map(([k, v]) => {
            const cleanValue = v.replace(/\s*\(.*?\)/g, "").trim();
            return `<b>${k}:</b> ${cleanValue}`;
        })
        .join("<br>");
      
      breakdownEl.innerHTML = modelString;
  
    } catch (error) {
      console.error(error);
      verdictEl.innerText = "Connection Error";
      verdictEl.style.color = "black";
      breakdownEl.innerText = "Could not connect to Python Backend. Is main.py running?";
    }
});