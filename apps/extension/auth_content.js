// This script runs on localhost:5173 / MeetingPilot dashboard to grab the token
// MeetingPilot probably stores it in localStorage.
// Let's check `auth-storage` or something similar, or we can just parse cookies.

function extractToken() {
  // Try to find the auth token in localStorage. 
  // Let's iterate through localStorage looking for a token.
  let token = null;
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key.includes('token') || key.includes('auth')) {
      try {
        const val = JSON.parse(localStorage.getItem(key));
        if (val && val.state && val.state.token) {
          token = val.state.token;
          break;
        }
      } catch (e) {
        if (typeof localStorage.getItem(key) === 'string' && localStorage.getItem(key).length > 20) {
          token = localStorage.getItem(key);
        }
      }
    }
  }

  // Assuming standard React Query / Zustand persistence:
  const authStore = localStorage.getItem('auth-storage');
  if (authStore) {
    try {
      const parsed = JSON.parse(authStore);
      if (parsed.state && parsed.state.token) {
        token = parsed.state.token;
      }
    } catch (e) {}
  }

  if (token) {
    // Send it to the background script to save
    chrome.runtime.sendMessage({ type: 'SAVE_TOKEN', token: token }, (response) => {
      if (response && response.success) {
        // Show an alert as requested by the user
        if (!sessionStorage.getItem('mp_ext_alert_shown')) {
          alert('MeetingPilot Extension: Token received and saved successfully!');
          sessionStorage.setItem('mp_ext_alert_shown', 'true');
        }
      }
    });
  }
}

// Run immediately and also listen for changes in case the user logs in
extractToken();
window.addEventListener('storage', extractToken);
