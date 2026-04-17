<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { CheckCircle, Clock, AlertTriangle, XCircle, Wrench, HelpCircle, Calendar, Maximize, Minimize, ChevronDown, ChevronRight } from 'lucide-vue-next';

const data        = ref(null);
const maintenance = ref([]);
const now         = ref(new Date());
let dataInterval  = null;
let clockInterval = null;

async function fetchAll() {
  const [sRes, mRes] = await Promise.all([fetch('/api/v1/status'), fetch('/api/v1/maintenance')]);
  if (sRes.ok) data.value        = await sRes.json();
  if (mRes.ok) maintenance.value = (await mRes.json()).maintenance;
}

onMounted(() => {
  fetchAll();
  dataInterval  = setInterval(fetchAll, 30_000);
  clockInterval = setInterval(() => { now.value = new Date(); }, 1000);
});
onUnmounted(() => { clearInterval(dataInterval); clearInterval(clockInterval); });

const timeStr = computed(() => now.value.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
const dateStr = computed(() => now.value.toLocaleDateString([], { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }));

const STATUS_META = {
  operational:        { label: 'Operational',    icon: CheckCircle,   dot: 'bg-green-500',  text: 'text-green-400',  badge: 'bg-green-500/15 border-green-500/30 text-green-400'   },
  performance_issues: { label: 'Perf. Issues',   icon: Clock,         dot: 'bg-yellow-400', text: 'text-yellow-300', badge: 'bg-yellow-400/15 border-yellow-400/30 text-yellow-300' },
  partial_outage:     { label: 'Partial Outage', icon: AlertTriangle, dot: 'bg-orange-500', text: 'text-orange-400', badge: 'bg-orange-500/15 border-orange-500/30 text-orange-400' },
  major_outage:       { label: 'Major Outage',   icon: XCircle,       dot: 'bg-red-500',    text: 'text-red-400',    badge: 'bg-red-500/15 border-red-500/30 text-red-400'          },
  under_maintenance:  { label: 'Maintenance',    icon: Wrench,        dot: 'bg-blue-500',   text: 'text-blue-400',   badge: 'bg-blue-500/15 border-blue-500/30 text-blue-400'       },
  unknown:            { label: 'Unknown',        icon: HelpCircle,    dot: 'bg-gray-500',   text: 'text-gray-400',   badge: 'bg-gray-500/15 border-gray-500/30 text-gray-400'       },
};

function meta(status) { return STATUS_META[status] || STATUS_META.unknown; }

const OVERALL_BANNER = {
  operational:        { label: 'All Systems Operational',     cls: 'bg-green-500/10 border-green-500/20 text-green-400'   },
  performance_issues: { label: 'Performance Issues Detected', cls: 'bg-yellow-400/10 border-yellow-400/20 text-yellow-300' },
  partial_outage:     { label: 'Partial System Outage',       cls: 'bg-orange-500/10 border-orange-500/20 text-orange-400' },
  major_outage:       { label: 'Major System Outage',         cls: 'bg-red-500/10 border-red-500/20 text-red-400'         },
  under_maintenance:  { label: 'Under Maintenance',           cls: 'bg-blue-500/10 border-blue-500/20 text-blue-400'      },
  unknown:            { label: 'Status Unknown',              cls: 'bg-gray-500/10 border-gray-500/20 text-gray-400'      },
};

const overallBanner = computed(() => {
  const s = data.value?.overall_status;
  return OVERALL_BANNER[s] || OVERALL_BANNER.unknown;
});

const activeMaintenance = computed(() => maintenance.value.filter(m => {
  const n = new Date();
  return new Date(m.starts_at) <= n && new Date(m.ends_at) >= n;
}));

// Whether a section is fully operational
function sectionAllOk(section) {
  return section.services.every(s => s.status === 'operational');
}

// Worst status of a section (for collapsed header badge)
function sectionWorstStatus(section) {
  const priority = { major_outage: 6, partial_outage: 5, performance_issues: 4, under_maintenance: 3, unknown: 2, operational: 1 };
  return section.services.reduce((worst, s) => {
    return (priority[s.status] || 0) > (priority[worst] || 0) ? s.status : worst;
  }, 'operational');
}

// Sections expand automatically when not all operational; user can also toggle manually
const manualOverrides = ref({}); // { [section_id]: true (forced open) | false (forced closed) }

function isExpanded(section) {
  if (section.id in manualOverrides.value) return manualOverrides.value[section.id];
  return !sectionAllOk(section);
}

function toggleSection(section) {
  const current = isExpanded(section);
  manualOverrides.value = { ...manualOverrides.value, [section.id]: !current };
}

// Reset manual overrides on data refresh so auto-expand stays reactive
// but only for sections whose state changed
function syncOverrides(newSections) {
  if (!newSections) return;
  const updated = { ...manualOverrides.value };
  for (const s of newSections) {
    // If the section is now in distress and was manually collapsed, reopen it
    if (!sectionAllOk(s) && updated[s.id] === false) {
      delete updated[s.id];
    }
    // If it's back to all-ok and was manually opened, let it auto-collapse
    if (sectionAllOk(s) && updated[s.id] === true) {
      delete updated[s.id];
    }
  }
  manualOverrides.value = updated;
}

// Watch for data changes to sync overrides
import { watch } from 'vue';
watch(() => data.value?.sections, (sections) => syncOverrides(sections));

// Fullscreen toggle
const isFullscreen = ref(false);
function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen();
    isFullscreen.value = true;
  } else {
    document.exitFullscreen();
    isFullscreen.value = false;
  }
}
document.addEventListener('fullscreenchange', () => {
  isFullscreen.value = !!document.fullscreenElement;
});
</script>

