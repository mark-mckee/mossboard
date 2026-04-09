<script setup>
import { ref, onMounted } from 'vue';
import { ChevronRight, Search, Crosshair, Eye, CheckCircle } from 'lucide-vue-next';
import StatusBadge from '../../components/StatusBadge.vue';

const incidents      = ref([]);
const services       = ref([]);
const showCreateForm = ref(false);
const showUpdateForm = ref(null);
const error          = ref('');
const createForm     = ref({ service_id: '', title: '', status: 'investigating', message: '' });
const updateForm     = ref({ status: 'identified', message: '' });

const INCIDENT_STATUS = [
  { value: 'investigating', label: 'Investigating', icon: Search,      color: 'text-red-500',    bg: 'bg-red-500/10',    border: 'border-red-500/30',    ring: 'ring-red-500/40'    },
  { value: 'identified',   label: 'Identified',   icon: Crosshair,    color: 'text-orange-500', bg: 'bg-orange-500/10', border: 'border-orange-500/30', ring: 'ring-orange-500/40' },
  { value: 'monitoring',   label: 'Monitoring',   icon: Eye,          color: 'text-blue-500',   bg: 'bg-blue-500/10',   border: 'border-blue-500/30',   ring: 'ring-blue-500/40'   },
  { value: 'resolved',     label: 'Resolved',     icon: CheckCircle,  color: 'text-green-500',  bg: 'bg-green-500/10',  border: 'border-green-500/30',  ring: 'ring-green-500/40'  },
];

const inputCls = 'w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none';

function statusMeta(value) {
  return INCIDENT_STATUS.find(s => s.value === value) || INCIDENT_STATUS[0];
}

async function fetchAll() {
  const [incRes, svcRes] = await Promise.all([fetch('/api/v1/admin/incidents'), fetch('/api/v1/admin/services')]);
  if (incRes.ok) incidents.value = (await incRes.json()).incidents;
  if (svcRes.ok) services.value  = (await svcRes.json()).services;
}

async function createIncident() {
  error.value = '';
  const res = await fetch('/api/v1/admin/incidents', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(createForm.value) });
  if (res.ok) { showCreateForm.value = false; await fetchAll(); }
  else { error.value = 'Failed to create.'; }
}

async function addUpdate(incidentId) {
  error.value = '';
  const res = await fetch(`/api/v1/admin/incidents/${incidentId}/updates`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(updateForm.value) });
  if (res.ok) { showUpdateForm.value = null; await fetchAll(); }
  else { error.value = 'Failed to post update.'; }
}

function serviceLabel(svc) {
  return svc.section_name ? `${svc.section_name} › ${svc.name}` : svc.name;
}

function incidentServiceLabel(incident) {
  if (!incident.service_name) return '';
  return incident.section_name
    ? `${incident.section_name} › ${incident.service_name}`
    : incident.service_name;
}

