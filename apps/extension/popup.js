const API_URL = 'http://localhost:8000';

let currentChecklist = null;
let currentMeeting = null;

document.addEventListener('DOMContentLoaded', () => {
  const viewDisconnected = document.getElementById('view-disconnected');
  const viewActive = document.getElementById('view-active-meet');
  const viewUpcoming = document.getElementById('view-upcoming');
  const dashboardBtn = document.getElementById('open-dashboard-btn');
  const saveBtn = document.getElementById('save-checklist-btn');

  function showView(view) {
    viewDisconnected.classList.add('hidden');
    viewActive.classList.add('hidden');
    viewUpcoming.classList.add('hidden');
    view.classList.remove('hidden');
  }

  dashboardBtn.addEventListener('click', () => {
    chrome.tabs.create({ url: 'http://localhost:5173/' });
  });

  saveBtn.addEventListener('click', saveChecklist);

  // Check auth
  chrome.storage.local.get(['mp_auth_token'], (result) => {
    if (!result.mp_auth_token) {
      showView(viewDisconnected);
      return;
    }

    // Authenticated, check active tab
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs.length === 0) {
        loadUpcoming();
        return;
      }
      
      const tabUrl = tabs[0].url;
      if (tabUrl && tabUrl.includes('meet.google.com')) {
        // Query backend for this meet link
        chrome.runtime.sendMessage({
          type: 'API_CALL',
          method: 'GET',
          url: `${API_URL}/api/extension/meeting-by-link?meet_link=${encodeURIComponent(tabUrl.split('?')[0])}`
        }, (res) => {
          if (res && res.data && res.data.meeting_id) {
            currentMeeting = res.data;
            document.getElementById('active-meet-title').textContent = currentMeeting.title || 'Meeting';
            showView(viewActive);
            loadChecklist(currentMeeting.meeting_id);
          } else {
            loadUpcoming();
          }
        });
      } else {
        loadUpcoming();
      }
    });
  });

  function loadUpcoming() {
    showView(viewUpcoming);
    chrome.runtime.sendMessage({
      type: 'API_CALL',
      method: 'GET',
      url: `${API_URL}/api/extension/upcoming-meetings`
    }, (res) => {
      const listEl = document.getElementById('upcoming-list');
      if (!res || !res.data) {
        listEl.innerHTML = '<div class="loading-text">Failed to load meetings.</div>';
        return;
      }
      
      if (res.data.length === 0) {
        listEl.innerHTML = '<div class="loading-text">No upcoming meetings scheduled.</div>';
        return;
      }

      listEl.innerHTML = res.data.map(m => {
        const time = new Date(m.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        return `
          <div class="meeting-item">
            <div class="meeting-item-title">${m.title}</div>
            <div class="meeting-item-time">${time}</div>
          </div>
        `;
      }).join('');
    });
  }

  function loadChecklist(meetingId) {
    chrome.runtime.sendMessage({
      type: 'API_CALL',
      method: 'GET',
      url: `${API_URL}/api/meetings/${meetingId}/checklist`
    }, (res) => {
      const container = document.getElementById('checklist-container');
      if (!res || !res.data || !res.data.items) {
        container.innerHTML = '<div class="loading-text">No checklist found.</div>';
        return;
      }

      currentChecklist = res.data;
      
      let html = '';
      currentChecklist.items.forEach((item, idx) => {
        const isChecked = item.ticked_by && item.ticked_by.length > 0;
        let commentsHtml = '';
        if (item.comments) {
          item.comments.forEach(c => {
            commentsHtml += `<div class="comment"><strong>${c.author}</strong>: ${c.text}</div>`;
          });
        }

        html += `
          <div class="checklist-item" data-id="${item.agenda_item_id}">
            <div class="checklist-header">
              <input type="checkbox" class="checkbox" id="cb-${idx}" ${isChecked ? 'checked' : ''}>
              <label class="item-text" for="cb-${idx}">${item.text || 'Agenda Item'}</label>
            </div>
            <div class="comments-section">
              ${commentsHtml}
              <textarea class="comment-input" placeholder="Add a comment..." data-id="${item.agenda_item_id}"></textarea>
            </div>
          </div>
        `;
      });
      
      container.innerHTML = html;
    });
  }

  function saveChecklist() {
    if (!currentMeeting || !currentChecklist) return;

    const btn = document.getElementById('save-checklist-btn');
    const status = document.getElementById('save-status');
    btn.textContent = 'Saving...';
    btn.disabled = true;

    const updatedItems = [...currentChecklist.items];
    const itemDivs = document.querySelectorAll('.checklist-item');
    
    itemDivs.forEach(div => {
      const id = div.getAttribute('data-id');
      const isChecked = div.querySelector('.checkbox').checked;
      const newComment = div.querySelector('.comment-input').value.trim();
      
      const itemIndex = updatedItems.findIndex(i => i.agenda_item_id === id);
      if (itemIndex >= 0) {
        if (isChecked && (!updatedItems[itemIndex].ticked_by || updatedItems[itemIndex].ticked_by.length === 0)) {
          updatedItems[itemIndex].ticked_by = ['Me']; 
        } else if (!isChecked) {
          updatedItems[itemIndex].ticked_by = [];
        }

        if (newComment) {
          if (!updatedItems[itemIndex].comments) updatedItems[itemIndex].comments = [];
          updatedItems[itemIndex].comments.push({
            author: 'Me',
            text: newComment,
            ts: new Date().toISOString()
          });
        }
      }
    });

    chrome.runtime.sendMessage({
      type: 'API_CALL',
      method: 'PATCH',
      url: `${API_URL}/api/meetings/${currentMeeting.meeting_id}/checklist`,
      body: { items: updatedItems }
    }, (res) => {
      btn.textContent = 'Save Changes';
      btn.disabled = false;
      if (res && res.error) {
        status.textContent = 'Failed to save.';
        status.style.color = '#ef4444';
      } else {
        status.textContent = 'Saved successfully!';
        status.style.color = '#10b981';
        setTimeout(() => status.textContent = '', 3000);
        // Refresh local view
        document.querySelectorAll('.comment-input').forEach(i => i.value = '');
        loadChecklist(currentMeeting.meeting_id);
      }
    });
  }
});
