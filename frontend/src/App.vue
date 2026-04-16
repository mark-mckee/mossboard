<script setup>
import { onMounted } from 'vue';
import { useTheme }  from './composables/useTheme.js';
import { useLayout } from './composables/useLayout.js';

const { setDefault } = useTheme();
const { setWide }    = useLayout();

onMounted(async () => {
  try {
    const res = await fetch('/api/v1/status');
    if (res.ok) {
      const data = await res.json();
      if (data.default_theme) setDefault(data.default_theme);
      setWide(data.wide_layout ?? false);
    }
  } catch {
    // network error — keep defaults
  }
});
</script>

<template>
  <router-view />
</template>
