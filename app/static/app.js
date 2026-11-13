// ============================================
// Global State
// ============================================
let currentData = null;
let missingSchemas = [];

// ============================================
// Main Analyze Function
// ============================================
document.getElementById('analyzeBtn').addEventListener('click', analyze);
document.getElementById('urlInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') analyze();
});

async function analyze() {
    if (window.__logoSwitchTrigger) window.__logoSwitchTrigger();

    const urlInput = document.getElementById('urlInput');
    const url = urlInput.value.trim();
    
    if (!url) {
        showError('Please enter a URL');
        return;
    }
    
    // Show loading, hide results and errors
    document.getElementById('loading').style.display = 'block';
    document.getElementById('results').style.display = 'none';
    document.getElementById('error').style.display = 'none';
    document.getElementById('analyzeBtn').disabled = true;
    
    try {
        const selectedModel = document.getElementById('modelSelect')?.value || 'gemini';
        const response = await fetch('/schematoaio/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url, model: selectedModel })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Analysis failed');
        }
        
        const data = await response.json();
        currentData = data;
        displayResults(data);
        
    } catch (error) {
        showError(error.message);
    } finally {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('analyzeBtn').disabled = false;
    }
}

function showError(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}

// ============================================
// Display Results
// ============================================
function displayResults(data) {
    document.getElementById('results').style.display = 'block';
    
    // Display each section with error handling
    try {
        displayGEOScore(data.geo_score);
    } catch (e) {
        console.error('Error displaying GEO score:', e);
    }
    
    try {
        displayContentFreshness(data.content_freshness);
    } catch (e) {
        console.error('Error displaying content freshness:', e);
    }
    
    try {
        displayLlmsTxt(data.llms_txt);
    } catch (e) {
        console.error('Error displaying llms.txt status:', e);
    }
    
    try {
        displaySchemaInventory(data.schema_inventory);
    } catch (e) {
        console.error('Error displaying schema inventory:', e);
    }
    
    try {
        displayIssues(data.issues);
    } catch (e) {
        console.error('Error displaying issues:', e);
    }
    
    try {
        displayContentRecs(data.content_recommendations);
    } catch (e) {
        console.error('Error displaying content recommendations:', e);
    }
    
    try {
        displaySchemaComparison(data.current_jsonld, data.improved_jsonld);
    } catch (e) {
        console.error('Error displaying schema comparison:', e);
    }
    
    // Initialize tab navigation
    initializeTabs();
}

// ============================================
// Tab Navigation
// ============================================
function initializeTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.dataset.tab;
            switchTab(tabName, btn);
        });
    });
}

let _issuesOriginalNextSibling = undefined;
function reorderIssuesSection(promoteToTop) {
    const issues = document.querySelector('.issues-section');
    if (!issues) return;
    const parent = issues.parentElement;
    if (!parent) return;

    if (_issuesOriginalNextSibling === undefined) {
        _issuesOriginalNextSibling = issues.nextElementSibling;
    }

    if (promoteToTop) {
        const firstVisible = Array.from(parent.querySelectorAll(':scope > [data-section]')).find(
            (el) => el !== issues && !el.classList.contains('hidden')
        );
        if (firstVisible && firstVisible !== issues) {
            parent.insertBefore(issues, firstVisible);
        }
    } else {
        if (_issuesOriginalNextSibling && _issuesOriginalNextSibling.parentElement === parent) {
            parent.insertBefore(issues, _issuesOriginalNextSibling);
        } else {
            parent.appendChild(issues);
        }
    }
}

