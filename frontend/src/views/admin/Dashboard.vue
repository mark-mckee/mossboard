<script setup>
import { ref, computed } from 'vue';
import { onMounted } from 'vue';
import StatusBadge from '../../components/StatusBadge.vue';

const statusData    = ref(null);
const adminServices = ref([]);
const savingId      = ref(null);

// Pending status change: { serviceId, newStatus, note }
const pending = ref(null);

const STATUS_CHOICES = [
  'operational', 'performance_issues', 'partial_outage',
  'major_outage', 'unknown', 'under_maintenance',
];

async function fetchStatus() {
  const res = await fetch('/api/v1/status');
  if (res.ok) statusData.value = await res.json();
}

async function fetchAdminServices() {
  const res = await fetch('/api/v1/admin/services');
  if (res.ok) adminServices.value = (await res.json()).services;
}

function requestChange(service, newStatus) {
  if (newStatus === service.status) return;
  pending.value = { serviceId: service.id, newStatus, note: '' };
}

function cancelChange() {
  pending.value = null;
}

async function confirmChange() {
  const { serviceId, newStatus, note } = pending.value;
  savingId.value = serviceId;
  pending.value  = null;
  await fetch(`/api/v1/admin/services/${serviceId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: newStatus, note }),
  });
  const svc = adminServices.value.find(s => s.id === serviceId);
  if (svc) svc.status = newStatus;
  savingId.value = null;
  await fetchStatus();
}

const allServices = computed(() => {
  if (!statusData.value) return [];
  return statusData.value.sections.flatMap((s) => s.services);
});

const groupedServices = computed(() => {
  if (!adminServices.value.length) return [];
  const sectionOrder = statusData.value ? statusData.value.sections.map(s => s.name) : [];
  const map = {};
  for (const svc of adminServices.value) {
    const key = svc.section_name || '—';
    if (!map[key]) map[key] = [];
    map[key].push(svc);
  }
  const keys = Object.keys(map).sort((a, b) => {
    const ia = sectionOrder.indexOf(a), ib = sectionOrder.indexOf(b);
    if (ia === -1 && ib === -1) return a.localeCompare(b);
    if (ia === -1) return 1; if (ib === -1) return -1;
    return ia - ib;
  });
  return keys.map(name => ({ name, services: map[name] }));
});

onMounted(() => { fetchStatus(); fetchAdminServices(); });
</script>

<template>
  <div class="p-8">
    <h1 class="text-lg font-bold text-gray-900 dark:text-white mb-6">Dashboard</h1>

    <div v-if="statusData" class="grid grid-cols-2 gap-4 mb-8">
      <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-4 shadow-sm dark:shadow-none">
        <div class="text-xs text-gray-400 dark:text-gray-500 mb-1">Sections</div>
        <div class="text-2xl font-bold text-gray-900 dark:text-white">{{ statusData.sections.length }}</div>
      </div>
      <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-4 shadow-sm dark:shadow-none">
        <div class="text-xs text-gray-400 dark:text-gray-500 mb-1">Services</div>
        <div class="text-2xl font-bold text-gray-900 dark:text-white">{{ allServices.length }}</div>
      </div>
    </div>

    <div v-if="statusData" class="flex items-center gap-2 mb-6">
      <span class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">Overall</span>
      <StatusBadge :status="statusData.overall_status" />
    </div>

    <h2 class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-3">Services</h2>

    <div class="space-y-4">
      <div v-for="group in groupedServices" :key="group.name">
        <div class="flex items-center gap-3 mb-2">
          <span class="text-xs font-semibold text-gray-500 dark:text-gray-400">{{ group.name }}</span>
          <div class="flex-1 h-px bg-gray-100 dark:bg-gray-800" />
        </div>
        <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden shadow-sm dark:shadow-none">
          <template v-for="service in group.services" :key="service.id">
            <!-- Service row -->
            <div
              class="flex items-center gap-3 px-4 py-3 border-b border-gray-100 dark:border-gray-800 last:border-0"
              :class="[
                savingId === service.id ? 'opacity-60' : '',
                pending?.serviceId === service.id ? 'bg-gray-50 dark:bg-gray-800/50' : '',
              ]"
            >
              <div class="flex-1 min-w-0">
                <span class="text-sm text-gray-800 dark:text-gray-200">{{ service.name }}</span>
              </div>
              <StatusBadge :status="service.status" />
              <select
                :value="service.status"
                @change="requestChange(service, $event.target.value)"
                :disabled="savingId === service.id"
                class="text-xs bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1 text-gray-700 dark:text-gray-300 focus:outline-none cursor-pointer"
              >
                <option v-for="s in STATUS_CHOICES" :key="s" :value="s">{{ s }}</option>
              </select>
            </div>

            <!-- Inline note + confirm -->
            <div v-if="pending?.serviceId === service.id"
              class="px-4 py-3 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
              <input
                v-model="pending.note"
                type="text"
                placeholder="Reason for status change (optional)…"
                class="flex-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 text-xs text-gray-900 dark:text-white focus:outline-none"
                @keyup.enter="confirmChange"
                @keyup.escape="cancelChange"
                autofocus
              />
              <button @click="confirmChange"
                class="bg-gray-800 hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 text-white text-xs px-3 py-1.5 rounded-lg transition-colors shrink-0">
                Confirm
              </button>
              <button @click="cancelChange"
                class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-xs px-2 py-1.5 transition-colors shrink-0">
                Cancel
              </button>
            </div>
          </template>
        </div>
      </div>

      <div v-if="!adminServices.length" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl px-4 py-8 text-center text-gray-400 dark:text-gray-600 text-sm shadow-sm dark:shadow-none">
        No services yet.
      </div>
    </div>
  </div>
</template>
