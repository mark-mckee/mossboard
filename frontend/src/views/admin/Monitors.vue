<script setup>
import { ref, computed, onMounted } from 'vue';
import { Activity, Globe, Wifi, Server, Plus, Trash2, Play, CheckCircle, Clock, AlertTriangle, XCircle, Wrench, HelpCircle, Search } from 'lucide-vue-next';
import StatusBadge from '../../components/StatusBadge.vue';

const monitors = ref([]);
const services = ref([]);
const showForm = ref(false);
const editId   = ref(null);
const error    = ref('');
const running  = ref(null); // monitor id currently being triggered manually

const inputCls = 'w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 transition-colors';
const selectCls = inputCls;

const STATUS_CHOICES = [
  { value: 'operational',        label: 'Operational',    icon: CheckCircle,   color: 'border-green-500/40 text-green-600 dark:text-green-400 bg-green-500/10 hover:bg-green-500/20' },
  { value: 'performance_issues', label: 'Perf. Issues',   icon: Clock,         color: 'border-yellow-400/40 text-yellow-600 dark:text-yellow-300 bg-yellow-400/10 hover:bg-yellow-400/20' },
  { value: 'partial_outage',     label: 'Partial Outage', icon: AlertTriangle, color: 'border-orange-500/40 text-orange-600 dark:text-orange-400 bg-orange-500/10 hover:bg-orange-500/20' },
  { value: 'major_outage',       label: 'Major Outage',   icon: XCircle,       color: 'border-red-500/40 text-red-600 dark:text-red-400 bg-red-500/10 hover:bg-red-500/20' },
  { value: 'under_maintenance',  label: 'Maintenance',    icon: Wrench,        color: 'border-blue-500/40 text-blue-600 dark:text-blue-400 bg-blue-500/10 hover:bg-blue-500/20' },
  { value: 'unknown',            label: 'Unknown',        icon: HelpCircle,    color: 'border-gray-400/40 text-gray-600 dark:text-gray-400 bg-gray-400/10 hover:bg-gray-400/20' },
];

const TYPE_INFO = {
  http: { label: 'HTTP',  icon: Globe,   desc: 'HTTP(S) request check' },
  tcp:  { label: 'TCP',   icon: Server,  desc: 'TCP connection check' },
  icmp: { label: 'ICMP',  icon: Wifi,    desc: 'Ping (ICMP echo) check' },
  dns:  { label: 'DNS',   icon: Search,  desc: 'DNS resolution check' },
};

const DNS_RECORD_TYPES = ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'NS', 'PTR'];

function emptyForm() {
  return {
    name: '',
    service_id: services.value[0]?.id || '',
    type: 'http',
    url: '',
    host: '',
    port: null,
    expected_status_codes: [200],
    dns_record_type: 'A',
    dns_server: '',
    dns_expected_values: [],
    failure_status: 'major_outage',
    interval_seconds: 60,
    timeout_seconds: 10,
    confirm_seconds: 0,
    active: true,
    // threshold arrays — each item: { max_ms/max_percent, status }
    response_time_thresholds: [],
    packet_loss_thresholds: [],
  };
}

const form = ref(emptyForm());

// Expected-status-codes as comma-separated string for the input
const expectedCodesStr = computed({
  get() {
    return form.value.expected_status_codes.join(', ');
  },
  set(val) {
    form.value.expected_status_codes = val
      .split(',')
      .map(v => parseInt(v.trim()))
      .filter(n => !isNaN(n));
  },
});

async function fetchAll() {
  const [monRes, svcRes] = await Promise.all([
    fetch('/api/v1/admin/monitors'),
    fetch('/api/v1/admin/services'),
  ]);
  if (monRes.ok) monitors.value = (await monRes.json()).monitors;
  if (svcRes.ok) services.value = (await svcRes.json()).services;
}

function startCreate() {
  editId.value = null;
  form.value = emptyForm();
  form.value.service_id = services.value[0]?.id || '';
  showForm.value = true;
  error.value = '';
}