function switchTab(tabName, clickedBtn) {
    // Update active tab button
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    clickedBtn.classList.add('active');

    // Show/hide sections based on tab
    const sections = document.querySelectorAll('[data-section]');

    if (tabName === 'all') {
        // Show all sections
        sections.forEach(section => {
            section.classList.remove('hidden');
        });
    } else {
        // Each section's data-section is a space-separated list of tabs it appears on.
        sections.forEach(section => {
            const sectionTabs = (section.dataset.section || '').split(/\s+/).filter(Boolean);
            if (sectionTabs.includes(tabName)) {
                section.classList.remove('hidden');
            } else {
                section.classList.add('hidden');
            }
        });
    }

    // Reward: show every available recommendation when the user opens the Recommendations tab
    if (currentData) {
        const recsForThisTab = (tabName === 'recommendations' && currentData.all_content_recommendations?.length)
            ? currentData.all_content_recommendations
            : (currentData.content_recommendations || []);
        displayContentRecs(recsForThisTab);
    }

    // On the Recommendations tab, surface Actionable Issues first.
    reorderIssuesSection(tabName === 'recommendations');

    // Smooth scroll to results
    document.getElementById('results').scrollIntoView({
        behavior: 'smooth',
        block: 'start'
    });
}

// ============================================
// GEO Score Display with Circular Ring
// ============================================
function displayGEOScore(geoScore) {
    const scoreNumber = document.getElementById('scoreNumber');
    const scoreLabel = document.getElementById('scoreLabel');
    const scoreRing = document.getElementById('scoreRing');
    const rulesDiv = document.getElementById('ruleResults');
    
    const score = geoScore.total_score;
    const maxScore = geoScore.max_score;
    
    // Determine color and label based on score
    let colorClass, labelText, ringColor;
    if (score >= 70) {
        colorClass = 'score-excellent';
        labelText = 'Excellent';
        ringColor = '#34A853';
    } else if (score >= 40) {
        colorClass = 'score-good';
        labelText = 'Good Progress';
        ringColor = '#FBBC04';
    } else {
        colorClass = 'score-poor';
        labelText = 'Needs Improvement';
        ringColor = '#EA4335';
    }
    
    // Update score display
    scoreNumber.textContent = Math.round(score);
    scoreNumber.className = `score-number ${colorClass}`;
    scoreLabel.textContent = `${labelText} (out of ${maxScore})`;
    
    // Animate circular ring
    const circumference = 2 * Math.PI * 90; // radius = 90
    const percentage = score / maxScore;
    const offset = circumference - (percentage * circumference);
    
    scoreRing.style.stroke = ringColor;
    
    // Trigger animation
    setTimeout(() => {
        scoreRing.style.strokeDashoffset = offset;
    }, 100);
    
    // Display rules with progress bars
    rulesDiv.innerHTML = '';
    geoScore.rules.forEach((rule, index) => {
        const ruleDiv = document.createElement('div');
        ruleDiv.className = 'rule-item';
        
        const ruleName = rule.rule_name.replace(/_/g, ' ');
        const percentage = (rule.score / rule.max_score) * 100;
        
        // Determine progress bar color
        let progressClass;
        if (percentage >= 84) { // 12/14.3 ≈ 84%
            progressClass = 'progress-excellent';
        } else if (percentage >= 56) { // 8/14.3 ≈ 56%
            progressClass = 'progress-good';
        } else {
            progressClass = 'progress-poor';
        }
        
        ruleDiv.innerHTML = `
            <div class="rule-header">
                <span class="rule-name">${ruleName}</span>
                <span class="rule-score ${progressClass}">${rule.score.toFixed(1)}/${rule.max_score}</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill ${progressClass}" data-width="${percentage}"></div>
            </div>
            <p class="rule-message">${rule.message}</p>
        `;
        
        rulesDiv.appendChild(ruleDiv);
        
        // Animate progress bar with stagger
        setTimeout(() => {
            const progressFill = ruleDiv.querySelector('.progress-fill');
            progressFill.style.width = `${percentage}%`;
        }, 200 + (index * 100));
    });
}