<template>
  <div class="min-h-screen bg-gray-950 text-white flex flex-col" style="font-family: 'JetBrains Mono', monospace;">

    <!-- Top bar -->
    <header class="flex items-center justify-between px-8 py-4 border-b border-gray-800 shrink-0">
      <div class="flex items-center gap-4">
        <h1 class="text-lg font-bold text-white tracking-wide">{{ data?.site_title ?? 'MOSSBoard' }}</h1>
        <div v-if="data" class="flex items-center gap-2 px-3 py-1 rounded-lg border text-xs font-semibold" :class="overallBanner.cls">
          <component :is="meta(data.overall_status).icon" class="w-3.5 h-3.5" :stroke-width="2" />
          {{ overallBanner.label }}
        </div>
      </div>
      <div class="flex items-center gap-6">
        <div class="text-right">
          <div class="text-2xl font-bold text-white tabular-nums tracking-widest">{{ timeStr }}</div>
          <div class="text-xs text-gray-500 mt-0.5">{{ dateStr }}</div>
        </div>
        <button @click="toggleFullscreen" class="p-2 rounded-lg text-gray-500 hover:text-gray-300 hover:bg-gray-800 transition-colors">
          <Maximize v-if="!isFullscreen" class="w-5 h-5" :stroke-width="1.75" />
          <Minimize v-else class="w-5 h-5" :stroke-width="1.75" />
        </button>
      </div>
    </header>

    <!-- Active maintenance banner -->
    <div v-if="activeMaintenance.length" class="px-8 py-2.5 bg-blue-500/10 border-b border-blue-500/20 flex items-center gap-3">
      <Calendar class="w-4 h-4 text-blue-400 shrink-0" :stroke-width="1.75" />
      <span class="text-xs text-blue-400 font-semibold uppercase tracking-wider mr-2">Active Maintenance</span>
      <span v-for="m in activeMaintenance" :key="m.id" class="text-xs text-blue-300 mr-4">
        {{ m.title }}
        <template v-if="m.services && m.services.length">
          <span v-for="svc in m.services" :key="svc.id" class="text-blue-500 ml-1">
            <template v-if="svc.section_name">{{ svc.section_name }} › </template>{{ svc.name }}
          </span>
        </template>
      </span>
    </div>

    <!-- Main content -->
    <main class="flex-1 px-8 py-6 overflow-auto">
      <div v-if="data" class="space-y-3">
        <div
          v-for="section in data.sections" :key="section.id"
          class="rounded-xl border overflow-hidden transition-colors"
          :class="sectionAllOk(section)
            ? 'border-gray-800 bg-gray-900/60'
            : 'border-gray-700 bg-gray-900'"
        >
          <!-- Section header — always visible, clickable to toggle -->
          <button
            @click="toggleSection(section)"
            class="w-full flex items-center justify-between px-5 py-3.5 text-left transition-colors hover:bg-gray-800/40"
          >
            <div class="flex items-center gap-3 min-w-0">
              <!-- Chevron -->
              <ChevronDown v-if="isExpanded(section)" class="w-4 h-4 text-gray-500 shrink-0 transition-transform" :stroke-width="1.75" />
              <ChevronRight v-else class="w-4 h-4 text-gray-500 shrink-0 transition-transform" :stroke-width="1.75" />

              <!-- Section name -->
              <span class="text-sm font-semibold text-gray-200 tracking-wide">{{ section.name }}</span>

              <!-- When collapsed: worst-status badge + service count -->
              <template v-if="!isExpanded(section)">
                <span class="text-xs px-2 py-0.5 rounded-full border font-medium" :class="meta(sectionWorstStatus(section)).badge">
                  {{ meta(sectionWorstStatus(section)).label }}
                </span>
                <span class="text-xs text-gray-600">{{ section.services.length }} service{{ section.services.length !== 1 ? 's' : '' }}</span>
              </template>
            </div>

            <!-- When collapsed and all OK: green pill on the right -->
            <div v-if="sectionAllOk(section) && !isExpanded(section)" class="flex items-center gap-2 shrink-0 ml-4">
              <div class="flex items-center gap-1.5 text-xs text-green-400">
                <div class="w-2 h-2 rounded-full bg-green-500" />
                {{ section.services.length }} / {{ section.services.length }} operational
              </div>
            </div>

            <!-- When expanded and all OK: subtle count -->
            <div v-if="sectionAllOk(section) && isExpanded(section)" class="text-xs text-gray-600 shrink-0 ml-4">
              {{ section.services.length }} service{{ section.services.length !== 1 ? 's' : '' }}
            </div>

            <!-- When expanded and NOT all OK: summary of affected services -->
            <div v-if="!sectionAllOk(section) && isExpanded(section)" class="flex items-center gap-2 shrink-0 ml-4">
              <span class="text-xs text-gray-500">
                {{ section.services.filter(s => s.status !== 'operational').length }} affected
              </span>
            </div>
          </button>

          <!-- Collapsed all-ok: compact single-row summary -->
          <div v-if="!isExpanded(section) && sectionAllOk(section)"
            class="px-5 pb-3.5 flex flex-wrap gap-2">
            <div
              v-for="service in section.services" :key="service.id"
              class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-green-500/5 border border-green-500/15 text-xs text-green-500/70"
            >
              <div class="w-1.5 h-1.5 rounded-full bg-green-500 opacity-60" />
              {{ service.name }}
            </div>
          </div>

          <!-- Collapsed not-all-ok: show only affected services as compact pills -->
          <div v-if="!isExpanded(section) && !sectionAllOk(section)"
            class="px-5 pb-3.5 flex flex-wrap gap-2">
            <div
              v-for="service in section.services.filter(s => s.status !== 'operational')" :key="service.id"
              class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-medium"
              :class="meta(service.status).badge"
            >
              <div class="w-1.5 h-1.5 rounded-full" :class="meta(service.status).dot" />
              {{ service.name }}
              <span class="opacity-60">· {{ meta(service.status).label }}</span>
            </div>
            <div
              v-if="section.services.filter(s => s.status === 'operational').length > 0"
              class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-green-500/5 border border-green-500/15 text-xs text-green-500/60"
            >
              <div class="w-1.5 h-1.5 rounded-full bg-green-500 opacity-60" />
              +{{ section.services.filter(s => s.status === 'operational').length }} operational
            </div>
          </div>

          <!-- Expanded: full service cards grid -->
          <div v-if="isExpanded(section)" class="px-5 pb-5">
            <div class="grid gap-3" style="grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));">
              <div
                v-for="service in section.services" :key="service.id"
                class="flex items-center gap-4 px-4 py-3.5 rounded-xl border bg-gray-950/60"
                :class="{
                  'border-green-500/20':  service.status === 'operational',
                  'border-yellow-400/25': service.status === 'performance_issues',
                  'border-orange-500/25': service.status === 'partial_outage',
                  'border-red-500/30':    service.status === 'major_outage',
                  'border-blue-500/20':   service.status === 'under_maintenance',
                  'border-gray-700':      service.status === 'unknown',
                }"
              >
                <!-- Status dot with pulse for non-operational -->
                <div class="relative shrink-0">
                  <div class="w-2.5 h-2.5 rounded-full" :class="meta(service.status).dot" />
                  <div
                    v-if="service.status !== 'operational' && service.status !== 'unknown'"
                    class="absolute inset-0 w-2.5 h-2.5 rounded-full animate-ping opacity-60"
                    :class="meta(service.status).dot"
                  />
                </div>
                <!-- Name + status label -->
                <div class="flex-1 min-w-0">
                  <div class="text-sm font-medium text-white truncate">{{ service.name }}</div>
                  <div class="text-xs mt-0.5" :class="meta(service.status).text">{{ meta(service.status).label }}</div>
                </div>
                <!-- Icon -->
                <component :is="meta(service.status).icon" class="w-4 h-4 shrink-0 opacity-40" :class="meta(service.status).text" :stroke-width="1.5" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Loading skeleton -->
      <div v-else class="space-y-3">
        <div v-for="i in 4" :key="i" class="h-14 rounded-xl bg-gray-900 animate-pulse border border-gray-800" />
      </div>
    </main>

    <!-- Footer -->
    <footer class="px-8 py-3 border-t border-gray-800 flex items-center justify-between shrink-0">
      <span class="text-xs text-gray-600">MOSSBoard by Maximilian Thoma 2026</span>
      <div class="flex items-center gap-1.5 text-xs text-gray-700">
        <div class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
        Refreshes every 30 s
      </div>
      <a href="/monitor" class="text-xs text-gray-700 hover:text-gray-500 transition-colors">← Monitor</a>
    </footer>
  </div>
</template>