function startEdit(m) {
  editId.value = m.id;
  form.value = {
    name: m.name,
    service_id: m.service_id,
    type: m.type,
    url: m.url || '',
    host: m.host || '',
    port: m.port || null,
    expected_status_codes: [...(m.expected_status_codes || [200])],
    dns_record_type: m.dns_record_type || 'A',
    dns_server: m.dns_server || '',
    dns_expected_values: [...(m.dns_expected_values || [])],
    failure_status: m.failure_status || 'major_outage',
    interval_seconds: m.interval_seconds,
    timeout_seconds: m.timeout_seconds,
    confirm_seconds: m.confirm_seconds ?? 0,
    active: m.active,
    response_time_thresholds: (m.response_time_thresholds || []).map(t => ({ ...t })),
    packet_loss_thresholds: (m.packet_loss_thresholds || []).map(t => ({ ...t })),
  };
  showForm.value = true;
  error.value = '';
}

function cancelForm() { showForm.value = false; error.value = ''; }

// ── Threshold helpers ─────────────────────────────────────────────────────────
function addRtThreshold() {
  form.value.response_time_thresholds.push({ max_ms: 200, status: 'operational' });
}
function removeRtThreshold(i) {
  form.value.response_time_thresholds.splice(i, 1);
}
function addPlThreshold() {
  form.value.packet_loss_thresholds.push({ max_percent: 0, status: 'operational' });
}
function removePlThreshold(i) {
  form.value.packet_loss_thresholds.splice(i, 1);
}

async function submitForm() {
  error.value = '';
  const payload = {
    name: form.value.name.trim(),
    service_id: form.value.service_id,
    type: form.value.type,
    url: form.value.url,
    host: form.value.host,
    port: form.value.port || null,
    expected_status_codes: form.value.expected_status_codes,
    dns_record_type: form.value.dns_record_type,
    dns_server: form.value.dns_server,
    dns_expected_values: form.value.dns_expected_values.filter(v => v.trim()),
    failure_status: form.value.failure_status,
    interval_seconds: Number(form.value.interval_seconds),
    timeout_seconds: Number(form.value.timeout_seconds),
    confirm_seconds: Number(form.value.confirm_seconds),
    active: form.value.active,
    response_time_thresholds: form.value.response_time_thresholds.map(t => ({
      max_ms: Number(t.max_ms),
      status: t.status,
    })),
    packet_loss_thresholds: form.value.packet_loss_thresholds.map(t => ({
      max_percent: Number(t.max_percent),
      status: t.status,
    })),
  };
  const url    = editId.value ? `/api/v1/admin/monitors/${editId.value}` : '/api/v1/admin/monitors';
  const method = editId.value ? 'PATCH' : 'POST';
  const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  if (res.ok) { showForm.value = false; await fetchAll(); }
  else {
    const body = await res.json().catch(() => ({}));
    error.value = body.message || 'Failed to save.';
  }
}

async function deleteMonitor(id) {
  if (!confirm('Delete this monitor?')) return;
  await fetch(`/api/v1/admin/monitors/${id}`, { method: 'DELETE' });
  await fetchAll();
}

async function triggerRun(id) {
  running.value = id;
  try {
    await fetch(`/api/v1/admin/monitors/${id}/run`, { method: 'POST' });
    // Poll once after 3s so we see an updated result
    setTimeout(async () => { await fetchAll(); running.value = null; }, 3000);
  } catch {
    running.value = null;
  }
}

function formatTs(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString();
}

function statusLabel(val) {
  return STATUS_CHOICES.find(s => s.value === val)?.label || val;
}

onMounted(fetchAll);
</script>

