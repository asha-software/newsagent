// Check if we're viewing a shared result
const resultsContainer = document.getElementById('results-container');
const isSharedView = resultsContainer.getAttribute('data-is-shared-view') === 'true';
let currentSearchQuery = '';
let currentSearchResult = null;

// Function to display search results
function displaySearchResults(data, query) {
  const resultsContainer = document.getElementById('results-container');
  const shareContainer = document.getElementById('share-container');
  
  if (resultsContainer) {
    resultsContainer.style.display = 'block';
    resultsContainer.innerHTML = '';
    
    // Store the current search query and result for sharing
    currentSearchQuery = query;
    currentSearchResult = data;

    // Show the share container if the user is authenticated
    if (shareContainer) {
      shareContainer.style.display = 'block';
    }

    // Check if data is an object with analyses array (new format)
    if (data.analyses && Array.isArray(data.analyses)) {
      // Create a container for the entire response
      const responseContainer = document.createElement('div');
      responseContainer.className = 'response-container';
      
      // Add a title for the response
      const responseTitle = document.createElement('h2');
      responseTitle.textContent = 'Analysis Results';
      responseTitle.className = 'response-title';
      responseContainer.appendChild(responseTitle);
      
      // Add final verdict if available
      if (data.final_label && data.final_justification) {
        const finalVerdictTable = document.createElement('table');
        finalVerdictTable.className = 'claims-table final-verdict-table';
        
        // Create table header with color based on final label
        const finalHeader = document.createElement('thead');
        const finalHeaderRow = document.createElement('tr');
        
        const finalTitleHeader = document.createElement('th');
        finalTitleHeader.textContent = 'Final Verdict';
        finalTitleHeader.colSpan = 2;
        
        // Set header color based on final label
        if (data.final_label === 'true') {
          finalTitleHeader.className = 'final-verdict-true';
        } else {
          finalTitleHeader.className = 'final-verdict-false';
        }
        
        finalHeaderRow.appendChild(finalTitleHeader);
        
        finalHeader.appendChild(finalHeaderRow);
        finalVerdictTable.appendChild(finalHeader);
        
        // Create table body
        const finalTableBody = document.createElement('tbody');
        
        // Add row for final label
        const finalLabelRow = document.createElement('tr');
        
        const finalLabelTitle = document.createElement('td');
        finalLabelTitle.textContent = 'Final Label';
        finalLabelTitle.className = 'label-title';
        finalLabelRow.appendChild(finalLabelTitle);
        
        const finalLabelValue = document.createElement('td');
        const finalVerdictIcon = document.createElement('img');
        finalVerdictIcon.src = data.final_label === 'true' ? 
          YES_ICON_URL : 
          NO_ICON_URL;
        finalVerdictIcon.alt = data.final_label === 'true' ? 'True' : 'False';
        finalVerdictIcon.className = 'verdict-icon';
        finalLabelValue.appendChild(finalVerdictIcon);
        finalLabelValue.appendChild(document.createTextNode(data.final_label));
        finalLabelRow.appendChild(finalLabelValue);
        
        finalTableBody.appendChild(finalLabelRow);
        
        // Add row for final justification
        const finalJustificationRow = document.createElement('tr');
        
        const finalJustificationTitle = document.createElement('td');
        finalJustificationTitle.textContent = 'Final Justification';
        finalJustificationTitle.className = 'label-title';
        finalJustificationRow.appendChild(finalJustificationTitle);
        
        const finalJustificationValue = document.createElement('td');
        finalJustificationValue.textContent = data.final_justification || 'No final justification provided';
        finalJustificationRow.appendChild(finalJustificationValue);
        
        finalTableBody.appendChild(finalJustificationRow);
        
        finalVerdictTable.appendChild(finalTableBody);
        responseContainer.appendChild(finalVerdictTable);
      }
      
      // Create a container for analyses with expandable sections
      const analysesContainer = document.createElement('div');
      analysesContainer.className = 'analyses-container';
      
      // Add a title for the analyses
      const analysesTitle = document.createElement('h3');
      analysesTitle.textContent = 'Analysis Results';
      analysesTitle.className = 'analyses-title';
      analysesContainer.appendChild(analysesTitle);
      
      // Create cards for each analysis
      for (let i = 0; i < data.analyses.length; i++) {
        const analysis = data.analyses[i];
        
        // Create a card for this analysis
        const analysisCard = document.createElement('div');
        analysisCard.className = 'analysis-card';
        
        // Create the top section with claim and verdict (non-collapsible)
        const topSection = document.createElement('div');
        topSection.className = 'top-section';
        
        // Add claim
        const claimContainer = document.createElement('div');
        claimContainer.className = 'claim-container';
        
        const claimLabel = document.createElement('span');
        claimLabel.className = 'field-label';
        claimLabel.textContent = 'Claim: ';
        claimContainer.appendChild(claimLabel);
        
        const claimText = document.createElement('span');
        claimText.className = 'claim-text';
        claimText.textContent = analysis.claim;
        claimContainer.appendChild(claimText);
        
        topSection.appendChild(claimContainer);
        
        // Add verdict with icon
        const verdictContainer = document.createElement('div');
        verdictContainer.className = 'verdict-container';
        
        const verdictLabel = document.createElement('span');
        verdictLabel.className = 'field-label';
        verdictLabel.textContent = 'Verdict: ';
        verdictContainer.appendChild(verdictLabel);
        
        const verdictIcon = document.createElement('img');
        verdictIcon.src = analysis.label === 'true' ? 
          YES_ICON_URL : 
          NO_ICON_URL;
        verdictIcon.alt = analysis.label === 'true' ? 'True' : 'False';
        verdictIcon.className = 'verdict-icon';
        verdictContainer.appendChild(verdictIcon);
        
        const verdictText = document.createElement('span');
        verdictText.className = 'verdict-text';
        verdictText.textContent = analysis.label === 'true' ? 'True' : 'False';
        verdictContainer.appendChild(verdictText);
        
        topSection.appendChild(verdictContainer);
        analysisCard.appendChild(topSection);
        
        // Create collapsible section
        const collapsibleSection = document.createElement('div');
        collapsibleSection.className = 'collapsible-section';
        
        // Create collapsible header
        const collapsibleHeader = document.createElement('div');
        collapsibleHeader.className = 'collapsible-header';
        
        const expandIcon = document.createElement('span');
        expandIcon.className = 'expand-icon';
        expandIcon.innerHTML = '&#9654;'; // Right-pointing triangle
        collapsibleHeader.appendChild(expandIcon);
        
        const detailsText = document.createElement('span');
        detailsText.textContent = 'Show Details';
        detailsText.className = 'details-text';
        collapsibleHeader.appendChild(detailsText);
        
        collapsibleSection.appendChild(collapsibleHeader);
        
        // Create expandable content
        const expandableContent = document.createElement('div');
        expandableContent.className = 'expandable-content';
        expandableContent.style.display = 'none'; // Initially hidden
        
        // Add justification section
        const justificationSection = document.createElement('div');
        justificationSection.className = 'content-section justification-section';
        
        const justificationTitle = document.createElement('h4');
        justificationTitle.textContent = 'Justification';
        justificationSection.appendChild(justificationTitle);
        
        const justificationContent = document.createElement('div');
        justificationContent.className = 'section-content';
        justificationContent.textContent = analysis.justification || 'No justification provided';
        justificationSection.appendChild(justificationContent);
        
        expandableContent.appendChild(justificationSection);
        
        // Add evidence section
        const evidenceSection = document.createElement('div');
        evidenceSection.className = 'content-section evidence-section';
        
        const evidenceTitle = document.createElement('h4');
        evidenceTitle.textContent = 'Evidence';
        evidenceSection.appendChild(evidenceTitle);
        
        const evidenceContent = document.createElement('div');
        evidenceContent.className = 'section-content';
        
        if (analysis.evidence && analysis.evidence.length > 0) {
          const evidenceList = document.createElement('ul');
          evidenceList.className = 'evidence-list';
          
          analysis.evidence.forEach(evidence => {
            const evidenceItem = document.createElement('li');
            evidenceItem.className = 'evidence-item';
            
            const evidenceName = document.createElement('div');
            evidenceName.className = 'evidence-name';
            evidenceName.textContent = `Source: ${evidence.name || 'Unknown'}`;
            evidenceItem.appendChild(evidenceName);
            
            const evidenceResult = document.createElement('div');
            evidenceResult.className = 'evidence-result';
            
            // Handle different types of evidence results
            if (typeof evidence.result === 'string') {
              evidenceResult.textContent = evidence.result;
            } else {
              evidenceResult.textContent = JSON.stringify(evidence.result);
            }
            
            evidenceItem.appendChild(evidenceResult);
            evidenceList.appendChild(evidenceItem);
          });
          
          evidenceContent.appendChild(evidenceList);
        } else {
          evidenceContent.textContent = 'No evidence provided';
        }
        
        evidenceSection.appendChild(evidenceContent);
        expandableContent.appendChild(evidenceSection);
        
        // Add expandable content to the collapsible section
        collapsibleSection.appendChild(expandableContent);
        
        // Add collapsible section to the card
        analysisCard.appendChild(collapsibleSection);
        
        // Add click handler to toggle expansion
        collapsibleHeader.addEventListener('click', function() {
          // Toggle the display of expandable content
          if (expandableContent.style.display === 'none') {
            expandableContent.style.display = 'block';
            expandIcon.innerHTML = '&#9660;'; // Down-pointing triangle
            detailsText.textContent = 'Hide Details';
            collapsibleSection.classList.add('expanded');
          } else {
            expandableContent.style.display = 'none';
            expandIcon.innerHTML = '&#9654;'; // Right-pointing triangle
            detailsText.textContent = 'Show Details';
            collapsibleSection.classList.remove('expanded');
          }
        });
        
        // Add the card to the container
        analysesContainer.appendChild(analysisCard);
      }
      
      responseContainer.appendChild(analysesContainer);
      
      // Add the raw JSON data in a collapsible section
      const rawDataContainer = document.createElement('div');
      rawDataContainer.className = 'raw-data-container';
      
      const rawDataToggle = document.createElement('button');
      rawDataToggle.className = 'raw-data-toggle';
      rawDataToggle.textContent = 'Show Raw JSON Data';
      rawDataToggle.onclick = function() {
        const rawDataContent = document.getElementById('raw-data-content');
        if (rawDataContent.style.display === 'none') {
          rawDataContent.style.display = 'block';
          this.textContent = 'Hide Raw JSON Data';
        } else {
          rawDataContent.style.display = 'none';
          this.textContent = 'Show Raw JSON Data';
        }
      };
      rawDataContainer.appendChild(rawDataToggle);
      
      const rawDataContent = document.createElement('pre');
      rawDataContent.id = 'raw-data-content';
      rawDataContent.className = 'raw-data-content';
      rawDataContent.style.display = 'none';
      rawDataContent.textContent = JSON.stringify(data, null, 2);
      rawDataContainer.appendChild(rawDataContent);
      
      responseContainer.appendChild(rawDataContainer);
      
      resultsContainer.appendChild(responseContainer);
      
      if (data.analyses.length === 0) {
        const noResults = document.createElement('div');
        noResults.className = 'no-results';
        noResults.textContent = 'No results found for your query.';
        resultsContainer.appendChild(noResults);
      }
    } else if (data.claims && Array.isArray(data.claims) && 
        data.labels && Array.isArray(data.labels) && 
        data.justifications && Array.isArray(data.justifications)) {
      // Original format handling (keeping this for backward compatibility)
      
      // Create a container for the entire response
      const responseContainer = document.createElement('div');
      responseContainer.className = 'response-container';
      
      // Add a title for the response
      const responseTitle = document.createElement('h2');
      responseTitle.textContent = 'Analysis Results';
      responseTitle.className = 'response-title';
      responseContainer.appendChild(responseTitle);
      
      // Create a container for analyses with expandable sections
      const claimsContainer = document.createElement('div');
      claimsContainer.className = 'analyses-container';
      
      // Add a title for the analyses
      const claimsTitle = document.createElement('h3');
      claimsTitle.textContent = 'Claims Analysis';
      claimsTitle.className = 'analyses-title';
      claimsContainer.appendChild(claimsTitle);
      
      // Create cards for each claim
      for (let i = 0; i < data.claims.length; i++) {
        // Create a card for this claim
        const claimCard = document.createElement('div');
        claimCard.className = 'analysis-card';
        
        // Create the top section with claim and verdict (non-collapsible)
        const topSection = document.createElement('div');
        topSection.className = 'top-section';
        
        // Add claim
        const claimContainer = document.createElement('div');
        claimContainer.className = 'claim-container';
        
        const claimLabel = document.createElement('span');
        claimLabel.className = 'field-label';
        claimLabel.textContent = 'Claim: ';
        claimContainer.appendChild(claimLabel);
        
        const claimText = document.createElement('span');
        claimText.className = 'claim-text';
        claimText.textContent = data.claims[i];
        claimContainer.appendChild(claimText);
        
        topSection.appendChild(claimContainer);
        
        // Add verdict with icon
        const verdictContainer = document.createElement('div');
        verdictContainer.className = 'verdict-container';
        
        const verdictLabel = document.createElement('span');
        verdictLabel.className = 'field-label';
        verdictLabel.textContent = 'Verdict: ';
        verdictContainer.appendChild(verdictLabel);
        
        const verdictIcon = document.createElement('img');
        verdictIcon.src = data.labels[i] === 'true' ? 
          YES_ICON_URL : 
          NO_ICON_URL;
        verdictIcon.alt = data.labels[i] === 'true' ? 'True' : 'False';
        verdictIcon.className = 'verdict-icon';
        verdictContainer.appendChild(verdictIcon);
        
        const verdictText = document.createElement('span');
        verdictText.className = 'verdict-text';
        verdictText.textContent = data.labels[i] === 'true' ? 'True' : 'False';
        verdictContainer.appendChild(verdictText);
        
        topSection.appendChild(verdictContainer);
        claimCard.appendChild(topSection);
        
        // Create collapsible section
        const collapsibleSection = document.createElement('div');
        collapsibleSection.className = 'collapsible-section';
        
        // Create collapsible header
        const collapsibleHeader = document.createElement('div');
        collapsibleHeader.className = 'collapsible-header';
        
        const expandIcon = document.createElement('span');
        expandIcon.className = 'expand-icon';
        expandIcon.innerHTML = '&#9654;'; // Right-pointing triangle
        collapsibleHeader.appendChild(expandIcon);
        
        const detailsText = document.createElement('span');
        detailsText.textContent = 'Show Justification';
        detailsText.className = 'details-text';
        collapsibleHeader.appendChild(detailsText);
        
        collapsibleSection.appendChild(collapsibleHeader);
        
        // Create expandable content
        const expandableContent = document.createElement('div');
        expandableContent.className = 'expandable-content';
        expandableContent.style.display = 'none'; // Initially hidden
        
        // Add justification section
        const justificationSection = document.createElement('div');
        justificationSection.className = 'content-section justification-section';
        
        const justificationTitle = document.createElement('h4');
        justificationTitle.textContent = 'Justification';
        justificationSection.appendChild(justificationTitle);
        
        const justificationContent = document.createElement('div');
        justificationContent.className = 'section-content';
        justificationContent.textContent = data.justifications[i] || 'No justification provided';
        justificationSection.appendChild(justificationContent);
        
        expandableContent.appendChild(justificationSection);
        
        // Add expandable content to the collapsible section
        collapsibleSection.appendChild(expandableContent);
        
        // Add collapsible section to the card
        claimCard.appendChild(collapsibleSection);
        
        // Add click handler to toggle expansion
        collapsibleHeader.addEventListener('click', function() {
          // Toggle the display of expandable content
          if (expandableContent.style.display === 'none') {
            expandableContent.style.display = 'block';
            expandIcon.innerHTML = '&#9660;'; // Down-pointing triangle
            detailsText.textContent = 'Hide Justification';
            collapsibleSection.classList.add('expanded');
          } else {
            expandableContent.style.display = 'none';
            expandIcon.innerHTML = '&#9654;'; // Right-pointing triangle
            detailsText.textContent = 'Show Justification';
            collapsibleSection.classList.remove('expanded');
          }
        });
        
        // Add the card to the container
        claimsContainer.appendChild(claimCard);
      }
      
      responseContainer.appendChild(claimsContainer);
      
      // Add final verdict if available
      if (data.final_label && data.final_justification) {
        const finalVerdictContainer = document.createElement('div');
        finalVerdictContainer.className = 'final-verdict-container';
        
        const finalVerdictTitle = document.createElement('h3');
        finalVerdictTitle.textContent = 'Final Verdict';
        finalVerdictContainer.appendChild(finalVerdictTitle);
        
        const finalVerdictContent = document.createElement('div');
        finalVerdictContent.className = 'final-verdict-content';
        
        const finalVerdictLabel = document.createElement('div');
        finalVerdictLabel.className = 'final-verdict-label';
        
        const finalVerdictIcon = document.createElement('img');
        finalVerdictIcon.src = data.final_label === 'true' ? 
          YES_ICON_URL : 
          NO_ICON_URL;
        finalVerdictIcon.alt = data.final_label === 'true' ? 'True' : 'False';
        finalVerdictIcon.className = 'verdict-icon';
        
        finalVerdictLabel.appendChild(finalVerdictIcon);
        finalVerdictLabel.appendChild(document.createTextNode(data.final_label));
        finalVerdictContent.appendChild(finalVerdictLabel);
        
        const finalVerdictJustification = document.createElement('p');
        finalVerdictJustification.className = 'final-verdict-justification';
        finalVerdictJustification.textContent = data.final_justification || 'No final justification provided';
        finalVerdictContent.appendChild(finalVerdictJustification);
        
        finalVerdictContainer.appendChild(finalVerdictContent);
        responseContainer.appendChild(finalVerdictContainer);
      }
      
      // Add the raw JSON data in a collapsible section
      const rawDataContainer = document.createElement('div');
      rawDataContainer.className = 'raw-data-container';
      
      const rawDataToggle = document.createElement('button');
      rawDataToggle.className = 'raw-data-toggle';
      rawDataToggle.textContent = 'Show Raw JSON Data';
      rawDataToggle.onclick = function() {
        const rawDataContent = document.getElementById('raw-data-content');
        if (rawDataContent.style.display === 'none') {
          rawDataContent.style.display = 'block';
          this.textContent = 'Hide Raw JSON Data';
        } else {
          rawDataContent.style.display = 'none';
          this.textContent = 'Show Raw JSON Data';
        }
      };
      rawDataContainer.appendChild(rawDataToggle);
      
      const rawDataContent = document.createElement('pre');
      rawDataContent.id = 'raw-data-content';
      rawDataContent.className = 'raw-data-content';
      rawDataContent.style.display = 'none';
      rawDataContent.textContent = JSON.stringify(data, null, 2);
      rawDataContainer.appendChild(rawDataContent);
      
      responseContainer.appendChild(rawDataContainer);
      
      resultsContainer.appendChild(responseContainer);
      
      if (data.claims.length === 0) {
        const noResults = document.createElement('div');
        noResults.className = 'no-results';
        noResults.textContent = 'No results found for your query.';
        resultsContainer.appendChild(noResults);
      }
    } else if (Array.isArray(data)) {
      // Handle the case where data is already an array (for backward compatibility)
      data.forEach(result => {
        const resultCard = document.createElement('div');
        resultCard.className = 'result-card';
        
        const header = document.createElement('div');
        header.className = 'result-header';
        
        const title = document.createElement('h2');
        title.textContent = result.claim || 'Claim Analysis';
        
        const icon = document.createElement('img');
        // Use label instead of verdict
        icon.src = result.label === 'true' ? 
          YES_ICON_URL : 
          NO_ICON_URL;
        icon.alt = result.label === 'true' ? 'True' : 'False';
        icon.className = 'result-icon';
        
        header.appendChild(title);
        header.appendChild(icon);
        
        const content = document.createElement('div');
        content.className = 'result-content';
        
        const reasoning = document.createElement('p');
        // Use justification instead of reasoning
        reasoning.textContent = result.justification || 'No reasoning provided';
        content.appendChild(reasoning);
        
        // Display evidence instead of sources
        if (result.evidence && result.evidence.length > 0) {
          const sourceDiv = document.createElement('div');
          sourceDiv.className = 'result-source';
          sourceDiv.textContent = 'Evidence: ';
          
          result.evidence.forEach((evidence, index) => {
            const sourceText = document.createElement('span');
            sourceText.textContent = evidence.name || `Evidence ${index + 1}`;
            
            sourceDiv.appendChild(sourceText);
            
            if (index < result.evidence.length - 1) {
              sourceDiv.appendChild(document.createTextNode(', '));
            }
          });
          
          content.appendChild(sourceDiv);
        }
        
        resultCard.appendChild(header);
        resultCard.appendChild(content);
        
        resultsContainer.appendChild(resultCard);
      });
      
      if (data.length === 0) {
        const noResults = document.createElement('div');
        noResults.className = 'no-results';
        noResults.textContent = 'No results found for your query.';
        resultsContainer.appendChild(noResults);
      }
    } else {
      // If data is neither an object with arrays nor an array itself
      const errorDiv = document.createElement('div');
      errorDiv.className = 'error';
      errorDiv.textContent = 'Unexpected response format from the server.';
      resultsContainer.appendChild(errorDiv);
    }
  }
}

