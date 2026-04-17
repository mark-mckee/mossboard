<script setup>
import { ref, onMounted, onUnmounted, computed }  from 'vue';
import { useLayout } from '../composables/useLayout.js';
const { isWide } = useLayout();
import { CheckCircle, Clock, AlertTriangle, XCircle, Wrench, HelpCircle, Calendar, Server, Key, Monitor, AlertCircle, ArrowRight } from 'lucide-vue-next';
import SectionCard  from '../components/SectionCard.vue';
import StatusBadge  from '../components/StatusBadge.vue';
import MetricChart  from '../components/MetricChart.vue';
import ThemeToggle  from '../components/ThemeToggle.vue';

const data        = ref(null);
const maintenance = ref([]);
const incidents   = ref({ open: [], resolved: [], resolved_total: 0, days: 7 });
const metrics     = ref([]);
const metricPts   = ref({});   // metric id → points array
const error       = ref(null);
let interval      = null;

async function fetchAll() {
  try {
    const [sRes, mRes] = await Promise.all([
      fetch('/api/v1/status'),
      fetch('/api/v1/maintenance'),
    ]);
    if (!sRes.ok) throw new Error('Failed to fetch status');
    data.value = await sRes.json();
    if (mRes.ok) maintenance.value = (await mRes.json()).maintenance;

    const [iRes, metricsRes] = await Promise.all([
      fetch(`/api/v1/incidents?days=${data.value?.incident_timeline_days ?? 7}`),
      fetch('/api/v1/metrics'),
    ]);
    if (iRes.ok)       incidents.value = await iRes.json();
    if (metricsRes.ok) {
      metrics.value = (await metricsRes.json()).metrics;
      // Fetch chart points for metrics that have display_chart enabled
      await Promise.all(
        metrics.value
          .filter(m => m.display_chart)
          .map(async m => {
            const r = await fetch(`/api/v1/metrics/${m.id}/points?view=${m.default_view}`);
            if (r.ok) metricPts.value[m.id] = (await r.json()).points;
          })
      );
    }
  } catch (e) { error.value = e.message; }
}

const bannerCfg = computed(() => {
  const s = data.value?.overall_status;
  const map = {
    operational:        { label: 'All Systems Operational',     icon: CheckCircle,    cls: 'bg-green-500/10 border-green-500/25 text-green-700 dark:text-green-400' },
    performance_issues: { label: 'Performance Issues Detected', icon: Clock,          cls: 'bg-yellow-400/10 border-yellow-400/25 text-yellow-700 dark:text-yellow-300' },
    partial_outage:     { label: 'Partial System Outage',       icon: AlertTriangle,  cls: 'bg-orange-500/10 border-orange-500/25 text-orange-700 dark:text-orange-400' },
    major_outage:       { label: 'Major System Outage',         icon: XCircle,        cls: 'bg-red-500/10 border-red-500/25 text-red-700 dark:text-red-400' },
    under_maintenance:  { label: 'Under Maintenance',           icon: Wrench,         cls: 'bg-blue-500/10 border-blue-500/25 text-blue-700 dark:text-blue-400' },
    unknown:            { label: 'Status Unknown',              icon: HelpCircle,     cls: 'bg-gray-400/10 border-gray-400/25 text-gray-600 dark:text-gray-400' },
  };
  return map[s] || map.unknown;
});

