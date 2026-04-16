<script setup>
import { ref, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { LayoutGrid, Layers, Server, Bell, Calendar, Key, Users, LogOut, ExternalLink, BookOpen, Activity, Settings } from 'lucide-vue-next';
import ThemeToggle from '../../components/ThemeToggle.vue';

const router = useRouter();
const route = useRoute();
const authenticated = ref(false);
const checking = ref(true);
const loginForm = ref({ username: '', password: '' });
const loginError = ref('');

async function checkAuth() {
  try {
    const res = await fetch('/api/v1/admin/me');
    const data = await res.json();
    authenticated.value = data.authenticated;
  } finally { checking.value = false; }
}

async function login() {
  loginError.value = '';
  try {
    const res = await fetch('/api/v1/admin/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(loginForm.value),
    });
    if (res.ok) { authenticated.value = true; }
    else { loginError.value = 'Invalid username or password.'; }
  } catch { loginError.value = 'Connection error.'; }
}

async function logout() {
  await fetch('/api/v1/admin/logout', { method: 'POST' });
  authenticated.value = false;
}

onMounted(checkAuth);

const nav = [
  { label: 'Dashboard',   path: '/admin',             icon: LayoutGrid },
  { label: 'Sections',    path: '/admin/sections',    icon: Layers     },
  { label: 'Services',    path: '/admin/services',    icon: Server     },
  { label: 'Incidents',   path: '/admin/incidents',   icon: Bell       },
  { label: 'Maintenance', path: '/admin/maintenance', icon: Calendar   },
  { label: 'Monitors',    path: '/admin/monitors',    icon: Activity   },
  { label: 'API Tokens',  path: '/admin/tokens',      icon: Key        },
  { label: 'Users',       path: '/admin/users',       icon: Users      },
  { label: 'Settings',    path: '/admin/settings',    icon: Settings   },
];
</script>

<template>
  <!-- Loading -->
  <div v-if="checking" class="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center">
    <div class="text-gray-400 text-sm">Loading…</div>
  </div>

  <!-- Login -->
  <div v-else-if="!authenticated" class="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center transition-colors">
    <div class="w-full max-w-sm">
      <div class="text-center mb-8">
        <div class="inline-flex p-3 rounded-2xl bg-gray-100 dark:bg-gray-800 mb-4">
          <Server class="w-7 h-7 text-gray-500 dark:text-gray-400" :stroke-width="1.5" />
        </div>
        <h1 class="text-xl font-bold text-gray-900 dark:text-white">Admin Login</h1>
      </div>
      <form @submit.prevent="login" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6 space-y-4 shadow-sm dark:shadow-none">
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Username</label>
          <input v-model="loginForm.username" type="text" autocomplete="username"
            class="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 transition-colors" />
        </div>
        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">Password</label>
          <input v-model="loginForm.password" type="password" autocomplete="current-password"
            class="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 transition-colors" />
        </div>
        <div v-if="loginError" class="text-red-500 dark:text-red-400 text-xs">{{ loginError }}</div>
        <button type="submit" class="w-full bg-gray-800 hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 text-white text-sm rounded-lg px-4 py-2 transition-colors">
          Sign in
        </button>
      </form>
    </div>
  </div>

  <!-- Admin shell -->
  <div v-else class="min-h-screen bg-gray-50 dark:bg-gray-950 flex transition-colors">
    <!-- Sidebar -->
    <aside class="w-56 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 flex flex-col shrink-0 shadow-sm dark:shadow-none">
      <div class="px-4 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center gap-2.5">
        <div class="p-1.5 rounded-lg bg-gray-100 dark:bg-gray-800">
          <Server class="w-4 h-4 text-gray-500 dark:text-gray-400" :stroke-width="1.75" />
        </div>
        <div>
          <span class="text-sm font-bold text-gray-900 dark:text-white">MOSSBoard</span>
          <span class="block text-xs text-gray-400 dark:text-gray-600">Admin</span>
        </div>
      </div>

      <nav class="flex-1 py-2">
        <router-link
          v-for="item in nav"
          :key="item.path"
          :to="item.path"
          class="flex items-center gap-2.5 px-3 py-2 mx-2 rounded-lg text-sm transition-colors"
          :class="(item.path === '/admin' ? route.path === '/admin' : route.path.startsWith(item.path))
            ? 'text-gray-900 dark:text-white bg-gray-100 dark:bg-gray-800'
            : 'text-gray-500 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800/50'"
        >
          <component :is="item.icon" class="w-4 h-4 shrink-0" :stroke-width="1.75" />
          {{ item.label }}
        </router-link>
      </nav>

      <div class="px-3 py-3 border-t border-gray-200 dark:border-gray-800 space-y-1">
        <ThemeToggle class="w-full justify-start px-2 py-1.5 rounded-lg text-sm gap-2 !text-gray-500 hover:!text-gray-700 dark:hover:!text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800/50 flex" />
        <a href="/" class="flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs text-gray-400 dark:text-gray-600 hover:text-gray-600 dark:hover:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
          <ExternalLink class="w-3.5 h-3.5" :stroke-width="1.75" /> Public page
        </a>
        <a href="/docs" target="_blank" class="flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs text-gray-400 dark:text-gray-600 hover:text-gray-600 dark:hover:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
          <BookOpen class="w-3.5 h-3.5" :stroke-width="1.75" /> API docs
        </a>
        <button @click="logout" class="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs text-gray-400 dark:text-gray-600 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/5 transition-colors">
          <LogOut class="w-3.5 h-3.5" :stroke-width="1.75" /> Sign out
        </button>
      </div>
    </aside>

    <main class="flex-1 overflow-auto">
      <router-view />
    </main>
  </div>
</template>
