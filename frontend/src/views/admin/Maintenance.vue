<script setup>
import { ref, onMounted, computed } from 'vue';
import { Calendar, Wrench, Clock, Check, RefreshCw, Pencil, X } from 'lucide-vue-next';

const items    = ref([]);
const services = ref([]);
const showForm = ref(false);
const error    = ref('');
const editId   = ref(null);
const editForm = ref({});

const form = ref({
  service_ids: [], title: '', description: '',
  starts_at: '', ends_at: '',
  auto_status: false, recurrence: 'none', recurrence_day: '',
});

const RECURRENCE_OPTS = [
  { value: 'none',    label: 'No recurrence' },
  { value: 'daily',   label: 'Daily' },
  { value: 'weekly',  label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' },
];
const WEEKDAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
const inputCls = 'w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none';

async function fetchAll() {
  try {
    const [mRes, sRes] = await Promise.all([
      fetch('/api/v1/admin/maintenance'),
      fetch('/api/v1/admin/services'),
    ]);
    if (mRes.ok) items.value    = (await mRes.json()).maintenance ?? [];
    if (sRes.ok) services.value = (await sRes.json()).services    ?? [];
  } catch (e) {
    console.error('Maintenance fetch failed:', e);
  }
}

function localDT(d) {
  const p = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}
function toLocalDT(iso) { return iso ? localDT(new Date(iso)) : ''; }

function toggleSvc(id, f) {
  const idx = f.service_ids.indexOf(id);
  if (idx === -1) f.service_ids.push(id);
  else f.service_ids.splice(idx, 1);
}

function recurrenceDayDefault(f) {
  const d = new Date(f.starts_at || Date.now());
  if (f.recurrence === 'weekly')  return WEEKDAYS[d.getDay() === 0 ? 6 : d.getDay() - 1];
  if (f.recurrence === 'monthly') return String(d.getDate());
  return '';
}

async function createMaintenance() {
  error.value = '';
  if (!form.value.title || !form.value.starts_at || !form.value.ends_at) {
    error.value = 'Title, starts at and ends at are required.'; return;
  }
  const res = await fetch('/api/v1/admin/maintenance', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      service_ids:    form.value.service_ids,
      title:          form.value.title.trim(),
      description:    form.value.description,
      starts_at:      new Date(form.value.starts_at).toISOString(),
      ends_at:        new Date(form.value.ends_at).toISOString(),
      auto_status:    form.value.auto_status,
      recurrence:     form.value.recurrence,
      recurrence_day: form.value.recurrence_day,
    }),
  });
  if (res.ok) { showForm.value = false; await fetchAll(); }
  else { error.value = 'Failed to create.'; }
}

function openEdit(m) {
  showForm.value = false;
  editId.value   = m.id;
  editForm.value = {
    service_ids:    (m.services || []).map(s => s.id),
    title:          m.title,
    description:    m.description || '',
    starts_at:      toLocalDT(m.starts_at),
    ends_at:        toLocalDT(m.ends_at),
    auto_status:    m.auto_status,
    recurrence:     m.recurrence || 'none',
    recurrence_day: m.recurrence_day || '',
  };
}

function closeEdit() { editId.value = null; editForm.value = {}; }

