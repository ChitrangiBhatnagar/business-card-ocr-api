/**
 * Business Card Scanner - Vanilla JavaScript Integration
 * 
 * Copy this code into your SalesCentri website or any HTML page.
 * No React/TypeScript dependencies required.
 * 
 * Usage: Add a <div id="business-card-scanner"></div> to your page
 */

// Configuration - Update this to your deployed API URL
const OCR_API_URL = "https://business-card-ocr-api.onrender.com";

// Initialize the scanner
function initBusinessCardScanner(containerId = "business-card-scanner") {
  const container = document.getElementById(containerId);
  if (!container) {
    console.error(`Container #${containerId} not found`);
    return;
  }

  // State
  let results = [];
  let isProcessing = false;

  // Render the UI
  container.innerHTML = `
    <div class="bcs-container">
      <h2 class="bcs-title">📇 Business Card Scanner</h2>
      
      <!-- Upload Zone -->
      <div id="bcs-dropzone" class="bcs-dropzone">
        <input type="file" id="bcs-file-input" accept="image/*" multiple hidden>
        <div class="bcs-dropzone-content">
          <div class="bcs-icon">📸</div>
          <p class="bcs-text">Drag & drop business cards or click to upload</p>
          <p class="bcs-subtext">Supports PNG, JPG, WEBP • Multiple cards supported</p>
        </div>
        <div id="bcs-loading" class="bcs-loading" style="display:none">
          <div class="bcs-spinner"></div>
          <p>Processing business cards...</p>
        </div>
      </div>

      <!-- Error Message -->
      <div id="bcs-error" class="bcs-error" style="display:none"></div>

      <!-- Results -->
      <div id="bcs-results" class="bcs-results" style="display:none">
        <h3 class="bcs-results-title">Extracted Contacts (<span id="bcs-count">0</span>)</h3>
        <div id="bcs-results-list" class="bcs-results-list"></div>
        
        <!-- Bulk Actions -->
        <div class="bcs-actions">
          <button id="bcs-export-btn" class="bcs-btn bcs-btn-success">Export All to CRM</button>
          <button id="bcs-clear-btn" class="bcs-btn bcs-btn-secondary">Clear Results</button>
        </div>
      </div>
    </div>
  `;

  // Add styles
  addStyles();

  // Get elements
  const dropzone = document.getElementById("bcs-dropzone");
  const fileInput = document.getElementById("bcs-file-input");
  const loading = document.getElementById("bcs-loading");
  const errorDiv = document.getElementById("bcs-error");
  const resultsDiv = document.getElementById("bcs-results");
  const resultsList = document.getElementById("bcs-results-list");
  const countSpan = document.getElementById("bcs-count");
  const exportBtn = document.getElementById("bcs-export-btn");
  const clearBtn = document.getElementById("bcs-clear-btn");

  // Event Listeners
  dropzone.addEventListener("click", () => fileInput.click());
  
  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("bcs-dragover");
  });
  
  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("bcs-dragover");
  });
  
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("bcs-dragover");
    handleFiles(e.dataTransfer.files);
  });

  fileInput.addEventListener("change", (e) => {
    handleFiles(e.target.files);
  });

  exportBtn.addEventListener("click", exportToCRM);
  clearBtn.addEventListener("click", clearResults);

  // Process files
  async function handleFiles(files) {
    if (isProcessing || files.length === 0) return;
    
    isProcessing = true;
    loading.style.display = "flex";
    errorDiv.style.display = "none";
    dropzone.querySelector(".bcs-dropzone-content").style.display = "none";

    for (const file of files) {
      try {
        const result = await processCard(file);
        results.push({ ...result, filename: file.name });
        renderResults();
      } catch (err) {
        results.push({ 
          success: false, 
          error: err.message, 
          filename: file.name 
        });
        renderResults();
      }
    }

    isProcessing = false;
    loading.style.display = "none";
    dropzone.querySelector(".bcs-dropzone-content").style.display = "block";
    fileInput.value = "";
  }

  // Call the OCR API
  async function processCard(file) {
    const formData = new FormData();
    formData.append("image", file);

    const response = await fetch(`${OCR_API_URL}/api/process`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  }

  // Render results
  function renderResults() {
    const successResults = results.filter(r => r.success);
    countSpan.textContent = successResults.length;
    
    if (results.length > 0) {
      resultsDiv.style.display = "block";
    }

    resultsList.innerHTML = results.map((result, index) => {
      if (!result.success) {
        return `
          <div class="bcs-card bcs-card-error">
            <span class="bcs-error-icon">❌</span>
            <span>${result.filename}: ${result.error || "Processing failed"}</span>
          </div>
        `;
      }

      const contact = result.contact_data || {};
      const enrichment = result.company_enrichment || {};
      const fieldConf = result.field_confidence || {};
      const logoUrl = contact.company_logo || enrichment.logo_url;
      const linkedinUrl = contact.linkedin || enrichment.linkedin_url;
      const confidence = contact.confidence_score || 0;
      const confClass = confidence >= 0.8 ? "high" : confidence >= 0.5 ? "medium" : "low";

      return `
        <div class="bcs-card">
          <div class="bcs-card-content">
            ${logoUrl ? `
              <div class="bcs-logo">
                <img src="${logoUrl}" alt="Logo" onerror="this.style.display='none'">
              </div>
            ` : ""}
            
            <div class="bcs-info">
              <div class="bcs-info-main">
                <p class="bcs-name">${contact.name || "Unknown"}</p>
                <p class="bcs-title-text">${contact.title || ""}</p>
                <p class="bcs-company">${contact.company || ""}</p>
                ${contact.industry || enrichment.industry ? `
                  <span class="bcs-industry">${contact.industry || enrichment.industry}</span>
                ` : ""}
              </div>
              
              <div class="bcs-contact">
                ${contact.email ? `
                  <p>📧 ${contact.email}
                    ${fieldConf.email ? `<span class="bcs-field-conf bcs-conf-${fieldConf.email >= 0.8 ? 'high' : fieldConf.email >= 0.5 ? 'medium' : 'low'}">${Math.round(fieldConf.email * 100)}%</span>` : ""}
                  </p>
                ` : ""}
                ${contact.phone && contact.phone.length > 0 ? `
                  <p>📱 ${Array.isArray(contact.phone) ? contact.phone.join(", ") : contact.phone}</p>
                ` : ""}
                ${contact.website ? `<p>🌐 ${contact.website}</p>` : ""}
                ${linkedinUrl ? `<a href="${linkedinUrl}" target="_blank" class="bcs-linkedin">🔗 LinkedIn</a>` : ""}
              </div>
            </div>
            
            <div class="bcs-meta">
              <span class="bcs-confidence bcs-conf-${confClass}">
                ${Math.round(confidence * 100)}% confidence
              </span>
              <span class="bcs-method">${result.ocr_method === "gemini_fallback" ? "🤖 AI Enhanced" : "⚡ Fast OCR"}</span>
              ${result.processing_time_ms ? `<span class="bcs-time">${result.processing_time_ms}ms</span>` : ""}
              <button class="bcs-btn bcs-btn-primary bcs-btn-sm" onclick="window.addContactToCRM(${index})">
                Add to CRM
              </button>
            </div>
          </div>
        </div>
      `;
    }).join("");
  }

  // Export function (customize this for your CRM)
  window.addContactToCRM = function(index) {
    const result = results[index];
    if (!result || !result.success) return;
    
    const contact = result.contact_data;
    console.log("Adding to CRM:", contact);
    
    // TODO: Replace with your actual CRM API call
    // fetch('/api/contacts', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify(contact)
    // });
    
    alert(`Added ${contact.name || contact.email} to CRM!`);
  };

  function exportToCRM() {
    const contacts = results
      .filter(r => r.success)
      .map(r => r.contact_data);
    
    console.log("Exporting contacts:", contacts);
    
    // TODO: Replace with your actual bulk export
    alert(`Exporting ${contacts.length} contacts to CRM...`);
  }

  function clearResults() {
    results = [];
    resultsDiv.style.display = "none";
    resultsList.innerHTML = "";
    countSpan.textContent = "0";
  }
}