// ============================================
// Content Freshness Display
// ============================================
function displayContentFreshness(freshness) {
    const freshnessDiv = document.getElementById('freshnessDisplay');
    
    // Handle missing freshness data or Unknown status
    if (!freshness || !freshness.status || freshness.status === 'Unknown') {
        freshnessDiv.innerHTML = `
            <div class="freshness-status freshness-unknown">
                <div class="freshness-header">
                    <span class="freshness-icon">📅</span>
                    <span class="freshness-label">No Date Found</span>
                </div>
                <p class="freshness-description">
                    No publication or modification date found in schema — consider adding <code>dateModified</code> to your structured data.
                </p>
                <div class="freshness-stat">
                    <strong>📊 AI Citation Insight:</strong> 76% of AI-cited content was updated within the last 30 days.
                </div>
            </div>
        `;
        return;
    }
    
    // Determine status styling
    let statusClass, statusIcon, statusDescription;
    
    switch(freshness.status) {
        case 'Fresh':
            statusClass = 'freshness-fresh';
            statusIcon = '✅';
            statusDescription = 'Content is up-to-date and recently published or modified';
            break;
        case 'Aging':
            statusClass = 'freshness-aging';
            statusIcon = '⚠️';
            statusDescription = 'Content is getting older - consider updating soon';
            break;
        case 'Stale':
            statusClass = 'freshness-stale';
            statusIcon = '❌';
            statusDescription = 'Content is outdated - update recommended';
            break;
        default:
            statusClass = 'freshness-unknown';
            statusIcon = '📅';
            statusDescription = 'No date information found in schema';
    }
    
    let detailsHTML = '';
    if (freshness.days_old !== null) {
        detailsHTML = `
            <div class="freshness-details">
                <p><strong>Days since last update:</strong> ${freshness.days_old}</p>
                <p><strong>Date found:</strong> ${new Date(freshness.date_found).toLocaleDateString()}</p>
                <p><strong>Source field:</strong> ${freshness.source_field}</p>
            </div>
        `;
    }
    
    freshnessDiv.innerHTML = `
        <div class="freshness-status ${statusClass}">
            <div class="freshness-header">
                <span class="freshness-icon">${statusIcon}</span>
                <span class="freshness-label">${freshness.status}</span>
            </div>
            <p class="freshness-description">${statusDescription}</p>
            ${detailsHTML}
        </div>
    `;
}

// ============================================
// llms.txt Status Display
// ============================================
function displayLlmsTxt(llmsTxt) {
    const llmsTxtDiv = document.getElementById('llmsTxtDisplay');
    
    // Handle missing llms.txt data gracefully
    if (!llmsTxt || !llmsTxt.status) {
        llmsTxtDiv.innerHTML = `
            <div class="llmstxt-status llmstxt-missing">
                <div class="llmstxt-header">
                    <span class="llmstxt-icon">🤖</span>
                    <span class="llmstxt-label">No llms.txt Detected</span>
                </div>
                <p class="llmstxt-description">
                    No llms.txt file detected — consider adding one to help AI crawlers understand your site's key content.
                </p>
                <div class="llmstxt-info">
                    <strong>💡 What is llms.txt?</strong> A standard file that helps AI systems discover and understand your most important content.
                </div>
            </div>
        `;
        return;
    }
    
    // Determine status styling
    let statusClass, statusIcon, statusDescription, detailsHTML;
    
    if (llmsTxt.status === 'Present') {
        statusClass = 'llmstxt-present';
        statusIcon = '✅';
        statusDescription = 'llms.txt file found! AI crawlers can discover your key content.';
        detailsHTML = `
            <div class="llmstxt-details">
                <p><strong>File URL:</strong> <a href="${llmsTxt.url}" target="_blank" rel="noopener">${llmsTxt.url}</a></p>
                ${llmsTxt.content_length ? `<p><strong>Content size:</strong> ${llmsTxt.content_length} characters</p>` : ''}
            </div>
        `;
    } else {
        statusClass = 'llmstxt-missing';
        statusIcon = '❌';
        statusDescription = 'No llms.txt file detected — consider adding one to help AI crawlers understand your site\'s key content.';
        detailsHTML = `
            <div class="llmstxt-info">
                <strong>💡 What is llms.txt?</strong> A standard file that helps AI systems discover and understand your most important content.
            </div>
        `;
    }
    
    llmsTxtDiv.innerHTML = `
        <div class="llmstxt-status ${statusClass}">
            <div class="llmstxt-header">
                <span class="llmstxt-icon">${statusIcon}</span>
                <span class="llmstxt-label">${llmsTxt.status}</span>
            </div>
            <p class="llmstxt-description">${statusDescription}</p>
            ${detailsHTML}
        </div>
    `;
}

