<script setup>
import { ref, computed, onMounted } from 'vue';
import { Bell, Webhook, Mail, Plus, Pencil, X, Trash2, Play, ChevronDown, ChevronUp, Info, Settings2 } from 'lucide-vue-next';

// ── State ─────────────────────────────────────────────────────────────────────
const tab          = ref('rules');     // 'rules' | 'destinations' | 'smtp'
const destinations = ref([]);
const rules        = ref([]);
const services     = ref([]);
const smtp         = ref({ smtp_host: '', smtp_port: 587, smtp_username: '', smtp_from: '', smtp_use_tls: true });
const smtpPassword = ref('');
const smtpSaved    = ref(false);

const showDestForm  = ref(false);
const showRuleForm  = ref(false);
const editDestId    = ref(null);
const editRuleId    = ref(null);
const testingId     = ref(null);
const testResult    = ref({});   // { [dest_id]: 'queued' | 'error' }

const inputCls = 'w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none';
const labelCls = 'block text-xs text-gray-500 dark:text-gray-400 mb-1.5';

// ── Form models ───────────────────────────────────────────────────────────────
const blankDest = () => ({
  name: '', type: 'webhook',
  url: '', method: 'POST', headers: '{}', body_template: '',
  email_to: '', email_subject_template: '', email_body_template: '',
  active: true,
});
const blankRule = () => ({
  name: '', trigger: 'monitor_status_change', destination_id: '',
  filter_from_status: '', filter_to_status: '', service_ids: [], active: true,
});

const destForm = ref(blankDest());
const ruleForm = ref(blankRule());
const formError = ref('');

// ── Trigger metadata ──────────────────────────────────────────────────────────
const TRIGGERS = [
  { value: 'maintenance_created',  label: 'Maintenance Announced',  desc: 'A new maintenance window is created' },
  { value: 'maintenance_started',  label: 'Maintenance Started',    desc: 'A maintenance window becomes active' },
  { value:'maintenance_ended',    label: 'Maintenance Ended',      desc: 'A maintenance window finishes' },
  { value: 'incident_created',    label: 'Incident Created',       desc: 'A new incident is opened' },
  { value: 'incident_updated',    label: 'Incident Updated',       desc: 'An update is added to an incident' },
  { value: 'incident_resolved',   label: 'Incident Resolved',      desc: 'An incident is resolved' },
  { value: 'monitor_status_change', label: 'Monitor Status Change', desc: 'A monitor changes from one status to another' },
];

const STATUS_VALUES = [
  '', 'operational', 'performance_issues', 'partial_outage',
  'major_outage', 'unknown', 'under_maintenance',
];
const STATUS_LABELS = {
  '': 'Any', operational: 'Operational', performance_issues: 'Performance Issues',
  partial_outage: 'Partial Outage', major_outage: 'Major Outage',
  unknown: 'Unknown', under_maintenance: 'Under Maintenance',
};

// Variables available per trigger
const TRIGGER_VARS = {
  maintenance_created:  ['title','description','starts_at','ends_at','service_name','recurrence','timestamp'],
  maintenance_started:  ['title','description','starts_at','ends_at','service_name','timestamp'],
  maintenance_ended:    ['title','description','starts_at','ends_at','service_name','timestamp'],
  incident_created:     ['title','service_name','service_slug','section_name','status','message','timestamp'],
  incident_updated:     ['title','service_name','service_slug','section_name','status','message','timestamp'],
  incident_resolved:    ['title','service_name','service_slug','section_name','status','message','timestamp'],
  monitor_status_change:['service_name','service_slug','section_name','prev_status','status','monitor_name','timestamp'],
};

// ── Fetch ─────────────────────────────────────────────────────────────────────
async function fetchAll() {
  const [dRes, rRes, sRes, smtpRes] = await Promise.all([
    fetch('/api/v1/admin/notifications/destinations'),
    fetch('/api/v1/admin/notifications/rules'),
    fetch('/api/v1/admin/services'),
    fetch('/api/v1/admin/notifications/smtp'),
  ]);
  if (dRes.ok)    destinations.value = (await dRes.json()).destinations ?? [];
  if (rRes.ok)    rules.value        = (await rRes.json()).rules        ?? [];
  if (sRes.ok)    services.value     = (await sRes.json()).services     ?? [];
  if (smtpRes.ok) smtp.value         = await smtpRes.json();
}
onMounted(fetchAll);

