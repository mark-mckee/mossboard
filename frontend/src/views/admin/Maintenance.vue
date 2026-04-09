<script setup>
import { ref, onMounted, computed } from 'vue';
import { Calendar, Wrench, Clock, Check, ChevronRight } from 'lucide-vue-next';

const items    = ref([]);
const services = ref([]);
const showForm = ref(false);
const error    = ref('');
const form     = ref({ service_id: '', title: '', description: '', starts_at: '', ends_at: '', auto_status: false });

const inputCls = 'w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none';

async function fetchAll() {
  const [mRes, sRes] = await Promise.all([
    fetch('/api/v1/admin/maintenance'),
    fetch('/api/v1/admin/services'),
  ]);
  if (mRes.ok) items.value    = (await mRes.json()).maintenance;
  if (sRes.ok) services.value = (await sRes.json()).services;
}

async function createMaintenance() {
  error.value = '';
  if (!form.value.service_id || !form.value.title || !form.value.starts_at || !form.value.ends_at) {
    error.value = 'All required fields must be filled.'; return;
  }
  const res = await fetch('/api/v1/admin/maintenance', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...form.value,
      starts_at: new Date(form.value.starts_at).toISOString(),
      ends_at:   new Date(form.value.ends_at).toISOString(),
    }),
  });
  if (res.ok) {
    showForm.value = false;
    form.value = { service_id: '', title: '', description: '', starts_at: '', ends_at: '' };
    await fetchAll();
  } else { error.value = 'Failed to create.'; }
}

async function deleteMaintenance(id) {
  if (!confirm('Delete this scheduled maintenance?')) return;
  await fetch(`/api/v1/admin/maintenance/${id}`, { method: 'DELETE' });
  await fetchAll();
}

const now        = () => new Date();
const isActive   = (m) => new Date(m.starts_at) <= now() && new Date(m.ends_at) >= now();
const isUpcoming = (m) => new Date(m.starts_at) > now();
const isPast     = (m) => new Date(m.ends_at) < now();

const grouped = computed(() => ({
  active:   items.value.filter(isActive),
  upcoming: items.value.filter(isUpcoming),
  past:     items.value.filter(isPast),
}));

function serviceLabel(m) {
  const parts = [m.section_name, m.service_name].filter(Boolean);
  return parts.join(' › ');
}