// Check if we're viewing a shared result
if (isSharedView) {
  // Get the shared result data from the data attribute
  const sharedResultData = resultsContainer.getAttribute('data-shared-result');
  const sharedQuery = resultsContainer.getAttribute('data-shared-query');
  
  if (sharedResultData) {
    try {
      // First parse the outer JSON string to get the serialized result data
      const parsedData = JSON.parse(sharedResultData);
      
      // Then parse the inner JSON string to get the actual result data
      const data = JSON.parse(parsedData);
      
      // Display the shared result
      displaySearchResults(data, sharedQuery || '');
      
      // Set the search input value to the shared query
      const searchInput = document.getElementById('search');
      if (searchInput && sharedQuery) {
        searchInput.value = sharedQuery;
      }
    } catch (error) {
      console.error('Error parsing shared result data:', error);
      resultsContainer.innerHTML = '<div class="error">Error displaying shared result: ' + error.message + '</div>';
      resultsContainer.style.display = 'block';
    }
  }
}

// When the form is submitted
document.querySelector('form').addEventListener('submit', function(e) {
  e.preventDefault();
  
  const searchQuery = document.getElementById('search').value.trim();
  if (!searchQuery) return;
  
  const loadingElement = document.getElementById('loading');
  const resultsContainer = document.getElementById('results-container');
  const searchContainer = document.querySelector('.search-container');
  const shareContainer = document.getElementById('share-container');
  
  // Check if the user is authenticated
  const isAuthenticated = this.getAttribute('data-is-authenticated') === 'true';
  
  if (!isAuthenticated) {
    // If the user is not authenticated, show a message
    if (resultsContainer) {
      resultsContainer.style.display = 'block';
      resultsContainer.innerHTML = `
        <div class="login-required">
          <h3>Login Required</h3>
          <p>You need to <a href="/signin/">log in</a> or <a href="/signup/">create an account</a> to perform searches.</p>
          <p>You can still view this shared result, but you cannot perform new searches without logging in.</p>
        </div>
      `;
    }
    return;
  }
  
  // Add a class to the search container to add padding when results are shown
  searchContainer.classList.add('with-results');
  
  if (loadingElement) {
    loadingElement.style.display = 'block';
  }
  
  if (resultsContainer) {
    resultsContainer.style.display = 'none';
  }
  
  if (shareContainer) {
    shareContainer.style.display = 'none';
  }

  const selectedSources = Array.from(document.querySelectorAll('input[name="source"]:checked'))
    .map(checkbox => checkbox.value);

  // Fix API URL for browser access
  let apiUrl = API_URL;
  if (apiUrl.includes('api:8000')) {
    apiUrl = apiUrl.replace('api:8000', 'localhost:8001');
  }
  
  // Get the API key
  fetch('/api/api-keys/', {
    method: 'GET',
    headers: {
      'X-Requested-With': 'XMLHttpRequest'
    },
    credentials: 'include'
  })
  .then(response => {
    // Check if the response is OK (status in the range 200-299)
    if (!response.ok) {
      // If we get a non-OK response, the user is likely not authenticated
      // Show a message instead of redirecting
      if (resultsContainer) {
        resultsContainer.style.display = 'block';
        resultsContainer.innerHTML = `
          <div class="login-required">
            <h3>Login Required</h3>
            <p>You need to <a href="/signin/">log in</a> or <a href="/signup/">create an account</a> to perform searches.</p>
            <p>You can still view this shared result, but you cannot perform new searches without logging in.</p>
          </div>
        `;
      }
      throw new Error('Authentication required');
    }
    return response.json();
  })
  .then(data => {
    const apiKey = data.api_key;
    
    // Use the API key to make the query
    return fetch(apiUrl + '/query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'X-API-Key': apiKey
      },
      body: JSON.stringify({
        body: searchQuery,
        sources: selectedSources
      })
    });
  })
  .then(response => {
    if (!response.ok) {
      return response.text().then(text => {
        throw new Error(`Network response was not ok: ${response.status} ${response.statusText}`);
      });
    }
    return response.json();
  })
  .then(data => {
    const loadingElement = document.getElementById('loading');
    
    if (loadingElement) {
      loadingElement.style.display = 'none';
    }
    
    // Display the search results
    displaySearchResults(data, searchQuery);
  })
  .catch(error => {
    const loadingElement = document.getElementById('loading');
    const resultsContainer = document.getElementById('results-container');
    
    if (loadingElement) {
      loadingElement.style.display = 'none';
    }
    
    if (resultsContainer) {
      resultsContainer.style.display = 'block';
      resultsContainer.innerHTML = `<div class="error">Error processing your request: ${error.message}</div>`;
    }
  });
});

