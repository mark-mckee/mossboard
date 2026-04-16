<script setup>
import { ref, onMounted } from 'vue';

const noDataBehavior       = ref('unknown');
const siteTitle            = ref('MOSSBoard');
const defaultTheme         = ref('dark');
const showIncidentTimeline = ref(false);
const incidentTimelineDays = ref(7);
const wideLayout           = ref(false);
const saved                = ref(false);
const loading              = ref(true);

const NO_DATA_OPTIONS = [
  {
    value: 'unknown',
    label: 'Unknown',
    desc:  'Periods without data are shown as unknown and counted as downtime.',
  },
  {
    value: 'operational',
    label: 'Operational (optimistic)',
    desc:  'Periods without data are assumed operational and counted as uptime.',
  },
  {
    value: 'exclude',
    label: 'Exclude',
    desc:  'Periods without data are excluded from uptime calculations entirely.',
  },
];

const THEME_OPTIONS = [
  { value: 'dark',  label: 'Dark'  },
  { value: 'light', label: 'Light' },
];

async function fetchSettings() {
  const res = await fetch('/api/v1/admin/settings');
  if (res.ok) {
    const data       = await res.json();
    noDataBehavior.value       = data.no_data_behavior;
    siteTitle.value            = data.site_title ?? 'MOSSBoard';
    defaultTheme.value         = data.default_theme ?? 'dark';
    showIncidentTimeline.value = data.show_incident_timeline ?? false;
    incidentTimelineDays.value = data.incident_timeline_days ?? 7;
    wideLayout.value           = data.wide_layout ?? false;
  }
  loading.value = false;
}

async function save() {
  const res = await fetch('/api/v1/admin/settings', {
    method:  'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({
      no_data_behavior:       noDataBehavior.value,
      site_title:             siteTitle.value,
      default_theme:          defaultTheme.value,
      show_incident_timeline: showIncidentTimeline.value,
      incident_timeline_days: incidentTimelineDays.value,
      wide_layout:            wideLayout.value,
    }),
  });
  if (res.ok) {
    saved.value = true;
    setTimeout(() => { saved.value = false; }, 2000);
  }
}

onMounted(fetchSettings);
</script>

