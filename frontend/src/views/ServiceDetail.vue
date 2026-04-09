<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ArrowLeft, History, Clock, ChevronRight, BarChart2 } from 'lucide-vue-next';
import StatusBadge from '../components/StatusBadge.vue';
import StatusBar from '../components/StatusBar.vue';
import IncidentTimeline from '../components/IncidentTimeline.vue';
import ThemeToggle from '../components/ThemeToggle.vue';

const route  = useRoute();
const router = useRouter();
const slug   = route.params.slug;

const service           = ref(null);
const history           = ref([]);
const openIncidents     = ref([]);
const resolvedIncidents = ref([]);
const resolvedTotal     = ref(0);
const statusLog         = ref([]);
const statusLogTotal    = ref(0);
const logExpanded       = ref(false);
const uptime            = ref(null);
const error             = ref(null);

const LOG_PREVIEW = 10;
const visibleLog  = computed(() => logExpanded.value ? statusLog.value : statusLog.value.slice(0, LOG_PREVIEW));

async function fetchData() {
  try {
    const [histRes, incRes, logRes, uptimeRes] = await Promise.all([
      fetch(`/api/v1/services/${slug}/history`),
      fetch(`/api/v1/services/${slug}/incidents`),
      fetch(`/api/v1/services/${slug}/log`),
      fetch(`/api/v1/services/${slug}/uptime`),
    ]);
    if (!histRes.ok) throw new Error('Not found');
    const histData = await histRes.json();
    const incData  = await incRes.json();
    service.value           = histData.service;
    history.value           = histData.history;
    openIncidents.value     = incData.open;
    resolvedIncidents.value = incData.resolved;
    if (logRes.ok) {
      const logData = await logRes.json();
      statusLog.value      = logData.log;
      statusLogTotal.value = logData.total;
    }
    if (uptimeRes.ok) uptime.value = await uptimeRes.json();
    resolvedTotal.value = incData.resolved_total ?? incData.resolved.length;
  } catch (e) { error.value = e.message; }
}

