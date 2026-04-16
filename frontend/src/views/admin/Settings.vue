<script setup>
import { ref, onMounted } from 'vue';

const setting = ref('unknown');
const saved = ref(false);
const loading = ref(true);

const OPTIONS = [
  {
    value: 'unknown',
    label: 'Unknown',
    desc: 'Periods without data are shown as unknown and counted as downtime.',
  },
  {
    value: 'operational',
    label: 'Operational (optimistic)',
    desc: 'Periods without data are assumed operational and counted as uptime.',
  },
  {
    value: 'exclude',
    label: 'Exclude',
    desc: 'Periods without data are excluded from uptime calculations entirely.',
  },
];

async function fetchSettings() {
  const res = await fetch('/api/v1/admin/settings');
  if (res.ok) {
    const data = await res.json();
    setting.value = data.no_data_behavior;
  }
  loading.value = false;
}

async function save() {
  const res = await fetch('/api/v1/admin/settings', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ no_data_behavior: setting.value }),
  });
  if (res.ok) {
    saved.value = true;
    setTimeout(() => { saved.value = false; }, 2000);
  }
}

onMounted(fetchSettings);
</script>

<template>
  <div class="p-8">
    <div class="mb-6">
      <h1 class="text-lg font-bold text-gray-900 dark:text-white">Settings</h1>
      <p class="text-xs text-gray-400 dark:text-gray-600 mt-0.5">Global configuration for the status board</p>
    </div>

    <div v-if="!loading" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5 shadow-sm dark:shadow-none max-w-xl">
      <h2 class="text-sm font-semibold text-gray-900 dark:text-white mb-1">No-data behavior</h2>
      <p class="text-xs text-gray-400 dark:text-gray-600 mb-4">
        How to handle time periods where no monitoring data was collected (e.g. before the service was created, or during gaps in snapshots).
        Affects uptime percentages and bar colors in the 30-day and 12-month summaries.
      </p>

      <div class="space-y-2">
        <label
          v-for="opt in OPTIONS" :key="opt.value"
          class="flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors"
          :class="setting === opt.value
            ? 'border-gray-400 dark:border-gray-500 bg-gray-50 dark:bg-gray-800'
            : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800/50'"
        >
          <input type="radio" :value="opt.value" v-model="setting" class="mt-0.5 accent-gray-700 dark:accent-gray-400 shrink-0" />
          <div>
            <div class="text-sm font-medium text-gray-800 dark:text-gray-200">{{ opt.label }}</div>
            <div class="text-xs text-gray-400 dark:text-gray-600 mt-0.5">{{ opt.desc }}</div>
          </div>
        </label>
      </div>

      <div class="flex items-center gap-3 mt-4">
        <button @click="save"
          class="bg-gray-800 hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 text-white text-xs px-4 py-1.5 rounded-lg transition-colors">
          Save
        </button>
        <span v-if="saved" class="text-xs text-green-500 dark:text-green-400">Saved!</span>
      </div>
    </div>

    <div v-else class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl h-32 animate-pulse shadow-sm dark:shadow-none max-w-xl" />
  </div>
</template>
