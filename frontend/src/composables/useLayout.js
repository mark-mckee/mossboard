import { ref } from 'vue';

// Singleton — shared across all pages
const _isWide = ref(false);

export function useLayout() {
  function setWide(wide) {
    _isWide.value = !!wide;
  }
  return { isWide: _isWide, setWide };
}