// ============================================
// Schema Inventory Display
// ============================================
function displaySchemaInventory(inventory) {
    const statusDiv = document.getElementById('schemaStatus');
    const typesDiv = document.getElementById('schemaTypes');
    const toggleBtn = document.getElementById('toggleMissing');
    
    // Status badge
    const statusText = ['No schemas found', 'Some schemas present', 'Multiple schemas present'][inventory.status];
    const statusClass = ['status-none', 'status-some', 'status-multiple'][inventory.status];
    statusDiv.textContent = statusText;
    statusDiv.className = `status-badge ${statusClass}`;
    
    // Separate found and missing schemas
    const foundSchemas = [];
    missingSchemas = [];
    
    inventory.types_found.forEach(type => {
        if (type.found) {
            foundSchemas.push(type);
        } else {
            missingSchemas.push(type);
        }
    });
    
    // Display found schemas
    typesDiv.innerHTML = '';
    foundSchemas.forEach(type => {
        const schemaDiv = document.createElement('div');
        schemaDiv.className = 'schema-item found';
        
        // Determine dot color based on completeness
        const dotColor = type.status_message.toLowerCase().includes('complete') ? 'green' : 'yellow';
        
        schemaDiv.innerHTML = `
            <span class="status-dot ${dotColor}"></span>
            <div>
                <strong>${type.type_name}</strong>: ${type.status_message}
            </div>
        `;
        typesDiv.appendChild(schemaDiv);
    });
    
    // Display missing schemas (initially hidden)
    missingSchemas.forEach(type => {
        const schemaDiv = document.createElement('div');
        schemaDiv.className = 'schema-item missing';
        schemaDiv.style.display = 'none';
        
        schemaDiv.innerHTML = `
            <span class="status-dot gray"></span>
            <div>
                <strong>${type.type_name}</strong>: Not found
            </div>
        `;
        typesDiv.appendChild(schemaDiv);
    });
    
    // Show toggle button if there are missing schemas
    if (missingSchemas.length > 0) {
        toggleBtn.style.display = 'flex';
        toggleBtn.innerHTML = `Show all ${inventory.types_found.length} types <span class="toggle-icon">▼</span>`;
        
        // Add toggle functionality
        toggleBtn.onclick = toggleMissingSchemas;
    } else {
        toggleBtn.style.display = 'none';
    }
}

function toggleMissingSchemas() {
    const toggleBtn = document.getElementById('toggleMissing');
    const missingItems = document.querySelectorAll('.schema-item.missing');
    const isExpanded = toggleBtn.classList.contains('expanded');
    
    if (isExpanded) {
        // Collapse
        missingItems.forEach(item => {
            item.style.display = 'none';
        });
        toggleBtn.classList.remove('expanded');
        toggleBtn.innerHTML = `Show all ${missingItems.length + document.querySelectorAll('.schema-item.found').length} types <span class="toggle-icon">▼</span>`;
    } else {
        // Expand
        missingItems.forEach(item => {
            item.style.display = 'flex';
        });
        toggleBtn.classList.add('expanded');
        toggleBtn.innerHTML = `Hide missing types <span class="toggle-icon">▲</span>`;
    }
}

