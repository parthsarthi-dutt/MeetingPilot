// Meet logic for Checklist Overlay
const API_URL = 'http://localhost:8000';
let overlayContainer = null;
let currentMeeting = null;
let currentChecklist = null;
let interactionTimeout = null;
let initialHideTimeout = null;
let hasInteracted = false;
let isOverlayVisible = false;

// We need to fetch meeting by link
async function fetchMeetingData() {
  const link = window.location.href.split('?')[0]; // Remove query params

  return new Promise((resolve) => {
    chrome.runtime.sendMessage({
      type: 'API_CALL',
      method: 'GET',
      url: `${API_URL}/api/extension/meeting-by-link?meet_link=${encodeURIComponent(link)}`
    }, (res) => {
      if (res && res.data) {
        resolve(res.data);
      } else {
        resolve(null);
      }
    });
  });
}

async function fetchChecklist(meetingId) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({
      type: 'API_CALL',
      method: 'GET',
      url: `${API_URL}/api/meetings/${meetingId}/checklist`
    }, (res) => {
      if (res && res.data) {
        resolve(res.data);
      } else {
        resolve(null);
      }
    });
  });
}

function renderOverlay() {
  if (!overlayContainer) {
    overlayContainer = document.createElement('div');
    overlayContainer.id = 'mp-overlay-container';
    
    // Add Inter font
    const link = document.createElement('link');
    link.href = 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap';
    link.rel = 'stylesheet';
    document.head.appendChild(link);
    
    document.body.appendChild(overlayContainer);
  }

  // Build the checklist HTML
  let itemsHtml = '';
  if (currentChecklist && currentChecklist.items) {
    currentChecklist.items.forEach((item, idx) => {
      const isChecked = item.ticked_by && item.ticked_by.length > 0;
      
      let commentsHtml = '';
      if (item.comments) {
        item.comments.forEach(c => {
          commentsHtml += `<div class="mp-comment"><strong>${c.author}</strong>: ${c.text}</div>`;
        });
      }

      itemsHtml += `
        <div class="mp-checklist-item" data-id="${item.agenda_item_id}">
          <div class="mp-checklist-header">
            <input type="checkbox" class="mp-checkbox" id="mp-cb-${idx}" ${isChecked ? 'checked' : ''}>
            <label class="mp-item-text" for="mp-cb-${idx}">${item.text || 'Agenda Item'}</label>
          </div>
          <div class="mp-comments">
            ${commentsHtml}
            <textarea class="mp-comment-input" placeholder="Add a comment..." data-id="${item.agenda_item_id}"></textarea>
          </div>
        </div>
      `;
    });
  }

  overlayContainer.innerHTML = `
    <div class="mp-header">
      <h2 class="mp-title"><div class="mp-title-indicator"></div> MeetingPilot Checklist</h2>
      <button class="mp-close-btn">&times;</button>
    </div>
    <div class="mp-content">
      ${itemsHtml || '<div style="font-size:13px; color:#64748b; text-align:center;">No checklist items found for this meeting.</div>'}
    </div>
    <div class="mp-footer">
      <button class="mp-btn-save">Save & Close</button>
    </div>
  `;

  // Attach event listeners
  overlayContainer.querySelector('.mp-close-btn').addEventListener('click', hideOverlay);
  overlayContainer.querySelector('.mp-btn-save').addEventListener('click', saveAndClose);
  
  // Track interaction
  overlayContainer.addEventListener('click', markInteraction);
  overlayContainer.addEventListener('input', markInteraction);
}

function markInteraction() {
  hasInteracted = true;
  clearTimeout(initialHideTimeout);
  
  // If user interacts, set a new 10-second timeout to auto-hide if they go idle
  clearTimeout(interactionTimeout);
  interactionTimeout = setTimeout(() => {
    saveAndClose();
  }, 10000);
}

function showOverlay() {
  if (isOverlayVisible) return;
  renderOverlay();
  setTimeout(() => overlayContainer.classList.add('mp-visible'), 50);
  isOverlayVisible = true;
  hasInteracted = false;

  // Auto-hide in 5 seconds if no interaction
  clearTimeout(initialHideTimeout);
  initialHideTimeout = setTimeout(() => {
    if (!hasInteracted) {
      hideOverlay();
    }
  }, 5000);
}

function hideOverlay() {
  if (overlayContainer) {
    overlayContainer.classList.remove('mp-visible');
    isOverlayVisible = false;
    clearTimeout(initialHideTimeout);
    clearTimeout(interactionTimeout);
  }
}

async function saveAndClose() {
  hideOverlay();
  
  if (!currentMeeting || !currentChecklist) return;

  // Gather updated data
  const updatedItems = [...currentChecklist.items];
  
  const itemDivs = overlayContainer.querySelectorAll('.mp-checklist-item');
  itemDivs.forEach(div => {
    const id = div.getAttribute('data-id');
    const isChecked = div.querySelector('.mp-checkbox').checked;
    const newComment = div.querySelector('.mp-comment-input').value.trim();
    
    const itemIndex = updatedItems.findIndex(i => i.agenda_item_id === id);
    if (itemIndex >= 0) {
      // Update ticked status (simple toggle for now)
      if (isChecked && (!updatedItems[itemIndex].ticked_by || updatedItems[itemIndex].ticked_by.length === 0)) {
        updatedItems[itemIndex].ticked_by = ['Me']; // Placeholder for actual user name
      } else if (!isChecked) {
        updatedItems[itemIndex].ticked_by = [];
      }

      // Add new comment
      if (newComment) {
        if (!updatedItems[itemIndex].comments) updatedItems[itemIndex].comments = [];
        updatedItems[itemIndex].comments.push({
          author: 'Me', // Placeholder
          text: newComment,
          ts: new Date().toISOString()
        });
      }
    }
  });

  // Send PATCH request
  chrome.runtime.sendMessage({
    type: 'API_CALL',
    method: 'PATCH',
    url: `${API_URL}/api/meetings/${currentMeeting.meeting_id}/checklist`,
    body: { items: updatedItems }
  });

  // Update local cache
  currentChecklist.items = updatedItems;
}

// Main initializer
async function init() {
  currentMeeting = await fetchMeetingData();
  if (currentMeeting && currentMeeting.meeting_id) {
    currentChecklist = await fetchChecklist(currentMeeting.meeting_id);
    
    // Initial popup
    showOverlay();

    // Set interval for every 10 minutes (600000 ms)
    setInterval(() => {
      showOverlay();
    }, 600000);
    
    // Tab close detection for auto-send
    window.addEventListener('beforeunload', () => {
      // Ping backend that meet has closed
      navigator.sendBeacon(`${API_URL}/api/extension/meet-closed?meet_link=${encodeURIComponent(window.location.href.split('?')[0])}`);
    });
  }
}

// Start after a slight delay to ensure Google Meet is loaded
setTimeout(init, 3000);
