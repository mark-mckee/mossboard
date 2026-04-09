<script setup>
import { ref, computed, onMounted } from 'vue';
import { CheckCircle, Clock, AlertTriangle, XCircle, Wrench, HelpCircle } from 'lucide-vue-next';
import StatusBadge from '../../components/StatusBadge.vue';

const services = ref([]);
const sections = ref([]);
const showForm  = ref(false);
const editId    = ref(null);
const editSlug  = ref('');
const copied    = ref(false);
const error     = ref('');
const form      = ref({ section_id: '', name: '', description: '', status: 'unknown', order: 0, visible: true, note: '', stale_after_seconds: null });

const inputCls = 'w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500';

const STATUS_CHOICES = [
  { value: 'operational',        label: 'Operational',        icon: CheckCircle,   color: 'border-green-500/40 text-green-600 dark:text-green-400 bg-green-500/10 hover:bg-green-500/20' },
  { value: 'performance_issues', label: 'Performance Issues', icon: Clock,         color: 'border-yellow-400/40 text-yellow-600 dark:text-yellow-300 bg-yellow-400/10 hover:bg-yellow-400/20' },
  { value: 'partial_outage',     label: 'Partial Outage',     icon: AlertTriangle, color: 'border-orange-500/40 text-orange-600 dark:text-orange-400 bg-orange-500/10 hover:bg-orange-500/20' },
  { value: 'major_outage',       label: 'Major Outage',       icon: XCircle,       color: 'border-red-500/40 text-red-600 dark:text-red-400 bg-red-500/10 hover:bg-red-500/20' },
  { value: 'under_maintenance',  label: 'Maintenance',        icon: Wrench,        color: 'border-blue-500/40 text-blue-600 dark:text-blue-400 bg-blue-500/10 hover:bg-blue-500/20' },
  { value: 'unknown',            label: 'Unknown',            icon: HelpCircle,    color: 'border-gray-400/40 text-gray-600 dark:text-gray-400 bg-gray-400/10 hover:bg-gray-400/20' },
];

async function fetchAll() {
  const [svcRes, secRes] = await Promise.all([fetch('/api/v1/admin/services'), fetch('/api/v1/admin/sections')]);
  if (svcRes.ok) services.value = (await svcRes.json()).services;
  if (secRes.ok) sections.value = (await secRes.json()).sections;
}

function startCreate() { editId.value = null; editSlug.value = ''; form.value = { section_id: sections.value[0]?.id || '', name: '', description: '', status: 'unknown', order: 0, visible: true, note: '', stale_after_seconds: null }; showForm.value = true; }
function startEdit(s) { editId.value = s.id; editSlug.value = s.slug; form.value = { section_id: s.section_id, name: s.name, description: s.description, status: s.status, order: s.order, visible: s.visible, note: '', stale_after_seconds: s.stale_after_seconds ?? null }; showForm.value = true; }
function cancelForm() { showForm.value = false; error.value = ''; copied.value = false; }

function copyEndpoint(type) {
  const text = type === 'id'
    ? `PATCH /api/v1/services/id/${editId.value}/status`
    : `PATCH /api/v1/services/${editSlug.value}/status`;
  navigator.clipboard.writeText(text);
  copied.value = type;
  setTimeout(() => { copied.value = false; }, 2000);
}

async function submitForm() {
  error.value = '';
  const url = editId.value ? `/api/v1/admin/services/${editId.value}` : '/api/v1/admin/services';
  const res = await fetch(url, { method: editId.value ? 'PATCH' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form.value) });
  if (res.ok) { showForm.value = false; await fetchAll(); }
  else { error.value = 'Failed to save.'; }
}

async function deleteService(id) {
  if (!confirm('Delete this service?')) return;
  await fetch(`/api/v1/admin/services/${id}`, { method: 'DELETE' });
  await fetchAll();
}

const groupedServices = computed(() => {
  // Use sections order as defined
  return sections.value.map(sec => ({
    id:       sec.id,
    name:     sec.name,
    services: services.value.filter(svc => svc.section_id === sec.id),
  })).filter(g => g.services.length > 0);
});

const unsectioned = computed(() => services.value.filter(svc => !svc.section_id));

onMounted(fetchAll);
</script>

