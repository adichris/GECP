document.addEventListener('DOMContentLoaded', () => {
  const button = document.getElementById('shuffle-guest');
  if (!button) return;
  button.addEventListener('click', async () => {
    button.disabled = true;
    const status = document.getElementById('guest-shuffle-status');
    try {
      const response = await fetch(button.dataset.url, {credentials: 'same-origin'});
      if (!response.ok) throw new Error('Request failed');
      const profile = await response.json();
      document.getElementById('id_guest_name').value = profile.guest_name;
      document.getElementById('id_guest_emoji').value = profile.guest_emoji;
      status.textContent = ' Suggested: ' + profile.guest_emoji + ' ' + profile.guest_name;
    } catch (_) { status.textContent = ' Could not shuffle. Enter a name and choose an emoji below.'; }
    finally { button.disabled = false; }
  });
});