// ── SMTP ──────────────────────────────────────────────────────────────────────
async function saveSMTP() {
  const body = { ...smtp.value };
  if (smtpPassword.value) body.smtp_password = smtpPassword.value;
  const res = await fetch('/api/v1/admin/notifications/smtp', {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (res.ok) { smtp.value = await res.json(); smtpPassword.value = ''; smtpSaved.value = true; setTimeout(() => smtpSaved.value = false, 2000); }
}

// ── Destinations ──────────────────────────────────────────────────────────────
function openDestForm(d) {
  formError.value = '';
  if (d) {
    editDestId.value = d.id;
    destForm.value = {
      name: d.name, type: d.type,
      url: d.url, method: d.method, headers: JSON.stringify(d.headers || {}, null, 2),
      body_template: d.body_template,
      email_to: d.email_to, email_subject_template: d.email_subject_template,
      email_body_template: d.email_body_template,
      active: d.active,
    };
  } else {
    editDestId.value = null;
    destForm.value = blankDest();
  }
  showDestForm.value = true;
  showRuleForm.value = false;
}

function closeDestForm() { showDestForm.value = false; editDestId.value = null; formError.value = ''; }

function destPayload() {
  let headers = {};
  try { headers = JSON.parse(destForm.value.headers || '{}'); } catch { /* ignore */ }
  return {
    name: destForm.value.name.trim(), type: destForm.value.type,
    url: destForm.value.url, method: destForm.value.method, headers,
    body_template: destForm.value.body_template,
    email_to: destForm.value.email_to,
    email_subject_template: destForm.value.email_subject_template,
    email_body_template: destForm.value.email_body_template,
    active: destForm.value.active,
  };
}

async function saveDest() {
  formError.value = '';
  if (!destForm.value.name) { formError.value = 'Name is required.'; return; }
  if (destForm.value.type === 'webhook' && !destForm.value.url) { formError.value = 'URL is required for webhook.'; return; }
  if (destForm.value.type === 'email' && !destForm.value.email_to) { formError.value = 'Email address is required.'; return; }
  const url    = editDestId.value ? `/api/v1/admin/notifications/destinations/${editDestId.value}` : '/api/v1/admin/notifications/destinations';
  const method = editDestId.value ? 'PATCH' : 'POST';
  const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(destPayload()) });
  if (res.ok) { closeDestForm(); await fetchAll(); }
  else { formError.value = 'Save failed.'; }
}

async function deleteDest(id) {
  if (!confirm('Delete this destination? Any rules using it will break.')) return;
  await fetch(`/api/v1/admin/notifications/destinations/${id}`, { method: 'DELETE' });
  await fetchAll();
}

async function testDest(id) {
  testingId.value = id;
  testResult.value = { ...testResult.value, [id]: null };
  try {
    const res = await fetch(`/api/v1/admin/notifications/destinations/${id}/test`, { method: 'POST' });
    testResult.value = { ...testResult.value, [id]: res.ok ? 'queued' : 'error' };
  } catch {
    testResult.value = { ...testResult.value, [id]: 'error' };
  }
  testingId.value = null;
}

function insertVar(field, variable, formRef) {
  formRef[field] = (formRef[field] || '') + `{{${variable}}}`;
}

// ── Rules ─────────────────────────────────────────────────────────────────────
function openRuleForm(r) {
  formError.value = '';
  if (r) {
    editRuleId.value = r.id;
    ruleForm.value = {
      name: r.name, trigger: r.trigger,
      destination_id: r.destination?.id || '',
      filter_from_status: r.filter_from_status || '',
      filter_to_status: r.filter_to_status || '',
      service_ids: (r.services || []).map(s => s.id),
      active: r.active,
    };
  } else {
    editRuleId.value = null;
    ruleForm.value = blankRule();
  }
  showRuleForm.value = true;
  showDestForm.value = false;
}
function closeRuleForm() { showRuleForm.value = false; editRuleId.value = null; formError.value = ''; }

function toggleSvc(id) {
  const idx = ruleForm.value.service_ids.indexOf(id);
  if (idx === -1) ruleForm.value.service_ids.push(id);
  else ruleForm.value.service_ids.splice(idx, 1);
}