function formatDate(iso) {
  return new Date(iso).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

onMounted(fetchAll);
</script>

<template>
  <div class="p-8">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-lg font-bold text-gray-900 dark:text-white">Incidents</h1>
      <button @click="showCreateForm = !showCreateForm" class="bg-gray-800 hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 text-white text-xs px-3 py-1.5 rounded-lg transition-colors">+ New Incident</button>
    </div>

    <div v-if="showCreateForm" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5 mb-6 shadow-sm dark:shadow-none">
      <h2 class="text-sm font-semibold text-gray-900 dark:text-white mb-4">New Incident</h2>
      <div class="space-y-4">
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Service</label>
          <select v-model="createForm.service_id" :class="inputCls">
            <option value="" disabled>Select a service…</option>
            <option v-for="s in services" :key="s.id" :value="s.id">{{ serviceLabel(s) }}</option>
          </select>
        </div>
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Title</label>
          <input v-model="createForm.title" type="text" placeholder="e.g. API returning 500 errors" :class="inputCls" />
        </div>
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-2">Status</label>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="s in INCIDENT_STATUS" :key="s.value"
              type="button"
              @click="createForm.status = s.value"
              class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all"
              :class="createForm.status === s.value
                ? [s.color, s.bg, s.border, 'ring-2', s.ring]
                : 'text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'"
            >
              <component :is="s.icon" class="w-3.5 h-3.5" :stroke-width="1.75" />
              {{ s.label }}
            </button>
          </div>
        </div>
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Initial message</label>
          <textarea v-model="createForm.message" rows="3" :class="inputCls" class="resize-none" />
        </div>
        <div v-if="error" class="text-red-500 dark:text-red-400 text-xs">{{ error }}</div>
        <div class="flex gap-2">
          <button @click="createIncident" class="bg-gray-800 hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 text-white text-xs px-4 py-1.5 rounded-lg transition-colors">Create</button>
          <button @click="showCreateForm = false" class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 text-xs px-3 py-1.5 transition-colors">Cancel</button>
        </div>
      </div>
    </div>

    <div class="space-y-4">
      <div v-for="incident in incidents" :key="incident.id"
        class="bg-white dark:bg-gray-900 border rounded-xl overflow-hidden shadow-sm dark:shadow-none"
        :class="incident.resolved_at ? 'border-gray-200 dark:border-gray-800' : 'border-orange-400/40'">
        <div class="px-4 py-3 flex items-center justify-between gap-3 border-b border-gray-100 dark:border-gray-800">
          <div>
            <span class="text-sm font-medium text-gray-800 dark:text-gray-200">{{ incident.title }}</span>
            <span v-if="incidentServiceLabel(incident)" class="ml-2 inline-flex items-center text-xs text-gray-400 dark:text-gray-500">
              <span v-if="incident.section_name">{{ incident.section_name }}</span>
              <ChevronRight v-if="incident.section_name" class="w-3 h-3 mx-0.5" :stroke-width="2" />
              <span>{{ incident.service_name }}</span>
            </span>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <span v-if="!incident.resolved_at" class="text-xs px-2 py-0.5 rounded bg-orange-500/15 text-orange-600 dark:text-orange-400 border border-orange-500/30">Ongoing</span>
            <span v-else class="text-xs text-gray-400 dark:text-gray-600">Resolved</span>
            <button v-if="!incident.resolved_at" @click="showUpdateForm = incident.id; updateForm = { status: 'identified', message: '' }"
              class="text-xs text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors">Add update</button>
          </div>
        </div>

        <div v-if="showUpdateForm === incident.id" class="px-4 py-4 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-100 dark:border-gray-800">
          <div class="space-y-3">
            <div>
              <div class="text-xs text-gray-500 dark:text-gray-400 mb-2">Status</div>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="s in INCIDENT_STATUS" :key="s.value"
                  type="button"
                  @click="updateForm.status = s.value"
                  class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all"
                  :class="updateForm.status === s.value
                    ? [s.color, s.bg, s.border, 'ring-2', s.ring]
                    : 'text-gray-500 dark:text-gray-400 bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'"
                >
                  <component :is="s.icon" class="w-3.5 h-3.5" :stroke-width="1.75" />
                  {{ s.label }}
                </button>
              </div>
            </div>
            <textarea v-model="updateForm.message" rows="2" placeholder="Update message…" class="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-xs text-gray-900 dark:text-white focus:outline-none resize-none" />
            <div class="flex gap-2">
              <button @click="addUpdate(incident.id)" class="bg-gray-800 hover:bg-gray-700 dark:bg-gray-700 text-white text-xs px-3 py-1 rounded-lg transition-colors">Post</button>
              <button @click="showUpdateForm = null" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-xs px-2 py-1 transition-colors">Cancel</button>
            </div>
          </div>
        </div>

        <div class="px-4 py-3 space-y-2">
          <div v-for="(update, i) in [...incident.updates].reverse()" :key="i" class="flex items-start gap-2">
            <StatusBadge :status="update.status" />
            <span class="text-xs text-gray-500 dark:text-gray-400 mt-0.5 flex-1">{{ update.message }}</span>
            <span class="text-xs text-gray-400 dark:text-gray-600 ml-auto shrink-0">{{ formatDate(update.created_at) }}</span>
          </div>
        </div>
      </div>
      <div v-if="!incidents.length" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl px-4 py-8 text-center text-gray-400 dark:text-gray-600 text-sm shadow-sm dark:shadow-none">No incidents.</div>
    </div>
  </div>
</template>