// ============================================
// Issues Display with Severity Dots
// ============================================
function displayIssues(issues) {
    const issuesList = document.getElementById('issuesList');
    issuesList.innerHTML = '';
    
    if (issues.length === 0) {
        issuesList.innerHTML = `
            <div class="issue-card">
                <div class="issue-header">
                    <span class="severity-dot" style="background: #34A853;"></span>
                    <h4 class="issue-title">No critical issues found!</h4>
                </div>
                <p class="issue-description">Your page is in good shape for AI search readiness.</p>
            </div>
        `;
        return;
    }
    
    issues.forEach(issue => {
        const issueCard = document.createElement('div');
        issueCard.className = 'issue-card';
        
        issueCard.innerHTML = `
            <div class="issue-header">
                <span class="severity-dot severity-${issue.severity}"></span>
                <h4 class="issue-title">${issue.title}</h4>
            </div>
            <p class="issue-description">${issue.description}</p>
        `;
        
        issuesList.appendChild(issueCard);
    });
}

// ============================================
// Content Recommendations with Numbers
// ============================================
function displayContentRecs(recommendations) {
    const recsList = document.getElementById('recsList');
    recsList.innerHTML = '';
    
    if (recommendations.length === 0) {
        recsList.innerHTML = `
            <div class="recommendation-item">
                <div class="rec-number">✓</div>
                <p class="rec-text">No recommendations - your content is well-optimized!</p>
            </div>
        `;
        return;
    }
    
    recommendations.forEach((rec, index) => {
        const recDiv = document.createElement('div');
        recDiv.className = 'recommendation-item';
        
        recDiv.innerHTML = `
            <div class="rec-number">${index + 1}</div>
            <p class="rec-text">${rec}</p>
        `;
        
        recsList.appendChild(recDiv);
    });
}

// ============================================
// Schema Comparison with Syntax Highlighting
// ============================================
function displaySchemaComparison(current, improved) {
    const currentPre = document.getElementById('currentJsonld');
    const improvedPre = document.getElementById('improvedJsonld');
    
    // Apply syntax highlighting
    currentPre.innerHTML = syntaxHighlight(current);
    improvedPre.innerHTML = syntaxHighlight(improved);
}

function syntaxHighlight(json) {
    if (typeof json !== 'string') {
        json = JSON.stringify(json, null, 2);
    }
    
    // Escape HTML
    json = json.replace(/&/g, '&').replace(/</g, '<').replace(/>/g, '>');
    
    // Apply syntax highlighting
    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
        let cls = 'json-number';
        if (/^"/.test(match)) {
            if (/:$/.test(match)) {
                cls = 'json-key';
            } else {
                cls = 'json-string';
            }
        } else if (/true|false/.test(match)) {
            cls = 'json-boolean';
        } else if (/null/.test(match)) {
            cls = 'json-null';
        }
        return '<span class="' + cls + '">' + match + '</span>';
    });
}

