import { ref } from 'vue';

// Read once at module load — null means the user has never explicitly chosen.
const _stored     = localStorage.getItem('theme');
const _hasExplicit = () => localStorage.getItem('theme') !== null;

// Only update the <html> class — never touches localStorage.
function _applyClass(dark) {
  document.documentElement.classList.toggle('dark', dark);
}

// If the user has a stored preference use it; otherwise fall back to dark
// until the server default arrives via setDefault().
const isDark = ref(_stored !== null ? _stored === 'dark' : true);

// Apply on module load (no localStorage write here).
_applyClass(isDark.value);

export function useTheme() {
  /** Explicit toggle by the user — persists the choice in localStorage. */
  function toggle() {
    isDark.value = !isDark.value;
    _applyClass(isDark.value);
    localStorage.setItem('theme', isDark.value ? 'dark' : 'light');
  }

  /**
   * Called once on app startup with the server-configured default.
   * Only takes effect when the user has never explicitly chosen a theme
   * (nothing in localStorage). Does NOT write to localStorage so that
   * future changes to the server default still apply on the next first visit.
   */
  function setDefault(theme) {
    if (_hasExplicit()) return;
    isDark.value = theme === 'dark';
    _applyClass(isDark.value);
  }

  return { isDark, toggle, setDefault };
}