// Add event listeners for the share functionality
if (document.getElementById('share-button')) {
  document.getElementById('share-button').addEventListener('click', function() {
    if (!currentSearchResult || !currentSearchQuery) {
      return;
    }
    
    const isPublic = document.getElementById('make-public').checked;
    const shareMessage = document.getElementById('share-message');
    const shareLinkContainer = document.getElementById('share-link-container');
    const shareLink = document.getElementById('share-link');
    
    // Save the result to the server
    fetch('/api/save-shared-result/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
      },
      body: JSON.stringify({
        query: currentSearchQuery,
        result_data: currentSearchResult,
        is_public: isPublic
      })
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Show the share link
        shareLink.value = window.location.origin + data.shared_url;
        shareLinkContainer.style.display = 'flex';
        shareMessage.textContent = data.message;
        shareMessage.className = 'share-message';
      } else {
        // Show error message
        shareMessage.textContent = data.message;
        shareMessage.className = 'share-message error';
      }
    })
    .catch(error => {
      // Show error message
      shareMessage.textContent = 'Error saving result: ' + error.message;
      shareMessage.className = 'share-message error';
    });
  });
  
  // Add event listener for the copy link button
  if (document.getElementById('copy-link-button')) {
    document.getElementById('copy-link-button').addEventListener('click', function() {
      const shareLink = document.getElementById('share-link');
      const shareMessage = document.getElementById('share-message');
      
      // Copy the link to the clipboard
      shareLink.select();
      document.execCommand('copy');
      
      // Show success message
      shareMessage.textContent = 'Link copied to clipboard!';
      shareMessage.className = 'share-message';
    });
  }
}
