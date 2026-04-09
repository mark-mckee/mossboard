<script setup>
import { useTheme } from '../composables/useTheme.js';
import AppIcon from './AppIcon.vue';

const { isDark, toggle } = useTheme();
</script>

<template>
  <button
    @click="toggle"
    class="p-1.5 rounded-md transition-colors text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
    :title="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
  >
    <AppIcon :name="isDark ? 'sun' : 'moon'" class="w-4 h-4" />
  </button>
</template>
