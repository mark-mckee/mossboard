<script setup>
import { useRouter } from 'vue-router';
import StatusBadge from './StatusBadge.vue';

const props = defineProps({ service: Object });
const router = useRouter();
</script>

<template>
  <div
    class="flex items-center justify-between py-3 px-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 border-b border-gray-100 dark:border-gray-800/50 last:border-0 cursor-pointer transition-colors"
    @click="router.push(`/services/${service.slug}`)"
  >
    <div class="flex-1 min-w-0">
      <span class="text-sm text-gray-800 dark:text-gray-200 font-medium">{{ service.name }}</span>
      <span v-if="service.description" class="ml-3 text-xs text-gray-400 dark:text-gray-500 truncate">
        {{ service.description }}
      </span>
    </div>
    <StatusBadge :status="service.status" class="ml-4 shrink-0" />
  </div>
</template>
