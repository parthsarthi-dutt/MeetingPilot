chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'SAVE_TOKEN') {
    chrome.storage.local.set({ mp_auth_token: message.token }, () => {
      sendResponse({ success: true });
    });
    return true; // Keep message channel open for async response
  }

  if (message.type === 'API_CALL') {
    chrome.storage.local.get(['mp_auth_token'], (result) => {
      const token = result.mp_auth_token;
      if (!token) {
        sendResponse({ error: 'No auth token found' });
        return;
      }

      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      };

      const options = {
        method: message.method || 'GET',
        headers: headers
      };

      if (message.body) {
        options.body = JSON.stringify(message.body);
      }

      fetch(message.url, options)
        .then(res => {
          if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
          }
          if (res.status === 204) return null;
          return res.json();
        })
        .then(data => sendResponse({ data }))
        .catch(error => sendResponse({ error: error.message }));
    });
    return true; 
  }
});