<template>
  <div class="p-8">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-lg font-bold text-gray-900 dark:text-white">Services</h1>
      <button @click="startCreate" class="bg-gray-800 hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 text-white text-xs px-3 py-1.5 rounded-lg transition-colors">+ New Service</button>
    </div>

    <div v-if="showForm" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5 mb-6 shadow-sm dark:shadow-none">
      <h2 class="text-sm font-semibold text-gray-900 dark:text-white mb-4">{{ editId ? 'Edit Service' : 'New Service' }}</h2>
      <div class="space-y-4">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Name</label>
            <input v-model="form.name" type="text" :class="inputCls" />
          </div>
          <div>
            <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Section</label>
            <select v-model="form.section_id" :class="inputCls">
              <option v-for="sec in sections" :key="sec.id" :value="sec.id">{{ sec.name }}</option>
            </select>
          </div>
          <div class="col-span-2">
            <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Description</label>
            <input v-model="form.description" type="text" :class="inputCls" />
          </div>
        </div>

        <!-- API endpoint (edit only) -->
        <div v-if="editId">
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">API Endpoint</label>
          <div class="flex items-center gap-2">
            <div class="flex-1 space-y-1.5">
              <div class="flex items-center gap-2">
                <code class="flex-1 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-xs text-gray-700 dark:text-gray-300 select-all">PATCH /api/v1/services/{{ editSlug }}/status</code>
                <button type="button" @click="copyEndpoint('slug')"
                  class="shrink-0 text-xs px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors">
                  {{ copied === 'slug' ? 'Copied!' : 'Copy' }}
                </button>
              </div>
              <div class="flex items-center gap-2">
                <code class="flex-1 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-xs text-gray-700 dark:text-gray-300 select-all">PATCH /api/v1/services/id/{{ editId }}/status</code>
                <button type="button" @click="copyEndpoint('id')"
                  class="shrink-0 text-xs px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors">
                  {{ copied === 'id' ? 'Copied!' : 'Copy' }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Status buttons -->
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-2">Status</label>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="s in STATUS_CHOICES" :key="s.value"
              type="button"
              @click="form.status = s.value"
              class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all"
              :class="[s.color, form.status === s.value ? 'ring-2 ring-gray-400/30 scale-105' : 'opacity-50 hover:opacity-90']"
            >
              <component :is="s.icon" :size="12" :stroke-width="2" />
              {{ s.label }}
            </button>
          </div>
        </div>

        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">
            Reason for status change <span class="text-gray-300 dark:text-gray-600">(optional)</span>
          </label>
          <input v-model="form.note" type="text" placeholder="e.g. Scheduled maintenance, deployment…" :class="inputCls" />
        </div>

        <div class="flex items-end gap-4 flex-wrap">
          <div>
            <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Order</label>
            <input v-model.number="form.order" type="number" :class="inputCls" class="w-24" />
          </div>
          <div>
            <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">
              Staleness timeout <span class="text-gray-300 dark:text-gray-600">(optional, in seconds)</span>
            </label>
            <div class="flex items-center gap-2">
              <input
                :value="form.stale_after_seconds ?? ''"
                @input="form.stale_after_seconds = $event.target.value === '' ? null : Number($event.target.value)"
                type="number" min="60" step="60"
                placeholder="deaktiviert"
                class="w-36 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 transition-colors placeholder-gray-300 dark:placeholder-gray-700" />
              <span v-if="form.stale_after_seconds" class="text-xs text-gray-400 dark:text-gray-600">
                → unknown nach {{ Math.round(form.stale_after_seconds / 60) }} Min.
              </span>
            </div>
          </div>
          <label class="flex items-center gap-2 cursor-pointer pb-2">
            <input v-model="form.visible" type="checkbox" class="rounded" />
            <span class="text-xs text-gray-500 dark:text-gray-400">Visible</span>
          </label>
        </div>

        <div v-if="error" class="text-red-500 dark:text-red-400 text-xs">{{ error }}</div>
        <div class="flex gap-2">
          <button @click="submitForm" class="bg-gray-800 hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 text-white text-xs px-4 py-1.5 rounded-lg transition-colors">Save</button>
          <button @click="cancelForm" class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 text-xs px-3 py-1.5 transition-colors">Cancel</button>
        </div>
      </div>
    </div>

    <div class="space-y-4">
      <!-- Grouped by section -->
      <template v-for="group in groupedServices" :key="group.id">
        <div class="flex items-center gap-3 mb-2">
          <span class="text-xs font-semibold text-gray-500 dark:text-gray-400">{{ group.name }}</span>
          <div class="flex-1 h-px bg-gray-100 dark:bg-gray-800" />
        </div>
        <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden shadow-sm dark:shadow-none">
          <div v-for="service in group.services" :key="service.id"
            class="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800 last:border-0">
            <div class="flex-1 min-w-0">
              <span class="text-sm text-gray-800 dark:text-gray-200">{{ service.name }}</span>
              <span v-if="!service.visible" class="ml-2 text-xs text-gray-400 dark:text-gray-600">(hidden)</span>
              <span v-if="service.stale_after_seconds" class="ml-2 text-xs text-gray-400 dark:text-gray-600">
                · unknown nach {{ Math.round(service.stale_after_seconds / 60) }} Min. ohne Update
              </span>
            </div>
            <div class="flex items-center gap-3">
              <StatusBadge :status="service.status" />
              <button @click="startEdit(service)" class="text-xs text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors">Edit</button>
              <button @click="deleteService(service.id)" class="text-xs text-red-400 hover:text-red-600 dark:hover:text-red-300 transition-colors">Delete</button>
            </div>
          </div>
        </div>
      </template>

      <!-- Unsectioned -->
      <template v-if="unsectioned.length">
        <div class="flex items-center gap-3 mb-2">
          <span class="text-xs font-semibold text-gray-400 dark:text-gray-600">Unsectioned</span>
          <div class="flex-1 h-px bg-gray-100 dark:bg-gray-800" />
        </div>
        <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden shadow-sm dark:shadow-none">
          <div v-for="service in unsectioned" :key="service.id"
            class="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800 last:border-0">
            <div class="flex-1 min-w-0">
              <span class="text-sm text-gray-800 dark:text-gray-200">{{ service.name }}</span>
              <span v-if="!service.visible" class="ml-2 text-xs text-gray-400 dark:text-gray-600">(hidden)</span>
              <span v-if="service.stale_after_seconds" class="ml-2 text-xs text-gray-400 dark:text-gray-600">
                · unknown nach {{ Math.round(service.stale_after_seconds / 60) }} Min. ohne Update
              </span>
            </div>
            <div class="flex items-center gap-3">
              <StatusBadge :status="service.status" />
              <button @click="startEdit(service)" class="text-xs text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors">Edit</button>
              <button @click="deleteService(service.id)" class="text-xs text-red-400 hover:text-red-600 dark:hover:text-red-300 transition-colors">Delete</button>
            </div>
          </div>
        </div>
      </template>

      <div v-if="!services.length" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl px-4 py-8 text-center text-gray-400 dark:text-gray-600 text-sm shadow-sm dark:shadow-none">No services yet.</div>
    </div>
  </div>
</template>
