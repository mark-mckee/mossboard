<script setup>
import { ref, computed, onMounted } from 'vue';
import { Plus, Pencil, Trash2, BarChart2, ChevronDown, ChevronUp, Copy, Check } from 'lucide-vue-next';

// ── state ─────────────────────────────────────────────────────────────────────
const metrics  = ref([]);
const services = ref([]);
const loading  = ref(true);
const showForm = ref(false);
const editing  = ref(null);   // metric id being edited, or null for create
const copied   = ref(null);   // id of metric whose endpoint was just copied

const EMPTY = () => ({
  service_id:    '',
  name:          '',
  suffix:        '',
  description:   '',
  default_view:  'last_hour',
  default_value: 0,
  display_chart: true,
  places:        0,
  metric_type:   'average',
  threshold:     0,
  visible:       true,
});
const form = ref(EMPTY());

// ── options ───────────────────────────────────────────────────────────────────
const VIEW_OPTS = [
  { value: 'last_hour', label: 'Last Hour'    },
  { value: 'today',     label: 'Today'        },
  { value: 'week',      label: 'Last 7 Days'  },
  { value: 'month',     label: 'Last 30 Days' },
];
const TYPE_OPTS = [
  { value: 'average', label: 'Average',    desc: 'Mean of all points in the window'    },
  { value: 'sum',     label: 'Sum',        desc: 'Total of all points in the window'   },
  { value: 'last',    label: 'Last Value', desc: 'Most recent point, ignoring window'  },
];

// ── computed ──────────────────────────────────────────────────────────────────
const serviceOptions = computed(() => services.value.map(s => ({ value: s.id, label: s.name })));

function pushUrl(metric) {
  return `POST /api/v1/metrics/${metric.id}/points`;
}

function typeLabel(m) {
  if (m.metric_type === 'last') return 'Last Value';
  const view = VIEW_OPTS.find(o => o.value === m.default_view)?.label ?? m.default_view;
  return `${m.metric_type === 'sum' ? 'Sum' : 'Avg'} · ${view}`;
}

function fmtValue(metric) {
  if (metric.current_value == null) return '—';
  const val = Number(metric.current_value).toFixed(metric.places);
  return metric.suffix ? `${val} ${metric.suffix}` : val;
}

// ── data fetching ─────────────────────────────────────────────────────────────
async function fetchAll() {
  loading.value = true;
  const [mRes, sRes] = await Promise.all([
    fetch('/api/v1/admin/metrics'),
    fetch('/api/v1/admin/services'),
  ]);
  if (mRes.ok) metrics.value  = (await mRes.json()).metrics;
  if (sRes.ok) services.value = (await sRes.json()).services;
  loading.value = false;
}

// ── form ──────────────────────────────────────────────────────────────────────
function openCreate() {
  editing.value = null;
  form.value    = EMPTY();
  showForm.value = true;
}

function openEdit(m) {
  editing.value = m.id;
  form.value = {
    service_id:    m.service_id   ?? '',
    name:          m.name,
    suffix:        m.suffix,
    description:   m.description,
    default_view:  m.default_view,
    default_value: m.default_value,
    display_chart: m.display_chart,
    places:        m.places,
    metric_type:   m.metric_type,
    threshold:     m.threshold,
    visible:       m.visible,
  };
  showForm.value = true;
}

function cancelForm() {
  showForm.value = false;
  editing.value  = null;
}

async function submitForm() {
  const body = { ...form.value };
  const url    = editing.value ? `/api/v1/admin/metrics/${editing.value}` : '/api/v1/admin/metrics';
  const method = editing.value ? 'PATCH' : 'POST';
  const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  if (res.ok) { cancelForm(); await fetchAll(); }
}

async function deleteMetric(id) {
  if (!confirm('Delete this metric and all its data points?')) return;
  await fetch(`/api/v1/admin/metrics/${id}`, { method: 'DELETE' });
  await fetchAll();
}

async function copyEndpoint(metric) {
  await navigator.clipboard.writeText(`POST /api/v1/metrics/${metric.id}/points`);
  copied.value = metric.id;
  setTimeout(() => { copied.value = null; }, 2000);
}