// Add CSS styles
function addStyles() {
  if (document.getElementById("bcs-styles")) return;
  
  const style = document.createElement("style");
  style.id = "bcs-styles";
  style.textContent = `
    .bcs-container {
      max-width: 900px;
      margin: 0 auto;
      padding: 24px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    .bcs-title {
      font-size: 1.5rem;
      font-weight: bold;
      color: #fff;
      margin-bottom: 24px;
    }
    
    .bcs-dropzone {
      border: 2px dashed #4a5568;
      border-radius: 12px;
      padding: 48px;
      text-align: center;
      cursor: pointer;
      transition: all 0.2s;
      background: #1a1a2e;
    }
    
    .bcs-dropzone:hover, .bcs-dragover {
      border-color: #3b82f6;
      background: rgba(59, 130, 246, 0.1);
    }
    
    .bcs-icon { font-size: 3rem; margin-bottom: 16px; }
    .bcs-text { color: #e2e8f0; margin-bottom: 8px; }
    .bcs-subtext { color: #718096; font-size: 0.875rem; }
    
    .bcs-loading {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
      color: #a0aec0;
    }
    
    .bcs-spinner {
      width: 48px;
      height: 48px;
      border: 4px solid #3b82f6;
      border-top-color: transparent;
      border-radius: 50%;
      animation: bcs-spin 1s linear infinite;
    }
    
    @keyframes bcs-spin {
      to { transform: rotate(360deg); }
    }
    
    .bcs-error {
      margin-top: 16px;
      padding: 16px;
      background: rgba(239, 68, 68, 0.2);
      border: 1px solid #ef4444;
      border-radius: 8px;
      color: #fca5a5;
    }
    
    .bcs-results {
      margin-top: 32px;
    }
    
    .bcs-results-title {
      font-size: 1.25rem;
      font-weight: 600;
      color: #fff;
      margin-bottom: 16px;
    }
    
    .bcs-results-list {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    
    .bcs-card {
      background: #2d3748;
      border-radius: 12px;
      padding: 20px;
      border: 1px solid #4a5568;
    }
    
    .bcs-card-error {
      display: flex;
      align-items: center;
      gap: 8px;
      color: #fca5a5;
    }
    
    .bcs-card-content {
      display: flex;
      gap: 20px;
      align-items: flex-start;
    }
    
    .bcs-logo img {
      width: 64px;
      height: 64px;
      border-radius: 8px;
      background: #fff;
      padding: 8px;
      object-fit: contain;
    }
    
    .bcs-info {
      flex: 1;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }
    
    .bcs-name { font-size: 1.125rem; font-weight: 600; color: #fff; }
    .bcs-title-text { color: #a0aec0; }
    .bcs-company { color: #63b3ed; }
    
    .bcs-industry {
      display: inline-block;
      margin-top: 8px;
      padding: 2px 8px;
      background: rgba(139, 92, 246, 0.2);
      color: #a78bfa;
      border-radius: 4px;
      font-size: 0.75rem;
    }
    
    .bcs-contact p { color: #cbd5e0; margin: 4px 0; }
    .bcs-linkedin { color: #63b3ed; text-decoration: none; }
    .bcs-linkedin:hover { text-decoration: underline; }
    
    .bcs-meta {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 8px;
    }
    
    .bcs-confidence {
      padding: 4px 12px;
      border-radius: 9999px;
      font-size: 0.875rem;
      font-weight: 500;
    }
    
    .bcs-conf-high { background: rgba(34, 197, 94, 0.2); color: #4ade80; }
    .bcs-conf-medium { background: rgba(234, 179, 8, 0.2); color: #facc15; }
    .bcs-conf-low { background: rgba(239, 68, 68, 0.2); color: #f87171; }
    
    .bcs-field-conf {
      margin-left: 8px;
      padding: 1px 6px;
      border-radius: 4px;
      font-size: 0.7rem;
    }
    
    .bcs-method { color: #718096; font-size: 0.75rem; }
    .bcs-time { color: #4a5568; font-size: 0.75rem; }
    
    .bcs-actions {
      margin-top: 24px;
      display: flex;
      gap: 16px;
    }
    
    .bcs-btn {
      padding: 12px 24px;
      border-radius: 8px;
      font-weight: 500;
      cursor: pointer;
      border: none;
      transition: all 0.2s;
    }
    
    .bcs-btn-sm { padding: 8px 16px; font-size: 0.875rem; }
    .bcs-btn-primary { background: #3b82f6; color: #fff; }
    .bcs-btn-primary:hover { background: #2563eb; }
    .bcs-btn-success { background: #22c55e; color: #fff; }
    .bcs-btn-success:hover { background: #16a34a; }
    .bcs-btn-secondary { background: #4a5568; color: #fff; }
    .bcs-btn-secondary:hover { background: #374151; }
    
    @media (max-width: 768px) {
      .bcs-card-content { flex-direction: column; }
      .bcs-info { grid-template-columns: 1fr; }
      .bcs-meta { align-items: flex-start; flex-direction: row; flex-wrap: wrap; }
    }
  `;
  document.head.appendChild(style);
}

// Auto-initialize if container exists
document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("business-card-scanner")) {
    initBusinessCardScanner();
  }
});