// ============================================
// Copy to Clipboard Functionality
// ============================================
document.getElementById('copyBtn').addEventListener('click', async () => {
    const text = document.getElementById('improvedJsonld').textContent;
    const btn = document.getElementById('copyBtn');
    
    try {
        await navigator.clipboard.writeText(text);
        
        // Show success feedback
        const originalHTML = btn.innerHTML;
        btn.classList.add('copied');
        btn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/>
            </svg>
            Copied!
        `;
        
        setTimeout(() => {
            btn.classList.remove('copied');
            btn.innerHTML = originalHTML;
        }, 2000);
    } catch (err) {
        console.error('Failed to copy:', err);
        alert('Failed to copy to clipboard');
    }
});

// ============================================
// PDF Export Functionality
// ============================================
document.getElementById('pdfBtn').addEventListener('click', () => {
    if (!currentData) {
        alert('No analysis data to export. Please analyze a URL first.');
        return;
    }
    
    // Create a print-friendly version
    const printWindow = window.open('', '_blank');
    const url = document.getElementById('urlInput').value;
    const date = new Date().toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
    
    // Build HTML content for PDF
    let htmlContent = `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SchematoAIO Analysis Report - ${url}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            line-height: 1.6;
            color: #202124;
            padding: 40px;
            max-width: 900px;
            margin: 0 auto;
        }
        h1 {
            font-size: 28px;
            margin-bottom: 10px;
            color: #202124;
        }
        h2 {
            font-size: 20px;
            margin: 30px 0 15px;
            color: #3C4043;
            border-bottom: 2px solid #E8EAED;
            padding-bottom: 8px;
        }
        h3 {
            font-size: 16px;
            margin: 20px 0 10px;
            color: #5F6368;
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 3px solid #4285F4;
        }
        .logo {
            font-size: 32px;
            font-weight: 600;
            margin-bottom: 5px;
        }
        .url {
            color: #5F6368;
            font-size: 14px;
            word-break: break-all;
        }
        .date {
            color: #80868B;
            font-size: 12px;
            margin-top: 5px;
        }
        .score-box {
            background: #F8F9FA;
            border-left: 4px solid #34A853;
            padding: 20px;
            margin: 20px 0;
            border-radius: 4px;
        }
        .score-number {
            font-size: 48px;
            font-weight: 700;
            color: #34A853;
            line-height: 1;
        }
        .score-label {
            color: #5F6368;
            font-size: 14px;
        }
        .rule-item {
            background: #F8F9FA;
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
        }
        .rule-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            font-weight: 500;
        }
        .rule-score {
            color: #34A853;
            font-weight: 600;
        }
        .rule-message {
            color: #5F6368;
            font-size: 13px;
        }
        .status-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 12px;
            font-size: 13px;
            font-weight: 500;
            margin: 10px 0;
        }
        .status-fresh { background: #E8F5E9; color: #34A853; }
        .status-aging { background: #FFF4E5; color: #F57C00; }
        .status-stale { background: #FEE; color: #EA4335; }
        .status-unknown { background: #F1F3F4; color: #5F6368; }
        .status-present { background: #E8F5E9; color: #34A853; }
        .status-missing { background: #FEE; color: #EA4335; }
        .info-section {
            background: #F8F9FA;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
            border-left: 3px solid #4285F4;
        }
        .info-section p {
            margin: 8px 0;
            color: #5F6368;
        }
        .schema-item {
            padding: 10px;
            margin: 5px 0;
            background: #F8F9FA;
            border-radius: 4px;
            font-size: 14px;
        }
        .issue-item {
            padding: 15px;
            margin: 10px 0;
            background: #FEE;
            border-left: 4px solid #EA4335;
            border-radius: 4px;
        }
        .issue-title {
            font-weight: 600;
            margin-bottom: 5px;
        }
        .issue-description {
            color: #5F6368;
            font-size: 13px;
        }
        .recommendation {
            padding: 12px;
            margin: 8px 0;
            background: #F8F9FA;
            border-left: 3px solid #4285F4;
            border-radius: 4px;
            font-size: 14px;
        }
        .code-block {
            background: #F8F9FA;
            border: 1px solid #E8EAED;
            border-radius: 4px;
            padding: 15px;
            font-family: 'Courier New', monospace;
            font-size: 11px;
            overflow-x: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
            margin: 10px 0;
        }
        @media print {
            body { padding: 20px; }
            .page-break { page-break-before: always; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">SchematoAIO Analysis Report</div>
        <div class="url">${url}</div>
        <div class="date">Generated on ${date}</div>
    </div>
`;

    // GEO Score Section
    const geoScore = currentData.geo_score;
    const score = Math.round(geoScore.total_score);
    htmlContent += `
    <h2>🎯 GEO Readiness Score</h2>
    <div class="score-box">
        <div class="score-number">${score}</div>
        <div class="score-label">out of ${geoScore.max_score}</div>
    </div>
    <h3>Rule Breakdown</h3>
`;
    geoScore.rules.forEach(rule => {
        htmlContent += `
    <div class="rule-item">
        <div class="rule-header">
            <span>${rule.rule_name.replace(/_/g, ' ')}</span>
            <span class="rule-score">${rule.score.toFixed(1)}/${rule.max_score}</span>
        </div>
        <div class="rule-message">${rule.message}</div>
    </div>
`;
    });

    // Content Freshness
    htmlContent += `
    <h2>🕒 Content Freshness</h2>
    <div class="info-section">
`;
    if (currentData.content_freshness && currentData.content_freshness.status) {
        const freshness = currentData.content_freshness;
        const statusClass = `status-${freshness.status.toLowerCase()}`;
        htmlContent += `
        <div class="status-badge ${statusClass}">${freshness.status}</div>
`;
        if (freshness.days_old !== null && freshness.days_old !== undefined) {
            htmlContent += `
        <p><strong>Days since last update:</strong> ${freshness.days_old}</p>
        <p><strong>Date found:</strong> ${new Date(freshness.date_found).toLocaleDateString()}</p>
        <p><strong>Source field:</strong> ${freshness.source_field}</p>
`;
        } else {
            htmlContent += `<p>No date information found in schema markup.</p>`;
        }
    } else {
        htmlContent += `<p>Content freshness data not available.</p>`;
    }
    htmlContent += `
    </div>
`;

    // llms.txt Detection
    htmlContent += `
    <h2>🤖 llms.txt Detection</h2>
    <div class="info-section">
`;
    if (currentData.llms_txt && currentData.llms_txt.status) {
        const llmsTxt = currentData.llms_txt;
        const statusClass = llmsTxt.status === 'Present' ? 'status-present' : 'status-missing';
        htmlContent += `
        <div class="status-badge ${statusClass}">${llmsTxt.status}</div>
`;
        if (llmsTxt.status === 'Present' && llmsTxt.url) {
            htmlContent += `
        <p><strong>File URL:</strong> ${llmsTxt.url}</p>
`;
            if (llmsTxt.content_length) {
                htmlContent += `<p><strong>Content size:</strong> ${llmsTxt.content_length} characters</p>`;
            }
        } else {
            htmlContent += `<p>No llms.txt file detected at the root of the domain.</p>`;
        }
    } else {
        htmlContent += `<p>llms.txt detection data not available.</p>`;
    }
    htmlContent += `
    </div>
`;

    // Schema Inventory
    htmlContent += `
    <div class="page-break"></div>
    <h2>📋 Schema Inventory</h2>
`;
    currentData.schema_inventory.types_found.forEach(type => {
        if (type.found) {
            htmlContent += `
    <div class="schema-item">
        <strong>${type.type_name}:</strong> ${type.status_message}
    </div>
`;
        }
    });

    // Issues
    if (currentData.issues && currentData.issues.length > 0) {
        htmlContent += `
    <h2>⚠️ Actionable Issues</h2>
`;
        currentData.issues.forEach(issue => {
            htmlContent += `
    <div class="issue-item">
        <div class="issue-title">${issue.title}</div>
        <div class="issue-description">${issue.description}</div>
    </div>
`;
        });
    }

    // Recommendations
    if (currentData.content_recommendations && currentData.content_recommendations.length > 0) {
        htmlContent += `
    <h2>💡 Content Recommendations</h2>
`;
        currentData.content_recommendations.forEach((rec, index) => {
            htmlContent += `
    <div class="recommendation">
        <strong>${index + 1}.</strong> ${rec}
    </div>
`;
        });
    }

    // Improved JSON-LD
    if (currentData.improved_jsonld) {
        htmlContent += `
    <div class="page-break"></div>
    <h2>🔄 Improved JSON-LD Schema</h2>
    <div class="code-block">${JSON.stringify(currentData.improved_jsonld, null, 2)}</div>
`;
    }

    htmlContent += `
</body>
</html>
`;

    // Write to new window and trigger print
    printWindow.document.write(htmlContent);
    printWindow.document.close();
    
    // Wait for content to load, then print
    printWindow.onload = () => {
        setTimeout(() => {
            printWindow.print();
        }, 250);
    };
});

// ============================================
// Initialize on Load
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    // Focus on URL input
    document.getElementById('urlInput').focus();
});