<template>
  <div class="p-8">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-lg font-bold text-gray-900 dark:text-white">Monitors</h1>
        <p class="text-xs text-gray-400 dark:text-gray-600 mt-0.5">Active checks that automatically update service status</p>
      </div>
      <button @click="startCreate"
        class="bg-gray-800 hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 text-white text-xs px-3 py-1.5 rounded-lg transition-colors">
        + New Monitor
      </button>
    </div>

    <!-- ── Form ───────────────────────────────────────────────────────────────── -->
    <div v-if="showForm" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-6 mb-6 shadow-sm dark:shadow-none space-y-5">
      <h2 class="text-sm font-semibold text-gray-900 dark:text-white">{{ editId ? 'Edit Monitor' : 'New Monitor' }}</h2>

      <!-- Name + Service -->
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Name</label>
          <input v-model="form.name" type="text" placeholder="e.g. API Health" :class="inputCls" />
        </div>
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Linked Service</label>
          <select v-model="form.service_id" :class="selectCls">
            <option v-for="svc in services" :key="svc.id" :value="svc.id">
              {{ svc.section_name ? svc.section_name + ' › ' : '' }}{{ svc.name }}
            </option>
          </select>
        </div>
      </div>

      <!-- Type selector -->
      <div>
        <label class="block text-xs text-gray-500 dark:text-gray-400 mb-2">Check Type</label>
        <div class="flex gap-2">
          <button v-for="(info, key) in TYPE_INFO" :key="key" type="button"
            @click="form.type = key"
            class="flex items-center gap-2 px-4 py-2 rounded-lg border text-xs font-medium transition-all"
            :class="form.type === key
              ? 'border-gray-400 dark:border-gray-500 bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
              : 'border-gray-200 dark:border-gray-700 text-gray-400 dark:text-gray-500 hover:border-gray-300 dark:hover:border-gray-600'">
            <component :is="info.icon" :size="13" :stroke-width="1.75" />
            {{ info.label }}
          </button>
        </div>
      </div>

      <!-- Target: HTTP -->
      <div v-if="form.type === 'http'">
        <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">URL</label>
        <input v-model="form.url" type="url" placeholder="https://example.com/health" :class="inputCls" />
      </div>

      <!-- Target: TCP -->
      <div v-if="form.type === 'tcp'" class="grid grid-cols-3 gap-3">
        <div class="col-span-2">
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Host</label>
          <input v-model="form.host" type="text" placeholder="example.com" :class="inputCls" />
        </div>
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Port</label>
          <input v-model.number="form.port" type="number" min="1" max="65535" placeholder="80" :class="inputCls" />
        </div>
      </div>

      <!-- Target: ICMP -->
      <div v-if="form.type === 'icmp'">
        <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Host</label>
        <input v-model="form.host" type="text" placeholder="example.com or 192.168.1.1" :class="inputCls" />
      </div>

      <!-- Target + options: DNS -->
      <template v-if="form.type === 'dns'">
        <div class="grid grid-cols-3 gap-3">
          <div class="col-span-2">
            <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Hostname to resolve</label>
            <input v-model="form.host" type="text" placeholder="example.com" :class="inputCls" />
          </div>
          <div>
            <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Record type</label>
            <select v-model="form.dns_record_type" :class="selectCls">
              <option v-for="rt in DNS_RECORD_TYPES" :key="rt" :value="rt">{{ rt }}</option>
            </select>
          </div>
        </div>
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">
            Custom DNS server <span class="text-gray-300 dark:text-gray-600">(optional — IP address, e.g. 8.8.8.8)</span>
          </label>
          <input v-model="form.dns_server" type="text" placeholder="system default" :class="inputCls" />
        </div>
        <div>
          <div class="flex items-center justify-between mb-2">
            <label class="text-xs text-gray-500 dark:text-gray-400">
              Expected values
              <span class="text-gray-300 dark:text-gray-600 font-normal">— all must appear in the answer; empty = skip check</span>
            </label>
            <button type="button" @click="form.dns_expected_values.push('')"
              class="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors">
              <Plus :size="12" :stroke-width="2" /> Add value
            </button>
          </div>
          <div class="space-y-2">
            <div v-for="(_, i) in form.dns_expected_values" :key="i" class="flex items-center gap-2">
              <input v-model="form.dns_expected_values[i]" type="text"
                :placeholder="form.dns_record_type === 'A' ? '1.2.3.4' : form.dns_record_type === 'CNAME' ? 'target.example.com' : 'expected value'"
                class="flex-1 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-900 dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 transition-colors" />
              <button type="button" @click="form.dns_expected_values.splice(i, 1)"
                class="shrink-0 text-gray-300 hover:text-red-400 dark:text-gray-700 dark:hover:text-red-400 transition-colors">
                <Trash2 :size="13" :stroke-width="1.75" />
              </button>
            </div>
            <p v-if="!form.dns_expected_values.length" class="text-xs text-gray-300 dark:text-gray-700">
              No expected values — only latency and reachability will be checked.
            </p>
          </div>
        </div>
      </template>

      <!-- HTTP: expected status codes -->
      <div v-if="form.type === 'http'">
        <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">
          Expected HTTP status codes <span class="text-gray-300 dark:text-gray-600">(comma-separated)</span>
        </label>
        <input v-model="expectedCodesStr" type="text" placeholder="200, 201, 204" :class="inputCls" />
      </div>

      <!-- Failure status -->
      <div>
        <label class="block text-xs text-gray-500 dark:text-gray-400 mb-2">
          Status on failure
          <span class="text-gray-300 dark:text-gray-600 font-normal">
            — assigned when connection fails{{ form.type === 'http' ? ', times out, or returns unexpected code' : ' or times out' }}
          </span>
        </label>
        <div class="flex flex-wrap gap-2">
          <button v-for="s in STATUS_CHOICES" :key="s.value" type="button"
            @click="form.failure_status = s.value"
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all"
            :class="[s.color, form.failure_status === s.value ? 'ring-2 ring-gray-400/30 scale-105' : 'opacity-40 hover:opacity-80']">
            <component :is="s.icon" :size="11" :stroke-width="2" />
            {{ s.label }}
          </button>
        </div>
      </div>

      <!-- ICMP: packet loss thresholds -->
      <div v-if="form.type === 'icmp'">
        <div class="flex items-center justify-between mb-2">
          <label class="text-xs text-gray-500 dark:text-gray-400">
            Packet-loss thresholds
            <span class="text-gray-300 dark:text-gray-600 font-normal">— if loss% ≤ max → assign status (first match wins)</span>
          </label>
          <button type="button" @click="addPlThreshold"
            class="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors">
            <Plus :size="12" :stroke-width="2" /> Add rule
          </button>
        </div>
        <div class="space-y-2">
          <div v-for="(t, i) in form.packet_loss_thresholds" :key="i"
            class="flex items-center gap-2">
            <span class="text-xs text-gray-400 dark:text-gray-600 w-20 shrink-0">loss ≤</span>
            <div class="relative w-28 shrink-0">
              <input v-model.number="t.max_percent" type="number" min="0" max="100" step="1"
                class="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 pr-8 text-sm text-gray-900 dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 transition-colors" />
              <span class="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-gray-400">%</span>
            </div>
            <span class="text-xs text-gray-400 dark:text-gray-600">→</span>
            <select v-model="t.status"
              class="flex-1 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-900 dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 transition-colors">
              <option v-for="s in STATUS_CHOICES" :key="s.value" :value="s.value">{{ s.label }}</option>
            </select>
            <button type="button" @click="removePlThreshold(i)"
              class="shrink-0 text-gray-300 hover:text-red-400 dark:text-gray-700 dark:hover:text-red-400 transition-colors">
              <Trash2 :size="13" :stroke-width="1.75" />
            </button>
          </div>
          <p v-if="!form.packet_loss_thresholds.length" class="text-xs text-gray-300 dark:text-gray-700">
            No rules — any loss % will fall back to "Status on failure".
          </p>
        </div>
      </div>

      <!-- Response-time thresholds (all types) -->
      <div>
        <div class="flex items-center justify-between mb-2">
          <label class="text-xs text-gray-500 dark:text-gray-400">
            Response-time thresholds
            <span class="text-gray-300 dark:text-gray-600 font-normal">— if time ≤ max ms → assign status (first match wins)</span>
          </label>
          <button type="button" @click="addRtThreshold"
            class="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors">
            <Plus :size="12" :stroke-width="2" /> Add rule
          </button>
        </div>
        <div class="space-y-2">
          <div v-for="(t, i) in form.response_time_thresholds" :key="i"
            class="flex items-center gap-2">
            <span class="text-xs text-gray-400 dark:text-gray-600 w-20 shrink-0">time ≤</span>
            <div class="relative w-28 shrink-0">
              <input v-model.number="t.max_ms" type="number" min="0" step="1"
                class="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 pr-10 text-sm text-gray-900 dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 transition-colors" />
              <span class="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-gray-400">ms</span>
            </div>
            <span class="text-xs text-gray-400 dark:text-gray-600">→</span>
            <select v-model="t.status"
              class="flex-1 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-900 dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 transition-colors">
              <option v-for="s in STATUS_CHOICES" :key="s.value" :value="s.value">{{ s.label }}</option>
            </select>
            <button type="button" @click="removeRtThreshold(i)"
              class="shrink-0 text-gray-300 hover:text-red-400 dark:text-gray-700 dark:hover:text-red-400 transition-colors">
              <Trash2 :size="13" :stroke-width="1.75" />
            </button>
          </div>
          <p v-if="!form.response_time_thresholds.length" class="text-xs text-gray-300 dark:text-gray-700">
            No rules — response time is not evaluated (only connectivity matters).
          </p>
        </div>
      </div>

      <!-- Interval + Timeout + Confirmation + Active -->
      <div class="flex items-end gap-4 flex-wrap">
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Interval (s)</label>
          <input v-model.number="form.interval_seconds" type="number" min="10"
            class="w-24 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 transition-colors" />
        </div>
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Timeout (s)</label>
          <input v-model.number="form.timeout_seconds" type="number" min="1"
            class="w-24 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 transition-colors" />
        </div>
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">
            Confirmation (s)
            <span class="text-gray-300 dark:text-gray-700 font-normal">— 0 = immediate</span>
          </label>
          <input v-model.number="form.confirm_seconds" type="number" min="0" step="30"
            class="w-28 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 transition-colors" />
        </div>
        <label class="flex items-center gap-2 cursor-pointer pb-2">
          <input v-model="form.active" type="checkbox" class="rounded" />
          <span class="text-xs text-gray-500 dark:text-gray-400">Active</span>
        </label>
      </div>

      <div v-if="error" class="text-red-500 dark:text-red-400 text-xs">{{ error }}</div>
      <div class="flex gap-2 pt-1">
        <button @click="submitForm"
          class="bg-gray-800 hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 text-white text-xs px-4 py-1.5 rounded-lg transition-colors">
          Save
        </button>
        <button @click="cancelForm"
          class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 text-xs px-3 py-1.5 transition-colors">
          Cancel
        </button>
      </div>
    </div>

    <!-- ── Monitor list ───────────────────────────────────────────────────────── -->
    <div v-if="monitors.length" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden shadow-sm dark:shadow-none">
      <div v-for="m in monitors" :key="m.id"
        class="px-4 py-3 border-b border-gray-100 dark:border-gray-800 last:border-0">
        <div class="flex items-start justify-between gap-4">
          <!-- Left: name + meta -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <!-- Type badge -->
              <span class="inline-flex items-center gap-1 text-xs font-medium px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400">
                <component :is="TYPE_INFO[m.type].icon" :size="10" :stroke-width="2" />
                {{ TYPE_INFO[m.type].label }}
              </span>
              <!-- Active/inactive -->
              <span v-if="!m.active" class="text-xs text-gray-300 dark:text-gray-700">(inactive)</span>
              <span class="text-sm font-medium text-gray-800 dark:text-gray-200">{{ m.name }}</span>
            </div>

            <!-- Target -->
            <div class="text-xs text-gray-400 dark:text-gray-600 mb-1.5">
              <span v-if="m.type === 'http'">{{ m.url }}</span>
              <span v-else-if="m.type === 'tcp'">{{ m.host }}:{{ m.port }}</span>
              <span v-else-if="m.type === 'dns'">
                {{ m.dns_record_type }} {{ m.host }}
                <span v-if="m.dns_server" class="text-gray-300 dark:text-gray-700"> via {{ m.dns_server }}</span>
              </span>
              <span v-else>{{ m.host }}</span>
            </div>

            <!-- Service link -->
            <div class="text-xs text-gray-400 dark:text-gray-600">
              <span v-if="m.section_name" class="text-gray-300 dark:text-gray-700">{{ m.section_name }} › </span>
              <span>{{ m.service_name || '—' }}</span>
            </div>

            <!-- Last result -->
            <div v-if="m.last_checked_at" class="mt-2 flex flex-wrap items-center gap-3">
              <StatusBadge v-if="m.last_status" :status="m.last_status" />
              <span class="text-xs text-gray-300 dark:text-gray-700">{{ formatTs(m.last_checked_at) }}</span>
              <span v-if="m.last_result?.response_ms !== undefined" class="text-xs text-gray-400 dark:text-gray-500">
                {{ m.last_result.response_ms }} ms
              </span>
              <span v-if="m.last_result?.status_code !== undefined" class="text-xs text-gray-400 dark:text-gray-500">
                HTTP {{ m.last_result.status_code }}
              </span>
              <span v-if="m.last_result?.packet_loss_percent !== undefined" class="text-xs text-gray-400 dark:text-gray-500">
                {{ m.last_result.packet_loss_percent }}% loss
              </span>
              <span v-if="m.last_result?.resolved_values?.length" class="text-xs text-gray-400 dark:text-gray-500">
                → {{ m.last_result.resolved_values.join(', ') }}
              </span>
              <span v-if="m.last_result?.error" class="text-xs text-red-400 dark:text-red-500">
                {{ m.last_result.error }}
              </span>
            </div>
            <div v-else class="mt-1.5 text-xs text-gray-300 dark:text-gray-700">
              Not checked yet
            </div>

            <!-- Pending confirmation banner -->
            <div v-if="m.pending_status" class="mt-2 flex items-center gap-2 text-xs text-amber-600 dark:text-amber-400">
              <Clock :size="11" :stroke-width="2" class="shrink-0" />
              Warte auf Bestätigung:
              <StatusBadge :status="m.pending_status" />
              <span class="text-gray-400 dark:text-gray-600">
                seit {{ formatTs(m.pending_since) }}
                · {{ m.confirm_seconds }}s Bestätigungszeit
              </span>
            </div>
          </div>

          <!-- Right: actions -->
          <div class="flex items-center gap-2 shrink-0 mt-0.5">
            <!-- Interval badge -->
            <span class="text-xs text-gray-300 dark:text-gray-700">every {{ m.interval_seconds }}s</span>
            <button @click="triggerRun(m.id)" :disabled="running === m.id"
              class="flex items-center gap-1 text-xs px-2 py-1 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-400 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600 disabled:opacity-40 transition-colors">
              <Play :size="11" :stroke-width="2" />
              {{ running === m.id ? 'Running…' : 'Run now' }}
            </button>
            <button @click="startEdit(m)"
              class="text-xs text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors">
              Edit
            </button>
            <button @click="deleteMonitor(m.id)"
              class="text-xs text-red-400 hover:text-red-600 dark:hover:text-red-300 transition-colors">
              Delete
            </button>
          </div>
        </div>

        <!-- DNS expected values summary -->
        <div v-if="m.type === 'dns' && m.dns_expected_values?.length"
          class="mt-2 text-xs text-gray-400 dark:text-gray-600">
          erwartet: <span class="text-gray-500 dark:text-gray-400">{{ m.dns_expected_values.join(', ') }}</span>
        </div>

        <!-- Threshold summary -->
        <div v-if="m.response_time_thresholds?.length || m.packet_loss_thresholds?.length"
          class="mt-2.5 flex flex-wrap gap-x-4 gap-y-1">
          <div v-for="t in m.packet_loss_thresholds" :key="'pl-'+t.max_percent"
            class="text-xs text-gray-400 dark:text-gray-600">
            loss ≤ {{ t.max_percent }}% → <span class="text-gray-500 dark:text-gray-400">{{ statusLabel(t.status) }}</span>
          </div>
          <div v-for="t in m.response_time_thresholds" :key="'rt-'+t.max_ms"
            class="text-xs text-gray-400 dark:text-gray-600">
            ≤ {{ t.max_ms }} ms → <span class="text-gray-500 dark:text-gray-400">{{ statusLabel(t.status) }}</span>
          </div>
          <div class="text-xs text-gray-300 dark:text-gray-700">
            else → {{ statusLabel(m.failure_status) }}
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="!showForm"
      class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl px-4 py-10 text-center text-gray-400 dark:text-gray-600 text-sm shadow-sm dark:shadow-none">
      <Activity class="w-8 h-8 mx-auto mb-3 opacity-30" :stroke-width="1.5" />
      No monitors yet. Create one to start automatically checking services.
    </div>
  </div>
</template>