function formatWindow(m) {
  const fmt = (iso) => new Date(iso).toLocaleString([], { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  return `${fmt(m.starts_at)} → ${fmt(m.ends_at)}`;
}

function isActive(m) {
  const now = new Date();
  return new Date(m.starts_at) <= now && new Date(m.ends_at) >= now;
}

// ── Incident timeline helpers ─────────────────────────────────────────────────

function localDayKey(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function dayLabel(key) {
  const today     = localDayKey(new Date());
  const yesterday = localDayKey(new Date(Date.now() - 86_400_000));
  if (key === today)     return 'Today';
  if (key === yesterday) return 'Yesterday';
  return new Date(key + 'T12:00:00').toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' });
}

function incidentStatus(inc) {
  if (inc.resolved_at) return 'resolved';
  if (inc.updates?.length) return inc.updates[inc.updates.length - 1].status;
  return 'investigating';
}

const VIEW_LABELS = { last_hour: 'Last Hour', today: 'Today', week: 'Last 7 Days', month: 'Last 30 Days' };

function metricViewLabel(m) {
  if (m.metric_type === 'last') return 'Latest value';
  return VIEW_LABELS[m.default_view] ?? m.default_view;
}

function fmtMetric(m) {
  if (m.current_value == null) return '—';
  const val = Number(m.current_value).toFixed(m.places);
  return m.suffix ? `${val} ${m.suffix}` : val;
}

// All N calendar days newest-first, each with its list of incidents (may be empty)
const timelineDays = computed(() => {
  const n   = data.value?.incident_timeline_days ?? 7;
  const map = new Map();
  for (const inc of [...incidents.value.open, ...incidents.value.resolved]) {
    const k = localDayKey(new Date(inc.created_at));
    if (!map.has(k)) map.set(k, []);
    map.get(k).push(inc);
  }
  const days = [];
  for (let i = 0; i < n; i++) {
    const d   = new Date();
    d.setDate(d.getDate() - i);
    const key = localDayKey(d);
    days.push({ key, label: dayLabel(key), incidents: map.get(key) ?? [] });
  }
  return days;
});

onMounted(() => { fetchAll(); interval = setInterval(fetchAll, 60_000); });
onUnmounted(() => clearInterval(interval));
</script>

<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-950 transition-colors">
    <div class="mx-auto px-4 py-10" :class="isWide ? 'max-w-6xl' : 'max-w-4xl'">

      <!-- Header -->
      <div class="mb-8 flex items-start justify-between">
        <div class="flex items-center gap-3">
          <div class="p-2 rounded-lg bg-gray-100 dark:bg-gray-800">
            <Server class="w-5 h-5 text-gray-500 dark:text-gray-400" :stroke-width="1.75" />
          </div>
          <div>
            <h1 class="text-xl font-bold text-gray-900 dark:text-white">{{ data?.site_title ?? 'MOSSBoard' }}</h1>
            <p class="text-gray-400 dark:text-gray-600 text-xs mt-0.5">Auto-refreshes every 60 s</p>
          </div>
        </div>
        <ThemeToggle />
      </div>

      <!-- Overall banner -->
      <div v-if="data" class="mb-6 px-5 py-4 rounded-lg border flex items-center gap-3 text-sm font-medium" :class="bannerCfg.cls">
        <component :is="bannerCfg.icon" class="w-5 h-5 shrink-0" :stroke-width="1.75" />
        {{ bannerCfg.label }}
      </div>

      <!-- Upcoming maintenance -->
      <div v-if="maintenance.length" class="mb-6 bg-blue-500/5 border border-blue-500/20 rounded-lg overflow-hidden">
        <div class="px-4 py-2.5 border-b border-blue-500/15 flex items-center gap-2">
          <Calendar class="w-4 h-4 text-blue-500" :stroke-width="1.75" />
          <span class="text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wider">Scheduled Maintenance</span>
        </div>
        <div v-for="m in maintenance" :key="m.id" class="px-4 py-3 border-b border-blue-500/10 last:border-0">
          <div class="flex items-start gap-2">
            <span v-if="isActive(m)" class="text-xs px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-600 dark:text-blue-300 border border-blue-500/30 shrink-0 mt-0.5">Active</span>
            <div>
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-sm text-gray-800 dark:text-gray-200 font-medium">{{ m.title }}</span>
                <template v-if="m.services && m.services.length">
                  <span v-for="svc in m.services" :key="svc.id" class="text-xs text-gray-400 dark:text-gray-500">
                    <template v-if="svc.section_name">{{ svc.section_name }} › </template>{{ svc.name }}
                  </span>
                </template>
              </div>
              <div class="text-xs text-gray-500 mt-0.5">{{ formatWindow(m) }}</div>
              <div v-if="m.description" class="text-xs text-gray-400 dark:text-gray-600 mt-0.5">{{ m.description }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Error -->
      <div v-if="error" class="mb-6 px-4 py-3 bg-red-500/10 border border-red-500/30 rounded text-red-600 dark:text-red-400 text-sm flex items-center gap-2">
        <XCircle class="w-4 h-4 shrink-0" :stroke-width="1.75" />
        {{ error }}
      </div>

      <!-- Sections -->
      <div v-if="data" class="space-y-4">
        <SectionCard v-for="section in data.sections" :key="section.id" :section="section" />
      </div>
      <div v-else-if="!error" class="space-y-4">
        <div v-for="i in 3" :key="i" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg h-32 animate-pulse" />
      </div>

      <!-- Metrics -->
      <div v-if="metrics.length" class="mt-6 space-y-3">
        <div
          v-for="m in metrics" :key="m.id"
          class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl shadow-sm dark:shadow-none overflow-hidden"
        >
          <!-- Header row -->
          <div class="px-5 pt-4 pb-3 flex items-start justify-between gap-4">
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <span class="text-sm font-semibold text-gray-900 dark:text-white">{{ m.name }}</span>
                <span class="text-xs text-gray-400 dark:text-gray-500">{{ m.service_name }}</span>
              </div>
              <p v-if="m.description" class="text-xs text-gray-400 dark:text-gray-600 mt-0.5 truncate">{{ m.description }}</p>
            </div>
            <div class="text-right shrink-0">
              <div class="text-2xl font-bold text-gray-900 dark:text-white tabular-nums leading-tight">{{ fmtMetric(m) }}</div>
              <div class="text-xs text-gray-400 dark:text-gray-600 mt-0.5">{{ metricViewLabel(m) }}</div>
            </div>
          </div>
          <!-- Sparkline -->
          <MetricChart
            v-if="m.display_chart"
            :points="metricPts[m.id] ?? []"
            :height="64"
            class="px-0"
          />
        </div>
      </div>

      <!-- Incident timeline -->
      <div v-if="data?.show_incident_timeline" class="mt-10">

        <!-- Section header -->
        <div class="flex items-center gap-2 mb-5">
          <AlertCircle class="w-4 h-4 text-gray-400 dark:text-gray-500" :stroke-width="1.75" />
          <h2 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
            Incident history · last {{ incidents.days }} day{{ incidents.days !== 1 ? 's' : '' }}
          </h2>
        </div>

        <!-- Day rows -->
        <div class="relative">
          <!-- Vertical guide line -->
          <div class="absolute left-[5px] top-2 bottom-2 w-px bg-gray-200 dark:bg-gray-800" />

          <div v-for="day in timelineDays" :key="day.key" class="mb-6 pl-7 relative">

            <!-- Day dot -->
            <div class="absolute left-0 top-1 w-[11px] h-[11px] rounded-full border-2 border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-950" />

            <!-- Day label -->
            <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2">{{ day.label }}</div>

            <!-- Incidents -->
            <div v-if="day.incidents.length" class="space-y-1.5">
              <a
                v-for="inc in day.incidents" :key="inc.id"
                :href="inc.service_slug ? '/services/' + inc.service_slug : '#'"
                class="flex items-center gap-3 px-3 py-2 rounded-lg bg-white dark:bg-gray-900 border transition-colors group"
                :class="inc.resolved_at
                  ? 'border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700'
                  : 'border-orange-400/40 hover:border-orange-400/60'"
              >
                <!-- Status dot -->
                <span
                  class="w-2 h-2 rounded-full shrink-0"
                  :class="{
                    'bg-yellow-400': incidentStatus(inc) === 'investigating',
                    'bg-orange-500': incidentStatus(inc) === 'identified',
                    'bg-blue-500':   incidentStatus(inc) === 'monitoring',
                    'bg-green-500':  incidentStatus(inc) === 'resolved',
                  }"
                />

                <!-- Title -->
                <span class="text-sm text-gray-800 dark:text-gray-200 font-medium truncate flex-1 min-w-0">{{ inc.title }}</span>

                <!-- Breadcrumb -->
                <span class="text-xs text-gray-400 dark:text-gray-500 shrink-0 hidden sm:block">
                  <template v-if="inc.section_name">{{ inc.section_name }} › </template>{{ inc.service_name }}
                </span>

                <!-- Status badge -->
                <StatusBadge :status="incidentStatus(inc)" class="shrink-0" />

                <!-- Arrow -->
                <ArrowRight class="w-3.5 h-3.5 text-gray-300 dark:text-gray-700 group-hover:text-gray-400 dark:group-hover:text-gray-500 shrink-0 transition-colors" :stroke-width="1.75" />
              </a>
            </div>

            <!-- Empty day -->
            <p v-else class="text-xs text-gray-400 dark:text-gray-600 italic">No incidents on this day</p>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="mt-10 flex items-center justify-between text-xs text-gray-400 dark:text-gray-600">
        <span>MOSSBoard by Maximilian Thoma 2026</span>
        <div class="flex items-center gap-4">
          <a href="/monitor" class="inline-flex items-center gap-1.5 hover:text-gray-600 dark:hover:text-gray-400 transition-colors">
            <Monitor class="w-3 h-3" :stroke-width="1.75" /> Monitor
          </a>
          <a href="/admin" class="inline-flex items-center gap-1.5 hover:text-gray-600 dark:hover:text-gray-400 transition-colors">
            <Key class="w-3 h-3" :stroke-width="1.75" /> Admin
          </a>
        </div>
      </div>
    </div>
  </div>
</template>