async function saveRule() {
  formError.value = '';
  if (!ruleForm.value.name) { formError.value = 'Name is required.'; return; }
  if (!ruleForm.value.destination_id) { formError.value = 'Destination is required.'; return; }
  const url    = editRuleId.value ? `/api/v1/admin/notifications/rules/${editRuleId.value}` : '/api/v1/admin/notifications/rules';
  const method = editRuleId.value ? 'PATCH' : 'POST';
  const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(ruleForm.value) });
  if (res.ok) { closeRuleForm(); await fetchAll(); }
  else { formError.value = 'Save failed.'; }
}

async function deleteRule(id) {
  if (!confirm('Delete this rule?')) return;
  await fetch(`/api/v1/admin/notifications/rules/${id}`, { method: 'DELETE' });
  await fetchAll();
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function triggerLabel(v) { return TRIGGERS.find(t => t.value === v)?.label || v; }
function svcLabel(s) { return s.section_name ? `${s.section_name} › ${s.name}` : s.name; }

const currentTriggerVars = computed(() => TRIGGER_VARS[ruleForm.value.trigger] || []);
const currentDestType = computed(() => {
  const d = destinations.value.find(d => d.id === ruleForm.value.destination_id);
  return d?.type || '';
});
</script>

<template>
  <div class="p-8">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-2">
        <Bell class="w-5 h-5 text-blue-500" :stroke-width="1.75" />
        <h1 class="text-lg font-bold text-gray-900 dark:text-white">Notifications</h1>
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex gap-1 mb-6 bg-gray-100 dark:bg-gray-800/60 p-1 rounded-xl w-fit">
      <button v-for="t in [['rules','Rules'],['destinations','Destinations'],['smtp','SMTP']]" :key="t[0]"
        @click="tab = t[0]; showDestForm = false; showRuleForm = false;"
        class="px-4 py-1.5 rounded-lg text-sm font-medium transition-colors"
        :class="tab === t[0]
          ? 'bg-white dark:bg-gray-900 text-gray-900 dark:text-white shadow-sm'
          : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'"
      >{{ t[1] }}</button>
    </div>

    <!-- ══ RULES TAB ══════════════════════════════════════════════════════════ -->
    <template v-if="tab === 'rules'">
      <div class="flex justify-end mb-4">
        <button @click="openRuleForm(null)"
          class="bg-gray-800 hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 text-white text-xs px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5">
          <Plus class="w-3.5 h-3.5" :stroke-width="2" /> Add Rule
        </button>
      </div>

      <!-- Rule form -->
      <div v-if="showRuleForm" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5 mb-6 shadow-sm dark:shadow-none">
        <h2 class="text-sm font-semibold text-gray-900 dark:text-white mb-4">{{ editRuleId ? 'Edit Rule' : 'New Rule' }}</h2>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label :class="labelCls">Rule name</label>
            <input v-model="ruleForm.name" type="text" placeholder="e.g. Alert on major outage" :class="inputCls" />
          </div>
          <div>
            <label :class="labelCls">Destination</label>
            <select v-model="ruleForm.destination_id" :class="inputCls">
              <option value="">— select —</option>
              <option v-for="d in destinations" :key="d.id" :value="d.id">{{ d.name }} ({{ d.type }})</option>
            </select>
          </div>
          <div class="col-span-2">
            <label :class="labelCls">Trigger</label>
            <div class="grid grid-cols-2 gap-2">
              <label v-for="t in TRIGGERS" :key="t.value"
                class="flex items-start gap-2 p-2.5 rounded-lg border cursor-pointer transition-colors"
                :class="ruleForm.trigger === t.value
                  ? 'border-blue-500/40 bg-blue-500/5 text-blue-600 dark:text-blue-400'
                  : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:border-gray-300 dark:hover:border-gray-600'">
                <input type="radio" :value="t.value" v-model="ruleForm.trigger" class="mt-0.5 accent-blue-500" />
                <div>
                  <div class="text-xs font-medium">{{ t.label }}</div>
                  <div class="text-xs opacity-60">{{ t.desc }}</div>
                </div>
              </label>
            </div>
          </div>

          <!-- Monitor status change filters -->
          <template v-if="ruleForm.trigger === 'monitor_status_change'">
            <div>
              <label :class="labelCls">From status <span class="opacity-50">(any = leave empty)</span></label>
              <select v-model="ruleForm.filter_from_status" :class="inputCls">
                <option v-for="s in STATUS_VALUES" :key="s" :value="s">{{ STATUS_LABELS[s] }}</option>
              </select>
            </div>
            <div>
              <label :class="labelCls">To status <span class="opacity-50">(any = leave empty)</span></label>
              <select v-model="ruleForm.filter_to_status" :class="inputCls">
                <option v-for="s in STATUS_VALUES" :key="s" :value="s">{{ STATUS_LABELS[s] }}</option>
              </select>
            </div>
          </template>

          <!-- Service filter -->
          <div class="col-span-2">
            <label :class="labelCls">Limit to services <span class="opacity-50">(none = all services)</span></label>
            <div class="flex flex-wrap gap-x-4 gap-y-2 p-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg min-h-[40px]">
              <span v-if="!services.length" class="text-xs text-gray-400">No services found.</span>
              <label v-for="s in services" :key="s.id" class="flex items-center gap-1.5 cursor-pointer select-none text-xs text-gray-700 dark:text-gray-300">
                <input type="checkbox" :checked="ruleForm.service_ids.includes(s.id)" @change="toggleSvc(s.id)" class="w-3.5 h-3.5 rounded accent-blue-500" />
                {{ svcLabel(s) }}
              </label>
            </div>
          </div>

          <div class="col-span-2">
            <label class="flex items-center gap-2 cursor-pointer select-none">
              <input type="checkbox" v-model="ruleForm.active" class="w-4 h-4 rounded accent-blue-500" />
              <span class="text-xs text-gray-700 dark:text-gray-300">Active</span>
            </label>
          </div>
        </div>
        <div v-if="formError" class="text-red-500 text-xs mt-3">{{ formError }}</div>
        <div class="flex gap-2 mt-4">
          <button @click="saveRule" class="bg-blue-600 hover:bg-blue-500 text-white text-xs px-4 py-1.5 rounded-lg transition-colors">Save</button>
          <button @click="closeRuleForm" class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 text-xs px-3 py-1.5 transition-colors">Cancel</button>
        </div>
      </div>

      <!-- Rules list -->
      <div v-if="rules.length" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden shadow-sm dark:shadow-none">
        <div v-for="(r, i) in rules" :key="r.id"
          class="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800 last:border-0"
          :class="!r.active ? 'opacity-50' : ''">
          <div class="flex items-start gap-3 min-w-0">
            <div class="mt-0.5 w-7 h-7 rounded-full flex items-center justify-center shrink-0 border"
              :class="r.active ? 'bg-blue-500/10 border-blue-500/20 text-blue-500' : 'bg-gray-100 dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-400'">
              <Bell class="w-3.5 h-3.5" :stroke-width="1.75" />
            </div>
            <div class="min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-sm font-medium text-gray-800 dark:text-gray-200">{{ r.name }}</span>
                <span v-if="!r.active" class="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-400">disabled</span>
              </div>
              <div class="flex items-center gap-2 mt-0.5 flex-wrap">
                <span class="text-xs px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">{{ triggerLabel(r.trigger) }}</span>
                <span v-if="r.destination" class="text-xs text-gray-400 dark:text-gray-500">→ {{ r.destination.name }}</span>
                <template v-if="r.trigger === 'monitor_status_change'">
                  <span v-if="r.filter_from_status || r.filter_to_status" class="text-xs text-gray-400 dark:text-gray-500">
                    {{ r.filter_from_status || 'any' }} → {{ r.filter_to_status || 'any' }}
                  </span>
                </template>
                <span v-if="r.services && r.services.length" class="text-xs text-gray-400 dark:text-gray-500">
                  {{ r.services.map(s=>s.name).join(', ') }}
                </span>
              </div>
            </div>
          </div>
          <div class="flex items-center gap-2 ml-4 shrink-0">
            <button @click="openRuleForm(r)" class="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors">
              <Pencil class="w-3.5 h-3.5" :stroke-width="1.75" />
            </button>
            <button @click="deleteRule(r.id)" class="text-gray-300 hover:text-red-500 dark:text-gray-600 dark:hover:text-red-400 transition-colors">
              <Trash2 class="w-3.5 h-3.5" :stroke-width="1.75" />
            </button>
          </div>
        </div>
      </div>
      <div v-else-if="!showRuleForm" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl px-4 py-12 text-center shadow-sm dark:shadow-none">
        <Bell class="w-8 h-8 text-gray-300 dark:text-gray-700 mx-auto mb-2" :stroke-width="1.5" />
        <p class="text-gray-400 dark:text-gray-600 text-sm">No notification rules yet.</p>
      </div>
    </template>

    <!-- ══ DESTINATIONS TAB ═══════════════════════════════════════════════════ -->
    <template v-if="tab === 'destinations'">
      <div class="flex justify-end mb-4">
        <button @click="openDestForm(null)"
          class="bg-gray-800 hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 text-white text-xs px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5">
          <Plus class="w-3.5 h-3.5" :stroke-width="2" /> Add Destination
        </button>
      </div>

      <!-- Destination form -->
      <div v-if="showDestForm" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5 mb-6 shadow-sm dark:shadow-none">
        <h2 class="text-sm font-semibold text-gray-900 dark:text-white mb-4">{{ editDestId ? 'Edit Destination' : 'New Destination' }}</h2>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label :class="labelCls">Name</label>
            <input v-model="destForm.name" type="text" placeholder="e.g. Slack Alerts" :class="inputCls" />
          </div>
          <div>
            <label :class="labelCls">Type</label>
            <div class="flex gap-2">
              <label class="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg border cursor-pointer text-xs font-medium transition-colors"
                :class="destForm.type === 'webhook'
                  ? 'border-blue-500/40 bg-blue-500/5 text-blue-600 dark:text-blue-400'
                  : 'border-gray-200 dark:border-gray-700 text-gray-500 hover:border-gray-300 dark:hover:border-gray-600'">
                <input type="radio" value="webhook" v-model="destForm.type" class="sr-only" />
                <Webhook class="w-3.5 h-3.5" :stroke-width="1.75" /> Webhook
              </label>
              <label class="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg border cursor-pointer text-xs font-medium transition-colors"
                :class="destForm.type === 'email'
                  ? 'border-blue-500/40 bg-blue-500/5 text-blue-600 dark:text-blue-400'
                  : 'border-gray-200 dark:border-gray-700 text-gray-500 hover:border-gray-300 dark:hover:border-gray-600'">
                <input type="radio" value="email" v-model="destForm.type" class="sr-only" />
                <Mail class="w-3.5 h-3.5" :stroke-width="1.75" /> Email
              </label>
            </div>
          </div>

          <!-- Webhook fields -->
          <template v-if="destForm.type === 'webhook'">
            <div class="col-span-2 grid grid-cols-4 gap-3">
              <div>
                <label :class="labelCls">Method</label>
                <select v-model="destForm.method" :class="inputCls">
                  <option>POST</option><option>PUT</option><option>PATCH</option><option>GET</option>
                </select>
              </div>
              <div class="col-span-3">
                <label :class="labelCls">URL</label>
                <input v-model="destForm.url" type="url" placeholder="https://hooks.example.com/…" :class="inputCls" />
              </div>
            </div>
            <div class="col-span-2">
              <label :class="labelCls">Headers <span class="opacity-50">(JSON object)</span></label>
              <textarea v-model="destForm.headers" rows="3" :class="inputCls" class="resize-none font-mono text-xs" placeholder='{"Authorization": "Bearer …"}' />
            </div>
            <div class="col-span-2">
              <label :class="labelCls">Body template <span class="opacity-50">(JSON with <code class="font-mono">&#123;&#123;variable&#125;&#125;</code> placeholders)</span></label>
              <textarea v-model="destForm.body_template" rows="5" :class="inputCls" class="resize-none font-mono text-xs"
                placeholder='{"text": "{{service_name}} changed to {{status}}"}' />
            </div>
          </template>

          <!-- Email fields -->
          <template v-else>
            <div class="col-span-2">
              <label :class="labelCls">Recipient email</label>
              <input v-model="destForm.email_to" type="email" placeholder="alerts@example.com" :class="inputCls" />
            </div>
            <div class="col-span-2">
              <label :class="labelCls">Subject template</label>
              <input v-model="destForm.email_subject_template" type="text"
                placeholder="[MOSSBoard] {{title}} — {{service_name}}" :class="inputCls" />
            </div>
            <div class="col-span-2">
              <label :class="labelCls">Body template <span class="opacity-50">(<code class="font-mono text-xs">&#123;&#123;variable&#125;&#125;</code> placeholders)</span></label>
              <textarea v-model="destForm.email_body_template" rows="6" :class="inputCls" class="resize-none text-sm"
                placeholder="Service {{service_name}} changed from {{prev_status}} to {{status}} at {{timestamp}}." />
            </div>
          </template>

          <div class="col-span-2">
            <label class="flex items-center gap-2 cursor-pointer select-none">
              <input type="checkbox" v-model="destForm.active" class="w-4 h-4 rounded accent-blue-500" />
              <span class="text-xs text-gray-700 dark:text-gray-300">Active</span>
            </label>
          </div>
        </div>

        <div v-if="formError" class="text-red-500 text-xs mt-3">{{ formError }}</div>
        <div class="flex gap-2 mt-4">
          <button @click="saveDest" class="bg-blue-600 hover:bg-blue-500 text-white text-xs px-4 py-1.5 rounded-lg transition-colors">Save</button>
          <button @click="closeDestForm" class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 text-xs px-3 py-1.5 transition-colors">Cancel</button>
        </div>
      </div>

      <!-- Destinations list -->
      <div v-if="destinations.length" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden shadow-sm dark:shadow-none">
        <div v-for="d in destinations" :key="d.id"
          class="border-b border-gray-100 dark:border-gray-800 last:border-0"
          :class="!d.active ? 'opacity-50' : ''">
          <div class="flex items-center justify-between px-4 py-3">
            <div class="flex items-center gap-3 min-w-0">
              <div class="w-7 h-7 rounded-full flex items-center justify-center shrink-0 border"
                :class="d.type === 'webhook'
                  ? 'bg-purple-500/10 border-purple-500/20 text-purple-500'
                  : 'bg-green-500/10 border-green-500/20 text-green-500'">
                <Webhook v-if="d.type === 'webhook'" class="w-3.5 h-3.5" :stroke-width="1.75" />
                <Mail v-else class="w-3.5 h-3.5" :stroke-width="1.75" />
              </div>
              <div class="min-w-0">
                <div class="flex items-center gap-2">
                  <span class="text-sm font-medium text-gray-800 dark:text-gray-200">{{ d.name }}</span>
                  <span class="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400">{{ d.type }}</span>
                  <span v-if="!d.active" class="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-400">disabled</span>
                </div>
                <div class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                  <template v-if="d.type === 'webhook'">{{ d.method }} {{ d.url }}</template>
                  <template v-else>→ {{ d.email_to }}</template>
                </div>
              </div>
            </div>
            <div class="flex items-center gap-2 ml-4 shrink-0">
              <!-- Test result badge -->
              <span v-if="testResult[d.id] === 'queued'" class="text-xs text-green-500">queued ✓</span>
              <span v-else-if="testResult[d.id] === 'error'" class="text-xs text-red-500">error ✗</span>
              <button @click="testDest(d.id)" :disabled="testingId === d.id"
                class="flex items-center gap-1 text-xs text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 transition-colors disabled:opacity-50">
                <Play class="w-3 h-3" :stroke-width="1.75" /> Test
              </button>
              <button @click="openDestForm(d)" class="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors">
                <Pencil class="w-3.5 h-3.5" :stroke-width="1.75" />
              </button>
              <button @click="deleteDest(d.id)" class="text-gray-300 hover:text-red-500 dark:text-gray-600 dark:hover:text-red-400 transition-colors">
                <Trash2 class="w-3.5 h-3.5" :stroke-width="1.75" />
              </button>
            </div>
          </div>
        </div>
      </div>
      <div v-else-if="!showDestForm" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl px-4 py-12 text-center shadow-sm dark:shadow-none">
        <Bell class="w-8 h-8 text-gray-300 dark:text-gray-700 mx-auto mb-2" :stroke-width="1.5" />
        <p class="text-gray-400 dark:text-gray-600 text-sm">No destinations configured yet.</p>
      </div>

      <!-- Variable reference -->
      <div class="mt-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 shadow-sm dark:shadow-none">
        <div class="flex items-center gap-1.5 mb-3">
          <Info class="w-3.5 h-3.5 text-gray-400" :stroke-width="1.75" />
          <span class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Available template variables</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-xs">
            <thead>
              <tr class="text-left text-gray-400 dark:text-gray-500 border-b border-gray-100 dark:border-gray-800">
                <th class="pr-4 pb-2 font-medium">Variable</th>
                <th class="pr-4 pb-2 font-medium">Description</th>
                <th class="pb-2 font-medium">Available for</th>
              </tr>
            </thead>
            <tbody class="text-gray-600 dark:text-gray-400">
              <tr v-for="row in [
                ['service_name','Name of the affected service','incidents, monitors, maintenance'],
                ['service_slug','URL slug of the service','incidents, monitors'],
                ['section_name','Section the service belongs to','incidents, monitors'],
                ['status','New / current status','incidents, monitors'],
                ['prev_status','Previous status (before change)','monitor_status_change'],
                ['title','Incident or maintenance title','incidents, maintenance'],
                ['description','Maintenance description','maintenance'],
                ['starts_at','Maintenance window start (ISO 8601)','maintenance'],
                ['ends_at','Maintenance window end (ISO 8601)','maintenance'],
                ['message','Incident update message','incidents'],
                ['monitor_name','Name of the monitor','monitor_status_change'],
                ['recurrence','Recurrence type (none/daily/weekly/monthly)','maintenance_created'],
                ['timestamp','UTC timestamp of the event','all'],
              ]" :key="row[0]" class="border-b border-gray-50 dark:border-gray-800/50 last:border-0">
                <td class="pr-4 py-1.5 font-mono text-blue-600 dark:text-blue-400">&#123;&#123;{{ row[0] }}&#125;&#125;</td>
                <td class="pr-4 py-1.5">{{ row[1] }}</td>
                <td class="py-1.5 text-gray-400 dark:text-gray-500">{{ row[2] }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <!-- ══ SMTP TAB ═══════════════════════════════════════════════════════════ -->
    <template v-if="tab === 'smtp'">
      <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5 shadow-sm dark:shadow-none max-w-xl">
        <div class="flex items-center gap-2 mb-4">
          <Settings2 class="w-4 h-4 text-gray-400" :stroke-width="1.75" />
          <h2 class="text-sm font-semibold text-gray-900 dark:text-white">SMTP Configuration</h2>
        </div>
        <p class="text-xs text-gray-400 dark:text-gray-500 mb-4">Configure an outgoing mail server to send email notifications. Leave blank to disable email delivery.</p>

        <div class="space-y-3">
          <div class="grid grid-cols-3 gap-3">
            <div class="col-span-2">
              <label :class="labelCls">SMTP Host</label>
              <input v-model="smtp.smtp_host" type="text" placeholder="smtp.example.com" :class="inputCls" />
            </div>
            <div>
              <label :class="labelCls">Port</label>
              <input v-model.number="smtp.smtp_port" type="number" placeholder="587" :class="inputCls" />
            </div>
          </div>
          <div>
            <label :class="labelCls">Username</label>
            <input v-model="smtp.smtp_username" type="text" placeholder="user@example.com" :class="inputCls" />
          </div>
          <div>
            <label :class="labelCls">Password <span class="opacity-50">(leave blank to keep current)</span></label>
            <input v-model="smtpPassword" type="password" placeholder="••••••••" :class="inputCls" />
          </div>
          <div>
            <label :class="labelCls">From address <span class="opacity-50">(optional)</span></label>
            <input v-model="smtp.smtp_from" type="email" placeholder="mossboard@example.com" :class="inputCls" />
          </div>
          <div>
            <label class="flex items-center gap-2 cursor-pointer select-none">
              <input type="checkbox" v-model="smtp.smtp_use_tls" class="w-4 h-4 rounded accent-blue-500" />
              <span class="text-xs text-gray-700 dark:text-gray-300">Use STARTTLS (port 587). Uncheck for SMTP_SSL (port 465) or plain SMTP.</span>
            </label>
          </div>
        </div>

        <div class="flex items-center gap-3 mt-5">
          <button @click="saveSMTP" class="bg-blue-600 hover:bg-blue-500 text-white text-xs px-4 py-1.5 rounded-lg transition-colors">Save SMTP</button>
          <span v-if="smtpSaved" class="text-xs text-green-500">Saved ✓</span>
        </div>
      </div>
    </template>
  </div>
</template>