onMounted(fetchAll);
</script>

<template>
  <div class="p-8">

    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-lg font-bold text-gray-900 dark:text-white">Metrics</h1>
        <p class="text-xs text-gray-400 dark:text-gray-600 mt-0.5">Time-series metrics pushed via API token</p>
      </div>
      <button @click="openCreate"
        class="flex items-center gap-1.5 bg-gray-800 hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 text-white text-xs px-3 py-1.5 rounded-lg transition-colors">
        <Plus class="w-3.5 h-3.5" :stroke-width="2" /> New Metric
      </button>
    </div>

    <!-- Create / Edit form -->
    <div v-if="showForm" class="mb-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5 shadow-sm dark:shadow-none">
      <h2 class="text-sm font-semibold text-gray-900 dark:text-white mb-4">{{ editing ? 'Edit Metric' : 'New Metric' }}</h2>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">

        <!-- Service -->
        <div class="sm:col-span-2">
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">Service</label>
          <select v-model="form.service_id"
            class="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 transition-colors">
            <option value="" disabled>Select a service…</option>
            <option v-for="s in serviceOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>

        <!-- Name -->
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">Name</label>
          <input v-model="form.name" type="text" placeholder="Users Online"
            class="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 transition-colors" />
        </div>

        <!-- Suffix -->
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">Suffix</label>
          <input v-model="form.suffix" type="text" placeholder="users"
            class="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 transition-colors" />
        </div>

        <!-- Description -->
        <div class="sm:col-span-2">
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">Description</label>
          <input v-model="form.description" type="text" placeholder="The number of users currently online"
            class="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 transition-colors" />
        </div>

        <!-- Default View (not relevant for "last" type) -->
        <div v-if="form.metric_type !== 'last'">
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">Default View</label>
          <select v-model="form.default_view"
            class="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 transition-colors">
            <option v-for="o in VIEW_OPTS" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
        </div>

        <!-- Default Value -->
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">Default Value</label>
          <input v-model.number="form.default_value" type="number" step="any"
            class="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 transition-colors" />
        </div>

        <!-- Metric Type -->
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Metric Type</label>
          <div class="flex gap-2">
            <label v-for="o in TYPE_OPTS" :key="o.value"
              class="flex-1 flex items-start gap-2 p-2.5 rounded-lg border cursor-pointer transition-colors"
              :class="form.metric_type === o.value
                ? 'border-gray-400 dark:border-gray-500 bg-gray-50 dark:bg-gray-800'
                : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800/50'">
              <input type="radio" :value="o.value" v-model="form.metric_type" class="mt-0.5 accent-gray-700 dark:accent-gray-400 shrink-0" />
              <div>
                <div class="text-xs font-medium text-gray-800 dark:text-gray-200">{{ o.label }}</div>
                <div class="text-xs text-gray-400 dark:text-gray-600 mt-0.5">{{ o.desc }}</div>
              </div>
            </label>
          </div>
        </div>

        <!-- Places -->
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">Decimal Places</label>
          <input v-model.number="form.places" type="number" min="0" max="10"
            class="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 transition-colors" />
        </div>

        <!-- Threshold -->
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">Threshold (seconds)</label>
          <input v-model.number="form.threshold" type="number" min="0"
            placeholder="0 = always create new point"
            class="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 transition-colors" />
          <p class="text-xs text-gray-400 dark:text-gray-600 mt-1">Points within this window are merged instead of stacked.</p>
        </div>

        <!-- Toggles row -->
        <div class="sm:col-span-2 flex flex-wrap gap-6">
          <!-- Display Chart -->
          <label class="flex items-center gap-2.5 cursor-pointer">
            <div class="relative">
              <input type="checkbox" v-model="form.display_chart" class="sr-only peer" />
              <div class="w-9 h-5 bg-gray-200 dark:bg-gray-700 peer-checked:bg-gray-700 dark:peer-checked:bg-gray-400 rounded-full transition-colors
                          after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:w-4 after:h-4
                          after:rounded-full after:bg-white after:transition-transform peer-checked:after:translate-x-4" />
            </div>
            <span class="text-sm text-gray-700 dark:text-gray-300">Display Chart</span>
          </label>
          <!-- Visible -->
          <label class="flex items-center gap-2.5 cursor-pointer">
            <div class="relative">
              <input type="checkbox" v-model="form.visible" class="sr-only peer" />
              <div class="w-9 h-5 bg-gray-200 dark:bg-gray-700 peer-checked:bg-gray-700 dark:peer-checked:bg-gray-400 rounded-full transition-colors
                          after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:w-4 after:h-4
                          after:rounded-full after:bg-white after:transition-transform peer-checked:after:translate-x-4" />
            </div>
            <span class="text-sm text-gray-700 dark:text-gray-300">Visible on status page</span>
          </label>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex items-center gap-3 mt-5 pt-4 border-t border-gray-100 dark:border-gray-800">
        <button @click="submitForm"
          class="bg-gray-800 hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 text-white text-xs px-4 py-1.5 rounded-lg transition-colors">
          {{ editing ? 'Save Changes' : 'Create Metric' }}
        </button>
        <button @click="cancelForm"
          class="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition-colors">
          Cancel
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl h-16 animate-pulse" />
    </div>

    <!-- Empty -->
    <div v-else-if="!metrics.length && !showForm"
      class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-10 text-center">
      <BarChart2 class="w-8 h-8 text-gray-300 dark:text-gray-700 mx-auto mb-3" :stroke-width="1.5" />
      <p class="text-sm text-gray-400 dark:text-gray-600">No metrics yet. Create one to start collecting data.</p>
    </div>

    <!-- List -->
    <div v-else-if="!loading" class="space-y-2">
      <div v-for="m in metrics" :key="m.id"
        class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl shadow-sm dark:shadow-none overflow-hidden">

        <!-- Row -->
        <div class="px-4 py-3 flex items-center gap-4">
          <!-- Icon -->
          <div class="p-1.5 rounded-lg bg-indigo-500/10 shrink-0">
            <BarChart2 class="w-4 h-4 text-indigo-500" :stroke-width="1.75" />
          </div>

          <!-- Name + meta -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <span class="text-sm font-medium text-gray-900 dark:text-white truncate">{{ m.name }}</span>
              <span v-if="!m.visible" class="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500">Hidden</span>
            </div>
            <div class="text-xs text-gray-400 dark:text-gray-600 mt-0.5 truncate">
              {{ m.service_name }} · {{ typeLabel(m) }}
            </div>
          </div>

          <!-- Current value -->
          <div class="text-right shrink-0">
            <div class="text-base font-semibold text-gray-900 dark:text-white tabular-nums">{{ fmtValue(m) }}</div>
            <div class="text-xs text-gray-400 dark:text-gray-600">current</div>
          </div>

          <!-- Push endpoint copy -->
          <button @click="copyEndpoint(m)" title="Copy push endpoint"
            class="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors shrink-0">
            <component :is="copied === m.id ? Check : Copy" class="w-3.5 h-3.5" :class="copied === m.id ? 'text-green-500' : ''" :stroke-width="1.75" />
          </button>

          <!-- Edit -->
          <button @click="openEdit(m)"
            class="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors shrink-0">
            <Pencil class="w-3.5 h-3.5" :stroke-width="1.75" />
          </button>

          <!-- Delete -->
          <button @click="deleteMetric(m.id)"
            class="p-1.5 rounded-lg text-gray-400 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/5 transition-colors shrink-0">
            <Trash2 class="w-3.5 h-3.5" :stroke-width="1.75" />
          </button>
        </div>

        <!-- Push endpoint hint -->
        <div class="px-4 pb-3 flex items-center gap-2">
          <code class="text-xs text-gray-400 dark:text-gray-600 font-mono bg-gray-50 dark:bg-gray-800 px-2 py-0.5 rounded">
            POST /api/v1/metrics/{{ m.id }}/points
          </code>
          <span class="text-xs text-gray-400 dark:text-gray-600">· Bearer token · body: <code class="font-mono">{"value": 42}</code></span>
        </div>
      </div>
    </div>
  </div>
</template>
