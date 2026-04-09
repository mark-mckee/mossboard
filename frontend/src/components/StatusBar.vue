<script setup>
import { ref } from 'vue';

defineProps({ history: { type: Array, default: () => [] } });

const tooltip = ref(null);
const tooltipX = ref(0);
const tooltipY = ref(0);

const blockClass = {
  operational:        'bg-green-500',
  performance_issues: 'bg-yellow-400',
  partial_outage:     'bg-orange-500',
  major_outage:       'bg-red-600',
  under_maintenance:  'bg-blue-500',
  unknown:            'bg-gray-200 dark:bg-gray-700',
};

const statusLabel = {
  operational:        'Operational',
  performance_issues: 'Performance Issues',
  partial_outage:     'Partial Outage',
  major_outage:       'Major Outage',
  under_maintenance:  'Under Maintenance',
  unknown:            'No data',
};

function showTooltip(block, event) {
  const start = new Date(block.block_start);
  const end   = new Date(block.block_end);
  const fmt   = (d) => d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  tooltip.value = { time: `${fmt(start)} – ${fmt(end)}`, status: statusLabel[block.status] || block.status };
  tooltipX.value = event.clientX;
  tooltipY.value = event.clientY;
}

function hideTooltip() { tooltip.value = null; }
</script>

<template>
  <div class="relative">
    <!-- Dense bar — no gap between blocks so 288 fit cleanly -->
    <div class="flex h-8 rounded overflow-hidden">
      <div
        v-for="(block, i) in history"
        :key="i"
        class="flex-1 cursor-default transition-opacity hover:opacity-75"
        :class="blockClass[block.status] || 'bg-gray-200 dark:bg-gray-700'"
        @mousemove="showTooltip(block, $event)"
        @mouseleave="hideTooltip"
      />
    </div>
    <div class="flex justify-between mt-1 text-xs text-gray-400 dark:text-gray-600">
      <span>24 h ago</span>
      <span>now</span>
    </div>
    <teleport to="body">
      <div
        v-if="tooltip"
        class="fixed z-50 pointer-events-none bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded px-3 py-2 text-xs shadow-lg"
        :style="{ left: tooltipX + 12 + 'px', top: tooltipY - 44 + 'px' }"
      >
        <div class="text-gray-500 dark:text-gray-400">{{ tooltip.time }}</div>
        <div class="text-gray-900 dark:text-white font-medium">{{ tooltip.status }}</div>
      </div>
    </teleport>
  </div>
</template>