function formatDate(iso) {
  return new Date(iso).toLocaleString([], { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function openForm() {
  const d = new Date(); d.setHours(d.getHours() + 1, 0, 0, 0);
  const e = new Date(d); e.setHours(e.getHours() + 1);
  form.value = {
    service_id:  services.value[0]?.id || '',
    title: '', description: '',
    starts_at: d.toISOString().slice(0, 16),
    ends_at:   e.toISOString().slice(0, 16),
    auto_status: false,
  };
  showForm.value = true;
}

function svcOptionLabel(svc) {
  return svc.section_name ? `${svc.section_name} › ${svc.name}` : svc.name;
}

onMounted(fetchAll);
</script>

<template>
  <div class="p-8">
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-2">
        <Calendar class="w-5 h-5 text-blue-500" :stroke-width="1.75" />
        <h1 class="text-lg font-bold text-gray-900 dark:text-white">Scheduled Maintenance</h1>
      </div>
      <button @click="openForm" class="bg-gray-800 hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 text-white text-xs px-3 py-1.5 rounded-lg transition-colors">
        + Schedule Maintenance
      </button>
    </div>

    <!-- Form -->
    <div v-if="showForm" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5 mb-6 shadow-sm dark:shadow-none">
      <h2 class="text-sm font-semibold text-gray-900 dark:text-white mb-4">New Maintenance Window</h2>
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Service</label>
          <select v-model="form.service_id" :class="inputCls">
            <option value="" disabled>Select a service…</option>
            <option v-for="s in services" :key="s.id" :value="s.id">{{ svcOptionLabel(s) }}</option>
          </select>
        </div>
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Title</label>
          <input v-model="form.title" type="text" placeholder="e.g. Database upgrade" :class="inputCls" />
        </div>
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Starts at</label>
          <input v-model="form.starts_at" type="datetime-local" :class="inputCls" />
        </div>
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Ends at</label>
          <input v-model="form.ends_at" type="datetime-local" :class="inputCls" />
        </div>
        <div class="col-span-2">
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Description <span class="text-gray-300 dark:text-gray-600">(optional)</span></label>
          <textarea v-model="form.description" rows="2" :class="inputCls" class="resize-none" />
        </div>
        <div class="col-span-2">
          <label class="flex items-center gap-2 cursor-pointer select-none">
            <input type="checkbox" v-model="form.auto_status" class="w-4 h-4 rounded accent-blue-500" />
            <span class="text-xs text-gray-700 dark:text-gray-300">Automatically set service status to <span class="font-medium text-blue-500">under_maintenance</span> when window starts, and restore to <span class="font-medium text-green-500">operational</span> when it ends</span>
          </label>
        </div>
      </div>
      <div v-if="error" class="text-red-500 dark:text-red-400 text-xs mt-3">{{ error }}</div>
      <div class="flex gap-2 mt-4">
        <button @click="createMaintenance" class="bg-blue-600 hover:bg-blue-500 text-white text-xs px-4 py-1.5 rounded-lg transition-colors">Schedule</button>
        <button @click="showForm = false" class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 text-xs px-3 py-1.5 transition-colors">Cancel</button>
      </div>
    </div>

    <!-- Active -->
    <template v-if="grouped.active.length">
      <div class="flex items-center gap-1.5 mb-3">
        <Wrench class="w-3.5 h-3.5 text-blue-500" :stroke-width="1.75" />
        <span class="text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wider">Active now</span>
      </div>
      <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden shadow-sm dark:shadow-none mb-6">
        <div v-for="m in grouped.active" :key="m.id"
          class="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800 last:border-0 bg-blue-500/5">
          <div class="flex items-start gap-3">
            <div class="mt-0.5 w-7 h-7 rounded-full flex items-center justify-center shrink-0 border bg-blue-500/10 border-blue-500/20 text-blue-500">
              <Calendar class="w-3.5 h-3.5" :stroke-width="1.75" />
            </div>
            <div>
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-sm font-medium text-gray-800 dark:text-gray-200">{{ m.title }}</span>
                <span v-if="serviceLabel(m)" class="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400">{{ serviceLabel(m) }}</span>
                <span v-if="m.auto_status" class="text-xs px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-500 border border-blue-500/20">auto-status</span>
              </div>
              <div class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{{ formatDate(m.starts_at) }} → {{ formatDate(m.ends_at) }}</div>
              <div v-if="m.description" class="text-xs text-gray-400 dark:text-gray-600 mt-0.5">{{ m.description }}</div>
            </div>
          </div>
          <button @click="deleteMaintenance(m.id)" class="text-xs text-red-400 hover:text-red-600 dark:hover:text-red-300 transition-colors ml-4 shrink-0">Delete</button>
        </div>
      </div>
    </template>

    <!-- Upcoming -->
    <template v-if="grouped.upcoming.length">
      <div class="flex items-center gap-1.5 mb-3">
        <Clock class="w-3.5 h-3.5 text-gray-400 dark:text-gray-500" :stroke-width="1.75" />
        <span class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Upcoming</span>
      </div>
      <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden shadow-sm dark:shadow-none mb-6">
        <div v-for="m in grouped.upcoming" :key="m.id"
          class="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800 last:border-0">
          <div class="flex items-start gap-3">
            <div class="mt-0.5 w-7 h-7 rounded-full flex items-center justify-center shrink-0 border bg-gray-100 dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-500">
              <Calendar class="w-3.5 h-3.5" :stroke-width="1.75" />
            </div>
            <div>
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-sm font-medium text-gray-800 dark:text-gray-200">{{ m.title }}</span>
                <span v-if="serviceLabel(m)" class="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400">{{ serviceLabel(m) }}</span>
                <span v-if="m.auto_status" class="text-xs px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-500 border border-blue-500/20">auto-status</span>
              </div>
              <div class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{{ formatDate(m.starts_at) }} → {{ formatDate(m.ends_at) }}</div>
              <div v-if="m.description" class="text-xs text-gray-400 dark:text-gray-600 mt-0.5">{{ m.description }}</div>
            </div>
          </div>
          <button @click="deleteMaintenance(m.id)" class="text-xs text-red-400 hover:text-red-600 dark:hover:text-red-300 transition-colors ml-4 shrink-0">Delete</button>
        </div>
      </div>
    </template>

    <!-- Past -->
    <template v-if="grouped.past.length">
      <div class="flex items-center gap-1.5 mb-3">
        <Check class="w-3.5 h-3.5 text-gray-300 dark:text-gray-600" :stroke-width="1.75" />
        <span class="text-xs font-semibold text-gray-400 dark:text-gray-600 uppercase tracking-wider">Past</span>
      </div>
      <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden shadow-sm dark:shadow-none">
        <div v-for="m in grouped.past" :key="m.id"
          class="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800 last:border-0">
          <div class="flex items-start gap-3">
            <div class="mt-0.5 w-7 h-7 rounded-full flex items-center justify-center shrink-0 border bg-gray-100 dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-400">
              <Calendar class="w-3.5 h-3.5" :stroke-width="1.75" />
            </div>
            <div>
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-sm font-medium text-gray-400 dark:text-gray-500">{{ m.title }}</span>
                <span v-if="serviceLabel(m)" class="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-600">{{ serviceLabel(m) }}</span>
                <span v-if="m.auto_status" class="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-600 border border-gray-200 dark:border-gray-700">auto-status</span>
              </div>
              <div class="text-xs text-gray-400 dark:text-gray-600 mt-0.5">{{ formatDate(m.starts_at) }} → {{ formatDate(m.ends_at) }}</div>
              <div v-if="m.description" class="text-xs text-gray-400 dark:text-gray-600 mt-0.5">{{ m.description }}</div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <div v-if="!items.length && !showForm" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl px-4 py-12 text-center shadow-sm dark:shadow-none">
      <Calendar class="w-8 h-8 text-gray-300 dark:text-gray-700 mx-auto mb-2" :stroke-width="1.5" />
      <p class="text-gray-400 dark:text-gray-600 text-sm">No maintenance windows scheduled.</p>
    </div>
  </div>
</template>