async function saveEdit(id) {
  const res = await fetch(`/api/v1/admin/maintenance/${id}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      service_ids:    editForm.value.service_ids,
      title:          editForm.value.title.trim(),
      description:    editForm.value.description,
      starts_at:      new Date(editForm.value.starts_at).toISOString(),
      ends_at:        new Date(editForm.value.ends_at).toISOString(),
      auto_status:    editForm.value.auto_status,
      recurrence:     editForm.value.recurrence,
      recurrence_day: editForm.value.recurrence_day,
    }),
  });
  if (res.ok) { closeEdit(); await fetchAll(); }
}

async function deleteMaintenance(id) {
  if (!confirm('Delete this scheduled maintenance?')) return;
  await fetch(`/api/v1/admin/maintenance/${id}`, { method: 'DELETE' });
  if (editId.value === id) closeEdit();
  await fetchAll();
}

const now        = () => new Date();
const isActive   = m => new Date(m.starts_at) <= now() && new Date(m.ends_at) >= now();
const isUpcoming = m => new Date(m.starts_at) > now();
const isPast     = m => new Date(m.ends_at)   <  now();

const grouped = computed(() => ({
  active:   items.value.filter(isActive),
  upcoming: items.value.filter(isUpcoming),
  past:     items.value.filter(isPast),
}));

function serviceLabels(m) {
  return (m.services || [])
    .map(s => s.section_name ? `${s.section_name} › ${s.name}` : s.name)
    .join(', ');
}

function recurrenceLabel(m) {
  if (!m.recurrence || m.recurrence === 'none') return null;
  const base = RECURRENCE_OPTS.find(o => o.value === m.recurrence)?.label || m.recurrence;
  return m.recurrence_day ? `${base} (${m.recurrence_day})` : base;
}

function formatDate(iso) {
  return new Date(iso).toLocaleString([], { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function openForm() {
  closeEdit();
  const d = new Date(); d.setHours(d.getHours() + 1, 0, 0, 0);
  const e = new Date(d); e.setHours(e.getHours() + 1);
  form.value = {
    service_ids: [], title: '', description: '',
    starts_at: localDT(d), ends_at: localDT(e),
    auto_status: false, recurrence: 'none',
    recurrence_day: WEEKDAYS[d.getDay() === 0 ? 6 : d.getDay() - 1],
  };
  showForm.value = true;
}

function svcLabel(s) {
  return s.section_name ? `${s.section_name} › ${s.name}` : s.name;
}

onMounted(fetchAll);
</script>

<template>
  <div class="p-8">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-2">
        <Calendar class="w-5 h-5 text-blue-500" :stroke-width="1.75" />
        <h1 class="text-lg font-bold text-gray-900 dark:text-white">Scheduled Maintenance</h1>
      </div>
      <button @click="openForm" class="bg-gray-800 hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 text-white text-xs px-3 py-1.5 rounded-lg transition-colors">
        + Schedule Maintenance
      </button>
    </div>

    <!-- Create form -->
    <div v-if="showForm" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5 mb-6 shadow-sm dark:shadow-none">
      <h2 class="text-sm font-semibold text-gray-900 dark:text-white mb-4">New Maintenance Window</h2>
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Title</label>
          <input v-model="form.title" type="text" placeholder="e.g. Database upgrade" :class="inputCls" />
        </div>
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Recurrence</label>
          <select v-model="form.recurrence" @change="form.recurrence_day = recurrenceDayDefault(form)" :class="inputCls">
            <option v-for="o in RECURRENCE_OPTS" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
        </div>
        <div v-if="form.recurrence === 'weekly'">
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Day of week</label>
          <select v-model="form.recurrence_day" :class="inputCls">
            <option v-for="day in WEEKDAYS" :key="day" :value="day">{{ day }}</option>
          </select>
        </div>
        <div v-else-if="form.recurrence === 'monthly'">
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Day of month</label>
          <select v-model="form.recurrence_day" :class="inputCls">
            <option v-for="d in 31" :key="d" :value="String(d)">{{ d }}</option>
          </select>
        </div>
        <div v-else></div>
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">
            {{ form.recurrence !== 'none' ? 'First occurrence — start' : 'Starts at' }}
          </label>
          <input v-model="form.starts_at" type="datetime-local" :class="inputCls" />
        </div>
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">
            {{ form.recurrence !== 'none' ? 'First occurrence — end' : 'Ends at' }}
          </label>
          <input v-model="form.ends_at" type="datetime-local" :class="inputCls" />
        </div>
        <div class="col-span-2">
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Description <span class="text-gray-300 dark:text-gray-600">(optional)</span></label>
          <textarea v-model="form.description" rows="2" :class="inputCls" class="resize-none" />
        </div>
        <div class="col-span-2">
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Services <span class="text-gray-300 dark:text-gray-600">(none = global)</span></label>
          <div class="flex flex-wrap gap-x-4 gap-y-2 p-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg min-h-[40px]">
            <span v-if="!services.length" class="text-xs text-gray-400 dark:text-gray-500">No services found.</span>
            <label v-for="s in services" :key="s.id" class="flex items-center gap-1.5 cursor-pointer select-none text-xs text-gray-700 dark:text-gray-300">
              <input type="checkbox" :checked="form.service_ids.includes(s.id)" @change="toggleSvc(s.id, form)" class="w-3.5 h-3.5 rounded accent-blue-500" />
              {{ svcLabel(s) }}
            </label>
          </div>
        </div>
        <div class="col-span-2">
          <label class="flex items-center gap-2 cursor-pointer select-none">
            <input type="checkbox" v-model="form.auto_status" class="w-4 h-4 rounded accent-blue-500" />
            <span class="text-xs text-gray-700 dark:text-gray-300">Auto-set services to <span class="font-medium text-blue-500">under_maintenance</span> on start, restore to <span class="font-medium text-green-500">operational</span> on end</span>
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
        <template v-for="m in grouped.active" :key="m.id">
          <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800 last:border-0 bg-blue-500/5">
            <div class="flex items-start gap-3 min-w-0">
              <div class="mt-0.5 w-7 h-7 rounded-full flex items-center justify-center shrink-0 border bg-blue-500/10 border-blue-500/20 text-blue-500">
                <Calendar class="w-3.5 h-3.5" :stroke-width="1.75" />
              </div>
              <div class="min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="text-sm font-medium text-gray-800 dark:text-gray-200">{{ m.title }}</span>
                  <span v-if="serviceLabels(m)" class="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400">{{ serviceLabels(m) }}</span>
                  <span v-if="m.auto_status" class="text-xs px-1.5 py-0.5 rounded border bg-blue-500/10 text-blue-500 border-blue-500/20">auto-status</span>
                  <span v-if="recurrenceLabel(m)" class="flex items-center gap-1 text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400">
                    <RefreshCw class="w-3 h-3" :stroke-width="1.75" />{{ recurrenceLabel(m) }}
                  </span>
                </div>
                <div class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{{ formatDate(m.starts_at) }} → {{ formatDate(m.ends_at) }}</div>
                <div v-if="m.description" class="text-xs text-gray-400 dark:text-gray-600 mt-0.5">{{ m.description }}</div>
              </div>
            </div>
            <div class="flex items-center gap-2 ml-4 shrink-0">
              <button @click="editId === m.id ? closeEdit() : openEdit(m)" class="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors">
                <X v-if="editId === m.id" class="w-3.5 h-3.5" :stroke-width="1.75" />
                <Pencil v-else class="w-3.5 h-3.5" :stroke-width="1.75" />
              </button>
              <button @click="deleteMaintenance(m.id)" class="text-xs text-red-400 hover:text-red-600 dark:hover:text-red-300 transition-colors">Delete</button>
            </div>
          </div>
          <div v-if="editId === m.id" class="px-4 py-4 border-b border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50">
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Title</label>
                <input v-model="editForm.title" type="text" :class="inputCls" />
              </div>
              <div>
                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Recurrence</label>
                <select v-model="editForm.recurrence" @change="editForm.recurrence_day = recurrenceDayDefault(editForm)" :class="inputCls">
                  <option v-for="o in RECURRENCE_OPTS" :key="o.value" :value="o.value">{{ o.label }}</option>
                </select>
              </div>
              <div v-if="editForm.recurrence === 'weekly'">
                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Day of week</label>
                <select v-model="editForm.recurrence_day" :class="inputCls">
                  <option v-for="day in WEEKDAYS" :key="day" :value="day">{{ day }}</option>
                </select>
              </div>
              <div v-else-if="editForm.recurrence === 'monthly'">
                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Day of month</label>
                <select v-model="editForm.recurrence_day" :class="inputCls">
                  <option v-for="d in 31" :key="d" :value="String(d)">{{ d }}</option>
                </select>
              </div>
              <div v-else></div>
              <div>
                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">
                  {{ editForm.recurrence !== 'none' ? 'This occurrence — start' : 'Starts at' }}
                </label>
                <input v-model="editForm.starts_at" type="datetime-local" :class="inputCls" />
              </div>
              <div>
                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">
                  {{ editForm.recurrence !== 'none' ? 'This occurrence — end' : 'Ends at' }}
                </label>
                <input v-model="editForm.ends_at" type="datetime-local" :class="inputCls" />
              </div>
              <div class="col-span-2">
                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Description</label>
                <textarea v-model="editForm.description" rows="2" :class="inputCls" class="resize-none" />
              </div>
              <div class="col-span-2">
                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Services <span class="text-gray-300 dark:text-gray-600">(none = global)</span></label>
                <div class="flex flex-wrap gap-x-4 gap-y-2 p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg min-h-[40px]">
                  <span v-if="!services.length" class="text-xs text-gray-400 dark:text-gray-500">No services found.</span>
                  <label v-for="s in services" :key="s.id" class="flex items-center gap-1.5 cursor-pointer select-none text-xs text-gray-700 dark:text-gray-300">
                    <input type="checkbox" :checked="editForm.service_ids && editForm.service_ids.includes(s.id)" @change="toggleSvc(s.id, editForm)" class="w-3.5 h-3.5 rounded accent-blue-500" />
                    {{ svcLabel(s) }}
                  </label>
                </div>
              </div>
              <div class="col-span-2">
                <label class="flex items-center gap-2 cursor-pointer select-none">
                  <input type="checkbox" v-model="editForm.auto_status" class="w-4 h-4 rounded accent-blue-500" />
                  <span class="text-xs text-gray-700 dark:text-gray-300">Auto-set services to <span class="font-medium text-blue-500">under_maintenance</span> on start, restore to <span class="font-medium text-green-500">operational</span> on end</span>
                </label>
              </div>
            </div>
            <div class="flex gap-2 mt-3">
              <button @click="saveEdit(m.id)" class="bg-blue-600 hover:bg-blue-500 text-white text-xs px-4 py-1.5 rounded-lg transition-colors">Save</button>
              <button @click="closeEdit" class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 text-xs px-3 py-1.5 transition-colors">Cancel</button>
            </div>
          </div>
        </template>
      </div>
    </template>

    <!-- Upcoming -->
    <template v-if="grouped.upcoming.length">
      <div class="flex items-center gap-1.5 mb-3">
        <Clock class="w-3.5 h-3.5 text-gray-400 dark:text-gray-500" :stroke-width="1.75" />
        <span class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Upcoming</span>
      </div>
      <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden shadow-sm dark:shadow-none mb-6">
        <template v-for="m in grouped.upcoming" :key="m.id">
          <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800 last:border-0">
            <div class="flex items-start gap-3 min-w-0">
              <div class="mt-0.5 w-7 h-7 rounded-full flex items-center justify-center shrink-0 border bg-gray-100 dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-400">
                <Calendar class="w-3.5 h-3.5" :stroke-width="1.75" />
              </div>
              <div class="min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="text-sm font-medium text-gray-800 dark:text-gray-200">{{ m.title }}</span>
                  <span v-if="serviceLabels(m)" class="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400">{{ serviceLabels(m) }}</span>
                  <span v-if="m.auto_status" class="text-xs px-1.5 py-0.5 rounded border bg-blue-500/10 text-blue-500 border-blue-500/20">auto-status</span>
                  <span v-if="recurrenceLabel(m)" class="flex items-center gap-1 text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400">
                    <RefreshCw class="w-3 h-3" :stroke-width="1.75" />{{ recurrenceLabel(m) }}
                  </span>
                </div>
                <div class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{{ formatDate(m.starts_at) }} → {{ formatDate(m.ends_at) }}</div>
                <div v-if="m.description" class="text-xs text-gray-400 dark:text-gray-600 mt-0.5">{{ m.description }}</div>
              </div>
            </div>
            <div class="flex items-center gap-2 ml-4 shrink-0">
              <button @click="editId === m.id ? closeEdit() : openEdit(m)" class="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors">
                <X v-if="editId === m.id" class="w-3.5 h-3.5" :stroke-width="1.75" />
                <Pencil v-else class="w-3.5 h-3.5" :stroke-width="1.75" />
              </button>
              <button @click="deleteMaintenance(m.id)" class="text-xs text-red-400 hover:text-red-600 dark:hover:text-red-300 transition-colors">Delete</button>
            </div>
          </div>
          <div v-if="editId === m.id" class="px-4 py-4 border-b border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50">
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Title</label>
                <input v-model="editForm.title" type="text" :class="inputCls" />
              </div>
              <div>
                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Recurrence</label>
                <select v-model="editForm.recurrence" @change="editForm.recurrence_day = recurrenceDayDefault(editForm)" :class="inputCls">
                  <option v-for="o in RECURRENCE_OPTS" :key="o.value" :value="o.value">{{ o.label }}</option>
                </select>
              </div>
              <div v-if="editForm.recurrence === 'weekly'">
                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Day of week</label>
                <select v-model="editForm.recurrence_day" :class="inputCls">
                  <option v-for="day in WEEKDAYS" :key="day" :value="day">{{ day }}</option>
                </select>
              </div>
              <div v-else-if="editForm.recurrence === 'monthly'">
                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Day of month</label>
                <select v-model="editForm.recurrence_day" :class="inputCls">
                  <option v-for="d in 31" :key="d" :value="String(d)">{{ d }}</option>
                </select>
              </div>
              <div v-else></div>
              <div>
                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">
                  {{ editForm.recurrence !== 'none' ? 'This occurrence — start' : 'Starts at' }}
                </label>
                <input v-model="editForm.starts_at" type="datetime-local" :class="inputCls" />
              </div>
              <div>
                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">
                  {{ editForm.recurrence !== 'none' ? 'This occurrence — end' : 'Ends at' }}
                </label>
                <input v-model="editForm.ends_at" type="datetime-local" :class="inputCls" />
              </div>
              <div class="col-span-2">
                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Description</label>
                <textarea v-model="editForm.description" rows="2" :class="inputCls" class="resize-none" />
              </div>
              <div class="col-span-2">
                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Services <span class="text-gray-300 dark:text-gray-600">(none = global)</span></label>
                <div class="flex flex-wrap gap-x-4 gap-y-2 p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg min-h-[40px]">
                  <span v-if="!services.length" class="text-xs text-gray-400 dark:text-gray-500">No services found.</span>
                  <label v-for="s in services" :key="s.id" class="flex items-center gap-1.5 cursor-pointer select-none text-xs text-gray-700 dark:text-gray-300">
                    <input type="checkbox" :checked="editForm.service_ids && editForm.service_ids.includes(s.id)" @change="toggleSvc(s.id, editForm)" class="w-3.5 h-3.5 rounded accent-blue-500" />
                    {{ svcLabel(s) }}
                  </label>
                </div>
              </div>
              <div class="col-span-2">
                <label class="flex items-center gap-2 cursor-pointer select-none">
                  <input type="checkbox" v-model="editForm.auto_status" class="w-4 h-4 rounded accent-blue-500" />
                  <span class="text-xs text-gray-700 dark:text-gray-300">Auto-set services to <span class="font-medium text-blue-500">under_maintenance</span> on start, restore to <span class="font-medium text-green-500">operational</span> on end</span>
                </label>
              </div>
            </div>
            <div class="flex gap-2 mt-3">
              <button @click="saveEdit(m.id)" class="bg-blue-600 hover:bg-blue-500 text-white text-xs px-4 py-1.5 rounded-lg transition-colors">Save</button>
              <button @click="closeEdit" class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 text-xs px-3 py-1.5 transition-colors">Cancel</button>
            </div>
          </div>
        </template>
      </div>
    </template>

    <!-- Past -->
    <template v-if="grouped.past.length">
      <div class="flex items-center gap-1.5 mb-3">
        <Check class="w-3.5 h-3.5 text-gray-300 dark:text-gray-600" :stroke-width="1.75" />
        <span class="text-xs font-semibold text-gray-400 dark:text-gray-600 uppercase tracking-wider">Past</span>
      </div>
      <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden shadow-sm dark:shadow-none mb-6">
        <template v-for="m in grouped.past" :key="m.id">
          <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800 last:border-0">
            <div class="flex items-start gap-3 min-w-0">
              <div class="mt-0.5 w-7 h-7 rounded-full flex items-center justify-center shrink-0 border bg-gray-100 dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-400">
                <Calendar class="w-3.5 h-3.5" :stroke-width="1.75" />
              </div>
              <div class="min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="text-sm font-medium text-gray-400 dark:text-gray-500">{{ m.title }}</span>
                  <span v-if="serviceLabels(m)" class="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-600">{{ serviceLabels(m) }}</span>
                  <span v-if="m.auto_status" class="text-xs px-1.5 py-0.5 rounded border bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-600 border-gray-200 dark:border-gray-700">auto-status</span>
                  <span v-if="recurrenceLabel(m)" class="flex items-center gap-1 text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-600">
                    <RefreshCw class="w-3 h-3" :stroke-width="1.75" />{{ recurrenceLabel(m) }}
                  </span>
                </div>
                <div class="text-xs text-gray-400 dark:text-gray-600 mt-0.5">{{ formatDate(m.starts_at) }} → {{ formatDate(m.ends_at) }}</div>
                <div v-if="m.description" class="text-xs text-gray-400 dark:text-gray-600 mt-0.5">{{ m.description }}</div>
              </div>
            </div>
            <div class="flex items-center gap-2 ml-4 shrink-0">
              <button @click="editId === m.id ? closeEdit() : openEdit(m)" class="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors">
                <X v-if="editId === m.id" class="w-3.5 h-3.5" :stroke-width="1.75" />
                <Pencil v-else class="w-3.5 h-3.5" :stroke-width="1.75" />
              </button>
              <button @click="deleteMaintenance(m.id)" class="text-xs text-red-400 hover:text-red-600 dark:hover:text-red-300 transition-colors">Delete</button>
            </div>
          </div>
          <div v-if="editId === m.id" class="px-4 py-4 border-b border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50">
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Title</label>
                <input v-model="editForm.title" type="text" :class="inputCls" />
              </div>
              <div>
                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Recurrence</label>
                <select v-model="editForm.recurrence" @change="editForm.recurrence_day = recurrenceDayDefault(editForm)" :class="inputCls">
                  <option v-for="o in RECURRENCE_OPTS" :key="o.value" :value="o.value">{{ o.label }}</option>
                </select>
              </div>
              <div v-if="editForm.recurrence === 'weekly'">
                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Day of week</label>
                <select v-model="editForm.recurrence_day" :class="inputCls">
                  <option v-for="day in WEEKDAYS" :key="day" :value="day">{{ day }}</option>
                </select>
              </div>
              <div v-else-if="editForm.recurrence === 'monthly'">
                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Day of month</label>
                <select v-model="editForm.recurrence_day" :class="inputCls">
                  <option v-for="d in 31" :key="d" :value="String(d)">{{ d }}</option>
                </select>
              </div>
              <div v-else></div>
              <div>
                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">
                  {{ editForm.recurrence !== 'none' ? 'This occurrence — start' : 'Starts at' }}
                </label>
                <input v-model="editForm.starts_at" type="datetime-local" :class="inputCls" />
              </div>
              <div>
                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">
                  {{ editForm.recurrence !== 'none' ? 'This occurrence — end' : 'Ends at' }}
                </label>
                <input v-model="editForm.ends_at" type="datetime-local" :class="inputCls" />
              </div>
              <div class="col-span-2">
                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Description</label>
                <textarea v-model="editForm.description" rows="2" :class="inputCls" class="resize-none" />
              </div>
              <div class="col-span-2">
                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Services <span class="text-gray-300 dark:text-gray-600">(none = global)</span></label>
                <div class="flex flex-wrap gap-x-4 gap-y-2 p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg min-h-[40px]">
                  <span v-if="!services.length" class="text-xs text-gray-400 dark:text-gray-500">No services found.</span>
                  <label v-for="s in services" :key="s.id" class="flex items-center gap-1.5 cursor-pointer select-none text-xs text-gray-700 dark:text-gray-300">
                    <input type="checkbox" :checked="editForm.service_ids && editForm.service_ids.includes(s.id)" @change="toggleSvc(s.id, editForm)" class="w-3.5 h-3.5 rounded accent-blue-500" />
                    {{ svcLabel(s) }}
                  </label>
                </div>
              </div>
              <div class="col-span-2">
                <label class="flex items-center gap-2 cursor-pointer select-none">
                  <input type="checkbox" v-model="editForm.auto_status" class="w-4 h-4 rounded accent-blue-500" />
                  <span class="text-xs text-gray-700 dark:text-gray-300">Auto-set services to <span class="font-medium text-blue-500">under_maintenance</span> on start, restore to <span class="font-medium text-green-500">operational</span> on end</span>
                </label>
              </div>
            </div>
            <div class="flex gap-2 mt-3">
              <button @click="saveEdit(m.id)" class="bg-blue-600 hover:bg-blue-500 text-white text-xs px-4 py-1.5 rounded-lg transition-colors">Save</button>
              <button @click="closeEdit" class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 text-xs px-3 py-1.5 transition-colors">Cancel</button>
            </div>
          </div>
        </template>
      </div>
    </template>

    <!-- Empty state -->
    <div v-if="!items.length && !showForm" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl px-4 py-12 text-center shadow-sm dark:shadow-none">
      <Calendar class="w-8 h-8 text-gray-300 dark:text-gray-700 mx-auto mb-2" :stroke-width="1.5" />
      <p class="text-gray-400 dark:text-gray-600 text-sm">No maintenance windows scheduled.</p>
    </div>
  </div>
</template>
