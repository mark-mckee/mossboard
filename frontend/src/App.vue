<script setup>
import { onMounted } from 'vue';
import { useTheme } from './composables/useTheme.js';

const { setDefault } = useTheme();

onMounted(async () => {
  try {
    const res = await fetch('/api/v1/status');
    if (res.ok) {
      const data = await res.json();
      if (data.default_theme) setDefault(data.default_theme);
    }
  } catch {
    // network error — keep current theme
  }
});
</script>

<template>
  <router-view />
</template>
