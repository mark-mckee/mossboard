import { ref } from 'vue';

const isDark = ref(
  localStorage.getItem('theme') === null
    ? true  // default dark
    : localStorage.getItem('theme') === 'dark'
);

function applyTheme() {
  if (isDark.value) {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light');
}

// Apply on module load
applyTheme();

export function useTheme() {
  function toggle() {
    isDark.value = !isDark.value;
    applyTheme();
  }
  return { isDark, toggle };
}