function formatDuration(mins) {
  if (mins < 60) return `${mins}m`;
  const h = Math.floor(mins / 60), m = mins % 60;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

function formatDate(iso) {
  return new Date(iso).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function formatDay(dateStr) {
  return new Date(dateStr + 'T00:00:00').toLocaleDateString([], { month: 'short', day: 'numeric' });
}

const statusDotClass = {
  operational: 'bg-green-500', performance_issues: 'bg-yellow-400',
  partial_outage: 'bg-orange-500', major_outage: 'bg-red-600',
  under_maintenance: 'bg-blue-500', unknown: 'bg-gray-400',
};

const dayColorClass = {
  operational:        'bg-green-500',
  performance_issues: 'bg-yellow-400',
  partial_outage:     'bg-orange-500',
  major_outage:       'bg-red-600',
  under_maintenance:  'bg-blue-500',
  unknown:            'bg-gray-200 dark:bg-gray-700',
};

const statusLabel = {
  operational: 'Operational', performance_issues: 'Performance Issues',
  partial_outage: 'Partial Outage', major_outage: 'Major Outage',
  under_maintenance: 'Under Maintenance', unknown: 'No data',
};

onMounted(fetchData);
</script>

<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-950 transition-colors">
    <div class="max-w-4xl mx-auto px-4 py-10">

      <!-- Top bar -->
      <div class="flex items-center justify-between mb-6">
        <button
          class="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm text-gray-600 dark:text-gray-400 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors shadow-sm"
          @click="router.back()"
        >
          <ArrowLeft class="w-4 h-4" :stroke-width="1.75" />
          Back
        </button>
        <ThemeToggle />
      </div>

      <div v-if="error" class="px-4 py-3 bg-red-500/10 border border-red-500/30 rounded text-red-600 dark:text-red-400 text-sm">{{ error }}</div>

      <template v-if="service">
        <!-- Breadcrumb + status -->
        <div class="mb-6 flex items-start justify-between gap-4">
          <div>
            <div v-if="service.section_name" class="flex items-center gap-1 text-xs text-gray-400 dark:text-gray-600 mb-1">
              <span>{{ service.section_name }}</span>
              <ChevronRight class="w-3 h-3" :stroke-width="2" />
              <span class="text-gray-500 dark:text-gray-400">{{ service.name }}</span>
            </div>
            <h1 class="text-xl font-bold text-gray-900 dark:text-white">{{ service.name }}</h1>
            <p v-if="service.description" class="text-gray-500 dark:text-gray-400 text-sm mt-1">{{ service.description }}</p>
            <p v-if="service.updated_at" class="text-xs text-gray-400 dark:text-gray-600 mt-1">Last updated: {{ formatDate(service.updated_at) }}</p>
          </div>
          <StatusBadge :status="service.status" />
        </div>

        <!-- 24h History -->
        <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-4 mb-4 shadow-sm dark:shadow-none">
          <div class="flex items-center justify-between mb-3">
            <h2 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">24-Hour History</h2>
            <span class="text-xs text-gray-400 dark:text-gray-600">5-min intervals · {{ history.length }} blocks</span>
          </div>
          <StatusBar :history="history" />
        </div>

        <!-- 30-day uptime summary -->
        <div v-if="uptime" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-4 mb-6 shadow-sm dark:shadow-none">
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center gap-2">
              <BarChart2 class="w-4 h-4 text-gray-400 dark:text-gray-500" :stroke-width="1.75" />
              <h2 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">30-Day Summary</h2>
            </div>
            <span v-if="uptime.uptime_pct !== null" class="text-xs font-semibold"
              :class="uptime.uptime_pct >= 99 ? 'text-green-500' : uptime.uptime_pct >= 95 ? 'text-yellow-500' : 'text-red-500'">
              {{ uptime.uptime_pct }}% uptime
            </span>
          </div>
          <div class="flex gap-px h-8 rounded overflow-hidden">
            <div
              v-for="day in uptime.days" :key="day.date"
              class="flex-1 cursor-default transition-opacity hover:opacity-75 group relative"
              :class="dayColorClass[day.status] || 'bg-gray-200 dark:bg-gray-700'"
              :title="`${formatDay(day.date)}: ${statusLabel[day.status] || day.status}`"
            />
          </div>
          <div class="flex justify-between text-xs text-gray-400 dark:text-gray-600 mt-1.5">
            <span>{{ formatDay(uptime.days[0]?.date) }}</span>
            <span>Today</span>
          </div>
        </div>

        <!-- Status Log -->
        <div v-if="statusLog.length" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg overflow-hidden mb-6 shadow-sm dark:shadow-none">
          <div class="px-4 py-3 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between gap-2">
            <div class="flex items-center gap-2">
              <History class="w-4 h-4 text-gray-400 dark:text-gray-500" :stroke-width="1.75" />
              <h2 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status Log</h2>
            </div>
            <span class="text-xs text-gray-400 dark:text-gray-600">{{ statusLogTotal }} entries</span>
          </div>
          <div class="divide-y divide-gray-100 dark:divide-gray-800">
            <div v-for="(entry, i) in visibleLog" :key="i" class="flex items-start gap-3 px-4 py-2.5">
              <div class="w-2 h-2 rounded-full shrink-0 mt-1.5" :class="statusDotClass[entry.status] || 'bg-gray-400'" />
              <div class="flex-1 min-w-0">
                <StatusBadge :status="entry.status" />
                <p v-if="entry.note" class="text-xs text-gray-500 dark:text-gray-400 mt-1 truncate">{{ entry.note }}</p>
              </div>
              <div class="text-right shrink-0">
                <div class="text-xs text-gray-500 dark:text-gray-400">{{ formatDate(entry.started_at) }}</div>
                <div class="flex items-center justify-end gap-1 text-xs text-gray-400 dark:text-gray-600 mt-0.5">
                  <Clock class="w-3 h-3" :stroke-width="1.75" />
                  <span v-if="entry.ended_at">{{ formatDuration(entry.duration_minutes) }}</span>
                  <span v-else class="text-green-500 dark:text-green-400">ongoing</span>
                </div>
              </div>
            </div>
          </div>
          <button v-if="statusLog.length > LOG_PREVIEW" @click="logExpanded = !logExpanded"
            class="w-full px-4 py-2 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 border-t border-gray-100 dark:border-gray-800 transition-colors">
            {{ logExpanded ? 'Show less' : `Show ${statusLog.length - LOG_PREVIEW} more` }}
          </button>
        </div>

        <!-- Incidents -->
        <div>
          <h2 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">Incidents</h2>
          <div v-if="!openIncidents.length && !resolvedIncidents.length" class="text-sm text-gray-400 dark:text-gray-600 text-center py-8">No incidents reported.</div>
          <template v-else>
            <div v-if="openIncidents.length" class="mb-6">
              <h3 class="text-xs text-orange-500 uppercase tracking-wider mb-3">Open</h3>
              <IncidentTimeline :incidents="openIncidents" />
            </div>
            <div v-if="resolvedIncidents.length">
              <div class="flex items-center justify-between mb-3">
                <h3 class="text-xs text-gray-400 dark:text-gray-500 uppercase tracking-wider">Recently Resolved</h3>
                <span v-if="resolvedTotal > resolvedIncidents.length" class="text-xs text-gray-400 dark:text-gray-600">Showing {{ resolvedIncidents.length }} of {{ resolvedTotal }}</span>
              </div>
              <IncidentTimeline :incidents="resolvedIncidents" />
            </div>
          </template>
        </div>
      </template>

      <div v-else-if="!error" class="space-y-4">
        <div v-for="i in 3" :key="i" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg h-24 animate-pulse" />
      </div>
    </div>
  </div>
</template>
