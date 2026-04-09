<script setup>
import { ref, onMounted } from 'vue';

const sections = ref([]);
const showForm = ref(false);
const form = ref({ name: '', order: 0, visible: true });
const editId = ref(null);
const error = ref('');

const inputCls = 'w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500';

async function fetchSections() {
  const res = await fetch('/api/v1/admin/sections');
  if (res.ok) sections.value = (await res.json()).sections;
}

function startCreate() { editId.value = null; form.value = { name: '', order: 0, visible: true }; showForm.value = true; }
function startEdit(s) { editId.value = s.id; form.value = { name: s.name, order: s.order, visible: s.visible }; showForm.value = true; }
function cancelForm() { showForm.value = false; error.value = ''; }

async function submitForm() {
  error.value = '';
  const url = editId.value ? `/api/v1/admin/sections/${editId.value}` : '/api/v1/admin/sections';
  const res = await fetch(url, { method: editId.value ? 'PATCH' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form.value) });
  if (res.ok) { showForm.value = false; await fetchSections(); }
  else { error.value = 'Failed to save.'; }
}

async function deleteSection(id) {
  if (!confirm('Delete this section? Services inside will also be deleted.')) return;
  await fetch(`/api/v1/admin/sections/${id}`, { method: 'DELETE' });
  await fetchSections();
}

onMounted(fetchSections);
</script>

<template>
  <div class="p-8">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-lg font-bold text-gray-900 dark:text-white">Sections</h1>
      <button @click="startCreate" class="bg-gray-800 hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 text-white text-xs px-3 py-1.5 rounded-lg transition-colors">
        + New Section
      </button>
    </div>

    <div v-if="showForm" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5 mb-6 shadow-sm dark:shadow-none">
      <h2 class="text-sm font-semibold text-gray-900 dark:text-white mb-4">{{ editId ? 'Edit Section' : 'New Section' }}</h2>
      <div class="space-y-3">
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Name</label>
          <input v-model="form.name" type="text" :class="inputCls" />
        </div>
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Order</label>
          <input v-model.number="form.order" type="number" :class="inputCls" class="w-28" />
        </div>
        <label class="flex items-center gap-2 cursor-pointer">
          <input v-model="form.visible" type="checkbox" class="rounded" />
          <span class="text-xs text-gray-500 dark:text-gray-400">Visible</span>
        </label>
        <div v-if="error" class="text-red-500 dark:text-red-400 text-xs">{{ error }}</div>
        <div class="flex gap-2 pt-1">
          <button @click="submitForm" class="bg-gray-800 hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 text-white text-xs px-4 py-1.5 rounded-lg transition-colors">Save</button>
          <button @click="cancelForm" class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 text-xs px-3 py-1.5 transition-colors">Cancel</button>
        </div>
      </div>
    </div>

    <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden shadow-sm dark:shadow-none">
      <div v-for="section in sections" :key="section.id"
        class="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800 last:border-0">
        <div>
          <span class="text-sm text-gray-800 dark:text-gray-200">{{ section.name }}</span>
          <span class="ml-2 text-xs text-gray-400 dark:text-gray-600">{{ section.slug }}</span>
          <span v-if="!section.visible" class="ml-2 text-xs text-gray-400 dark:text-gray-600">(hidden)</span>
        </div>
        <div class="flex gap-3">
          <button @click="startEdit(section)" class="text-xs text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors">Edit</button>
          <button @click="deleteSection(section.id)" class="text-xs text-red-400 hover:text-red-600 dark:hover:text-red-300 transition-colors">Delete</button>
        </div>
      </div>
      <div v-if="!sections.length" class="px-4 py-8 text-center text-gray-400 dark:text-gray-600 text-sm">No sections yet.</div>
    </div>
  </div>
</template>
