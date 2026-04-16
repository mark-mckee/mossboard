<script setup>
import { Search, Crosshair, Eye, Check, AlertTriangle, CheckCircle } from 'lucide-vue-next';
import StatusBadge from './StatusBadge.vue';

defineProps({ incidents: { type: Array, default: () => [] } });

const updateIcon = { investigating: Search, identified: Crosshair, monitoring: Eye, resolved: Check };
const updateRing = {
  investigating: 'bg-yellow-400/10 border-yellow-400/30 text-yellow-500',
  identified:    'bg-orange-500/10 border-orange-500/30 text-orange-400',
  monitoring:    'bg-blue-500/10  border-blue-500/30  text-blue-400',
  resolved:      'bg-green-500/10 border-green-500/30 text-green-400',
};

function formatDate(iso) {
  return new Date(iso).toLocaleString([], { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}
</script>

<template>
  <div class="space-y-5">
    <div
      v-for="incident in incidents"
      :key="incident.id"
      class="bg-white dark:bg-gray-900 border rounded-lg overflow-hidden shadow-sm dark:shadow-none"
      :class="incident.resolved_at ? 'border-gray-200 dark:border-gray-800' : 'border-orange-400/40'"
    >
      <!-- Header -->
      <div class="px-4 py-3 border-b border-gray-100 dark:border-gray-800 flex items-start justify-between gap-3">
        <div>
          <div class="flex items-center gap-2">
            <component
              :is="incident.resolved_at ? CheckCircle : AlertTriangle"
              class="w-4 h-4 shrink-0"
              :class="incident.resolved_at ? 'text-green-500' : 'text-orange-400'"
              :stroke-width="1.75"
            />
            <span class="font-medium text-gray-900 dark:text-gray-200 text-sm">{{ incident.title }}</span>
          </div>
          <div v-if="incident.section_name || incident.service_name" class="text-xs text-gray-400 dark:text-gray-500 mt-0.5 ml-6">
            <template v-if="incident.section_name">{{ incident.section_name }} › </template>{{ incident.service_name }}
          </div>
        </div>
        <span v-if="!incident.resolved_at" class="text-xs px-2 py-0.5 rounded bg-orange-500/15 text-orange-600 dark:text-orange-400 border border-orange-500/30 shrink-0 mt-0.5">Ongoing</span>
        <span v-else class="text-xs text-gray-400 dark:text-gray-500 shrink-0 mt-0.5">Resolved {{ formatDate(incident.resolved_at) }}</span>
      </div>

      <!-- Updates -->
      <div class="px-4 py-3">
        <div v-for="(update, i) in [...incident.updates].reverse()" :key="i" class="flex gap-3">
          <!-- Icon column -->
          <div class="flex flex-col items-center shrink-0">
            <div class="w-7 h-7 rounded-full flex items-center justify-center mt-0.5 border" :class="updateRing[update.status] || updateRing.investigating">
              <component :is="updateIcon[update.status] || Search" :size="13" :stroke-width="2" />
            </div>
            <div v-if="i < incident.updates.length - 1" class="w-px flex-1 bg-gray-200 dark:bg-gray-800 mt-1 mb-1" />
          </div>
          <!-- Content -->
          <div class="pb-4 min-w-0 flex-1">
            <div class="flex items-center gap-2 mb-1.5">
              <StatusBadge :status="update.status" />
              <span class="text-xs text-gray-400 dark:text-gray-500">{{ formatDate(update.created_at) }}</span>
            </div>
            <p class="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-line">{{ update.message }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
