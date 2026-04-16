<script setup>
import { ref, onMounted } from 'vue';

const tokens   = ref([]);
const services = ref([]);
const metrics  = ref([]);
const showForm = ref(false);
const newToken = ref(null);
const error    = ref('');
const form     = ref({ name: '', service_ids: [], metric_ids: [] });

const inputCls = 'w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none';

async function fetchAll() {
  const [tokRes, svcRes, metRes] = await Promise.all([
    fetch('/api/v1/admin/tokens'),
    fetch('/api/v1/admin/services'),
    fetch('/api/v1/admin/metrics'),
  ]);
  if (tokRes.ok) tokens.value   = (await tokRes.json()).tokens;
  if (svcRes.ok) services.value = (await svcRes.json()).services;
  if (metRes.ok) metrics.value  = (await metRes.json()).metrics;
  buildServicesBySection();
}

async function createToken() {
  error.value = '';
  const res = await fetch('/api/v1/admin/tokens', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(form.value),
  });
  if (res.ok) {
    newToken.value = await res.json();
    showForm.value = false;
    form.value = { name: '', service_ids: [], metric_ids: [] };
    await fetchAll();
  } else { error.value = 'Failed to create.'; }
}

async function toggleToken(token) {
  await fetch(`/api/v1/admin/tokens/${token.id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ active: !token.active }),
  });
  await fetchAll();
}

async function deleteToken(id) {
  if (!confirm('Revoke this token permanently?')) return;
  await fetch(`/api/v1/admin/tokens/${id}`, { method: 'DELETE' });
  await fetchAll();
}

function copyToken() { navigator.clipboard.writeText(newToken.value.token); }

function serviceLabel(info) {
  return info.section_name ? `${info.name} (${info.section_name})` : info.name;
}

function scopeLabel(token) {
  const parts = [];
  if (token.services_info?.length)
    parts.push(token.services_info.map(serviceLabel).join(', '));
  else
    parts.push('All services');
  if (token.metrics_info?.length)
    parts.push(`metrics: ${token.metrics_info.map(m => m.name).join(', ')}`);
  else
    parts.push('all metrics');
  return parts.join(' · ');
}

function formatDate(iso) {
  if (!iso) return 'Never';
  return new Date(iso).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

// Group services by section for the checkbox list
const servicesBySectionMap = ref({});
function buildServicesBySection() {
  const map = {};
  for (const svc of services.value) {
    const sec = svc.section_name || 'Unsectioned';
    if (!map[sec]) map[sec] = [];
    map[sec].push(svc);
  }
  servicesBySectionMap.value = map;
}

onMounted(fetchAll);
</script>

<template>
  <div class="p-8">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-lg font-bold text-gray-900 dark:text-white">API Tokens</h1>
      <button @click="showForm = !showForm; newToken = null"
        class="bg-gray-800 hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 text-white text-xs px-3 py-1.5 rounded-lg transition-colors">
        + New Token
      </button>
    </div>

    <!-- New token reveal -->
    <div v-if="newToken" class="bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-600/30 rounded-xl p-4 mb-6">
      <p class="text-xs text-green-700 dark:text-green-400 mb-2 font-semibold">Token created — copy it now, it won't be shown again.</p>
      <div class="flex items-center gap-2">
        <code class="flex-1 bg-white dark:bg-gray-900 rounded-lg px-3 py-2 text-xs text-green-700 dark:text-green-300 break-all border border-green-200 dark:border-green-800">{{ newToken.token }}</code>
        <button @click="copyToken" class="bg-gray-800 hover:bg-gray-700 dark:bg-gray-700 text-white text-xs px-3 py-1.5 rounded-lg shrink-0">Copy</button>
      </div>
      <button @click="newToken = null" class="mt-2 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">Dismiss</button>
    </div>

    <!-- Create form -->
    <div v-if="showForm" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5 mb-6 shadow-sm dark:shadow-none">
      <h2 class="text-sm font-semibold text-gray-900 dark:text-white mb-4">New Token</h2>
      <div class="space-y-4">

        <!-- Name -->
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Name</label>
          <input v-model="form.name" type="text" placeholder="e.g. CI Pipeline" :class="inputCls" />
        </div>

        <!-- Services -->
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-2">
            Authorized services
            <span class="text-gray-300 dark:text-gray-600">(empty = all)</span>
          </label>
          <div class="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
            <div v-for="(svcs, secName) in servicesBySectionMap" :key="secName">
              <div class="px-3 py-1.5 bg-gray-50 dark:bg-gray-800 text-xs text-gray-400 dark:text-gray-600 uppercase tracking-wider border-b border-gray-200 dark:border-gray-700">
                {{ secName }}
              </div>
              <div class="px-3 py-2 space-y-1.5">
                <label v-for="svc in svcs" :key="svc.id" class="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" :value="svc.id" v-model="form.service_ids" class="rounded accent-gray-700 dark:accent-gray-400" />
                  <span class="text-xs text-gray-700 dark:text-gray-300">{{ svc.name }}</span>
                </label>
              </div>
            </div>
            <div v-if="!services.length" class="px-3 py-3 text-xs text-gray-400 dark:text-gray-600 italic">No services yet</div>
          </div>
        </div>

        <!-- Metrics -->
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-2">
            Authorized metrics
            <span class="text-gray-300 dark:text-gray-600">(empty = all)</span>
          </label>
          <div class="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
            <div v-if="metrics.length" class="px-3 py-2 space-y-1.5">
              <label v-for="m in metrics" :key="m.id" class="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" :value="m.id" v-model="form.metric_ids" class="rounded accent-gray-700 dark:accent-gray-400" />
                <span class="text-xs text-gray-700 dark:text-gray-300">{{ m.name }}</span>
                <span class="text-xs text-gray-400 dark:text-gray-600">{{ m.service_name }}</span>
              </label>
            </div>
            <div v-else class="px-3 py-3 text-xs text-gray-400 dark:text-gray-600 italic">No metrics yet</div>
          </div>
        </div>

        <div v-if="error" class="text-red-500 dark:text-red-400 text-xs">{{ error }}</div>

        <div class="flex gap-2">
          <button @click="createToken"
            class="bg-gray-800 hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 text-white text-xs px-4 py-1.5 rounded-lg transition-colors">
            Generate
          </button>
          <button @click="showForm = false" class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 text-xs px-3 py-1.5 transition-colors">
            Cancel
          </button>
        </div>
      </div>
    </div>

    <!-- Token list -->
    <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden shadow-sm dark:shadow-none">
      <div
        v-for="token in tokens" :key="token.id"
        class="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800 last:border-0"
        :class="!token.active ? 'opacity-50' : ''"
      >
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="text-sm text-gray-800 dark:text-gray-200">{{ token.name }}</span>
            <code class="text-xs text-gray-400 dark:text-gray-500">{{ token.token_prefix }}…</code>
          </div>
          <div class="text-xs text-gray-400 dark:text-gray-600 mt-0.5 truncate">
            {{ scopeLabel(token) }} · Last used: {{ formatDate(token.last_used) }}
          </div>
        </div>
        <div class="flex items-center gap-3 ml-4 shrink-0">
          <span class="text-xs px-2 py-0.5 rounded border"
            :class="token.active
              ? 'text-green-600 dark:text-green-400 border-green-500/30 bg-green-500/10'
              : 'text-gray-400 border-gray-300 dark:border-gray-700 bg-gray-100 dark:bg-gray-800'">
            {{ token.active ? 'Active' : 'Inactive' }}
          </span>
          <button @click="toggleToken(token)" class="text-xs text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors">
            {{ token.active ? 'Disable' : 'Enable' }}
          </button>
          <button @click="deleteToken(token.id)" class="text-xs text-red-400 hover:text-red-600 dark:hover:text-red-300 transition-colors">
            Revoke
          </button>
        </div>
      </div>
      <div v-if="!tokens.length" class="px-4 py-8 text-center text-gray-400 dark:text-gray-600 text-sm">No tokens yet.</div>
    </div>
  </div>
</template>