<template>
  <div class="p-8 space-y-6 max-w-xl">
    <div>
      <h1 class="text-lg font-bold text-gray-900 dark:text-white">Settings</h1>
      <p class="text-xs text-gray-400 dark:text-gray-600 mt-0.5">Global configuration for the status board</p>
    </div>

    <div v-if="!loading" class="space-y-5">

      <!-- Site title -->
      <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5 shadow-sm dark:shadow-none">
        <h2 class="text-sm font-semibold text-gray-900 dark:text-white mb-1">Site title</h2>
        <p class="text-xs text-gray-400 dark:text-gray-600 mb-3">
          Displayed in the header of the public status page and the monitor view.
        </p>
        <input
          v-model="siteTitle"
          type="text"
          placeholder="MOSSBoard"
          class="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 transition-colors"
        />
      </div>

      <!-- Default theme -->
      <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5 shadow-sm dark:shadow-none">
        <h2 class="text-sm font-semibold text-gray-900 dark:text-white mb-1">Default theme</h2>
        <p class="text-xs text-gray-400 dark:text-gray-600 mb-3">
          Applied on first visit before the user makes an explicit choice. Stored browser preferences always take priority.
        </p>
        <div class="flex gap-3">
          <label
            v-for="opt in THEME_OPTIONS" :key="opt.value"
            class="flex items-center gap-2.5 px-4 py-2.5 rounded-lg border cursor-pointer transition-colors flex-1 justify-center"
            :class="defaultTheme === opt.value
              ? 'border-gray-400 dark:border-gray-500 bg-gray-50 dark:bg-gray-800'
              : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800/50'"
          >
            <input type="radio" :value="opt.value" v-model="defaultTheme" class="accent-gray-700 dark:accent-gray-400" />
            <span class="text-sm font-medium text-gray-800 dark:text-gray-200">{{ opt.label }}</span>
          </label>
        </div>
      </div>

      <!-- Wide layout -->
      <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5 shadow-sm dark:shadow-none">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h2 class="text-sm font-semibold text-gray-900 dark:text-white mb-1">Wide layout</h2>
            <p class="text-xs text-gray-400 dark:text-gray-600">
              Expand the public status page and service detail pages from 896 px to 1152 px. Useful for boards with many services or wide metric charts.
            </p>
          </div>
          <label class="relative inline-flex items-center cursor-pointer shrink-0 mt-0.5">
            <input type="checkbox" v-model="wideLayout" class="sr-only peer" />
            <div class="w-9 h-5 bg-gray-200 dark:bg-gray-700 peer-checked:bg-gray-700 dark:peer-checked:bg-gray-400 rounded-full transition-colors
                        after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:w-4 after:h-4
                        after:rounded-full after:bg-white after:transition-transform
                        peer-checked:after:translate-x-4" />
          </label>
        </div>
      </div>

      <!-- Incident timeline on status page -->
      <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5 shadow-sm dark:shadow-none">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h2 class="text-sm font-semibold text-gray-900 dark:text-white mb-1">Incident timeline</h2>
            <p class="text-xs text-gray-400 dark:text-gray-600">
              Show a day-grouped timeline of incidents at the bottom of the public status page.
            </p>
          </div>
          <label class="relative inline-flex items-center cursor-pointer shrink-0 mt-0.5">
            <input type="checkbox" v-model="showIncidentTimeline" class="sr-only peer" />
            <div class="w-9 h-5 bg-gray-200 dark:bg-gray-700 peer-checked:bg-gray-700 dark:peer-checked:bg-gray-400 rounded-full transition-colors
                        after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:w-4 after:h-4
                        after:rounded-full after:bg-white after:transition-transform
                        peer-checked:after:translate-x-4" />
          </label>
        </div>
        <div class="mt-4 flex items-center gap-3">
          <label class="text-xs text-gray-500 dark:text-gray-400 shrink-0">Show last</label>
          <input
            v-model.number="incidentTimelineDays"
            type="number" min="1" max="90"
            class="w-20 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-900 dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 transition-colors"
          />
          <label class="text-xs text-gray-500 dark:text-gray-400 shrink-0">days</label>
        </div>
      </div>

      <!-- No-data behavior -->
      <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5 shadow-sm dark:shadow-none">
        <h2 class="text-sm font-semibold text-gray-900 dark:text-white mb-1">No-data behavior</h2>
        <p class="text-xs text-gray-400 dark:text-gray-600 mb-4">
          How to handle time periods where no monitoring data was collected (e.g. before the service was created, or during gaps in snapshots).
          Affects uptime percentages and bar colors in the 30-day and 12-month summaries.
        </p>
        <div class="space-y-2">
          <label
            v-for="opt in NO_DATA_OPTIONS" :key="opt.value"
            class="flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors"
            :class="noDataBehavior === opt.value
              ? 'border-gray-400 dark:border-gray-500 bg-gray-50 dark:bg-gray-800'
              : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800/50'"
          >
            <input type="radio" :value="opt.value" v-model="noDataBehavior" class="mt-0.5 accent-gray-700 dark:accent-gray-400 shrink-0" />
            <div>
              <div class="text-sm font-medium text-gray-800 dark:text-gray-200">{{ opt.label }}</div>
              <div class="text-xs text-gray-400 dark:text-gray-600 mt-0.5">{{ opt.desc }}</div>
            </div>
          </label>
        </div>
      </div>

      <!-- Save -->
      <div class="flex items-center gap-3">
        <button @click="save"
          class="bg-gray-800 hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 text-white text-xs px-4 py-1.5 rounded-lg transition-colors">
          Save
        </button>
        <span v-if="saved" class="text-xs text-green-500 dark:text-green-400">Saved!</span>
      </div>

    </div>

    <!-- Loading skeleton -->
    <div v-else class="space-y-5">
      <div v-for="i in 3" :key="i"
        class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl h-32 animate-pulse shadow-sm dark:shadow-none" />
    </div>
  </div>
</template>
