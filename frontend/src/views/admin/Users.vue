<script setup>
import { ref, onMounted } from 'vue';
import { ShieldCheck, Eye, EyeOff, UserCheck, UserX } from 'lucide-vue-next';

const users = ref([]);
const showForm = ref(false);
const error = ref('');
const serverError = ref('');
const form = ref({ username: '', password: '', role: 'admin' });
const showPw = ref(false);

// Password reset state
const resetId = ref(null);
const resetPw = ref('');
const resetError = ref('');

const inputCls = 'w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none';

async function fetchUsers() {
  const res = await fetch('/api/v1/admin/users');
  if (res.ok) users.value = (await res.json()).users;
}

async function createUser() {
  error.value = '';
  serverError.value = '';
  if (!form.value.username || !form.value.password) { error.value = 'Username and password required.'; return; }
  const res = await fetch('/api/v1/admin/users', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form.value),
  });
  if (res.ok) { showForm.value = false; form.value = { username: '', password: '', role: 'admin' }; await fetchUsers(); }
  else { const d = await res.json(); serverError.value = d.error || 'Failed to create user.'; }
}

async function toggleActive(user) {
  await fetch(`/api/v1/admin/users/${user.id}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ active: !user.active }),
  });
  await fetchUsers();
}

async function changeRole(user, role) {
  await fetch(`/api/v1/admin/users/${user.id}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ role }),
  });
  await fetchUsers();
}

async function submitReset(userId) {
  resetError.value = '';
  if (!resetPw.value) { resetError.value = 'Password required.'; return; }
  const res = await fetch(`/api/v1/admin/users/${userId}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password: resetPw.value }),
  });
  if (res.ok) { resetId.value = null; resetPw.value = ''; await fetchUsers(); }
  else { resetError.value = 'Failed.'; }
}

async function deleteUser(id) {
  if (!confirm('Delete this user?')) return;
  const res = await fetch(`/api/v1/admin/users/${id}`, { method: 'DELETE' });
  if (res.ok) { await fetchUsers(); }
  else { const d = await res.json(); alert(d.error || 'Failed to delete.'); }
}

function formatDate(iso) {
  if (!iso) return 'Never';
  return new Date(iso).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

onMounted(fetchUsers);
</script>

<template>
  <div class="p-8">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-lg font-bold text-gray-900 dark:text-white">Users</h1>
      <button @click="showForm = !showForm; serverError = ''" class="bg-gray-800 hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 text-white text-xs px-3 py-1.5 rounded-lg transition-colors">
        + New User
      </button>
    </div>

    <!-- Create form -->
    <div v-if="showForm" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5 mb-6 shadow-sm dark:shadow-none">
      <h2 class="text-sm font-semibold text-gray-900 dark:text-white mb-4">New User</h2>
      <div class="space-y-3">
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Username</label>
          <input v-model="form.username" type="text" autocomplete="off" :class="inputCls" />
        </div>
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Password</label>
          <div class="relative">
            <input v-model="form.password" :type="showPw ? 'text' : 'password'" autocomplete="new-password" :class="inputCls" class="pr-9" />
            <button type="button" @click="showPw = !showPw" class="absolute right-2.5 top-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
              <component :is="showPw ? EyeOff : Eye" :size="14" :stroke-width="1.75" />
            </button>
          </div>
        </div>
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Role</label>
          <select v-model="form.role" :class="inputCls">
            <option value="admin">Admin</option>
            <option value="viewer">Viewer</option>
          </select>
        </div>
        <div v-if="error" class="text-red-500 dark:text-red-400 text-xs">{{ error }}</div>
        <div v-if="serverError" class="text-red-500 dark:text-red-400 text-xs">{{ serverError }}</div>
        <div class="flex gap-2">
          <button @click="createUser" class="bg-gray-800 hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 text-white text-xs px-4 py-1.5 rounded-lg transition-colors">Create</button>
          <button @click="showForm = false; error = ''" class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 text-xs px-3 py-1.5 transition-colors">Cancel</button>
        </div>
      </div>
    </div>

    <!-- User list -->
    <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden shadow-sm dark:shadow-none">
      <div v-for="user in users" :key="user.id">
        <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800 last:border-0"
          :class="!user.active ? 'opacity-50' : ''">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-xs font-bold text-gray-500 dark:text-gray-400 uppercase">
              {{ user.username[0] }}
            </div>
            <div>
              <div class="flex items-center gap-2">
                <span class="text-sm font-medium text-gray-800 dark:text-gray-200">{{ user.username }}</span>
                <span
                  class="text-xs px-1.5 py-0.5 rounded border"
                  :class="user.role === 'admin'
                    ? 'bg-purple-500/10 border-purple-500/30 text-purple-600 dark:text-purple-400'
                    : 'bg-gray-100 dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-500'"
                >
                  {{ user.role }}
                </span>
                <ShieldCheck v-if="user.role === 'admin'" class="w-3.5 h-3.5 text-purple-400" :stroke-width="1.75" />
              </div>
              <div class="text-xs text-gray-400 dark:text-gray-600 mt-0.5">
                Last login: {{ formatDate(user.last_login) }}
              </div>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <button
              @click="changeRole(user, user.role === 'admin' ? 'viewer' : 'admin')"
              class="text-xs text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
              :title="`Switch to ${user.role === 'admin' ? 'viewer' : 'admin'}`"
            >
              {{ user.role === 'admin' ? '→ viewer' : '→ admin' }}
            </button>
            <button @click="resetId = user.id; resetPw = ''; resetError = ''" class="text-xs text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors">
              Reset pw
            </button>
            <button @click="toggleActive(user)" class="text-xs transition-colors" :class="user.active ? 'text-orange-400 hover:text-orange-600 dark:hover:text-orange-300' : 'text-green-500 hover:text-green-700 dark:hover:text-green-300'">
              {{ user.active ? 'Disable' : 'Enable' }}
            </button>
            <button @click="deleteUser(user.id)" class="text-xs text-red-400 hover:text-red-600 dark:hover:text-red-300 transition-colors">Delete</button>
          </div>
        </div>

        <!-- Password reset inline -->
        <div v-if="resetId === user.id" class="px-4 py-3 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-100 dark:border-gray-800 flex items-center gap-2">
          <input v-model="resetPw" type="password" placeholder="New password" class="flex-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 text-xs text-gray-900 dark:text-white focus:outline-none" />
          <button @click="submitReset(user.id)" class="bg-gray-800 hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 text-white text-xs px-3 py-1.5 rounded-lg transition-colors">Save</button>
          <button @click="resetId = null" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-xs px-2">Cancel</button>
          <span v-if="resetError" class="text-red-500 dark:text-red-400 text-xs">{{ resetError }}</span>
        </div>
      </div>
      <div v-if="!users.length" class="px-4 py-8 text-center text-gray-400 dark:text-gray-600 text-sm">No users yet. The env-var admin always works as a fallback.</div>
    </div>
  </div>
</template>
