<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { CheckCircle, Clock, AlertTriangle, XCircle, Wrench, HelpCircle, Calendar, Server, Key, Monitor } from 'lucide-vue-next';
import SectionCard from '../components/SectionCard.vue';
import ThemeToggle from '../components/ThemeToggle.vue';

const data = ref(null);
const maintenance = ref([]);
const error = ref(null);
let interval = null;

async function fetchAll() {
  try {
    const [sRes, mRes] = await Promise.all([fetch('/api/v1/status'), fetch('/api/v1/maintenance')]);
    if (!sRes.ok) throw new Error('Failed to fetch status');
    data.value = await sRes.json();
    if (mRes.ok) maintenance.value = (await mRes.json()).maintenance;
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

onMounted(() => { fetchAll(); interval = setInterval(fetchAll, 60_000); });
onUnmounted(() => clearInterval(interval));
</script>

<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-950 transition-colors">
    <div class="max-w-4xl mx-auto px-4 py-10">

      <!-- Header -->
      <div class="mb-8 flex items-start justify-between">
        <div class="flex items-center gap-3">
          <div class="p-2 rounded-lg bg-gray-100 dark:bg-gray-800">
            <Server class="w-5 h-5 text-gray-500 dark:text-gray-400" :stroke-width="1.75" />
          </div>
          <div>
            <h1 class="text-xl font-bold text-gray-900 dark:text-white">System Status</h1>
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
              <div class="flex items-center gap-2">
                <span class="text-sm text-gray-800 dark:text-gray-200 font-medium">{{ m.title }}</span>
                <span class="text-xs text-gray-400 dark:text-gray-500">
                  <template v-if="m.section_name">{{ m.section_name }} › </template>{{ m.service_name }}
                </span>
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

      <!-- Footer -->
      <div class="mt-10 flex items-center justify-between text-xs text-gray-400 dark:text-gray-600">
        <span>© 2026 Maximilian Thoma</span>
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
