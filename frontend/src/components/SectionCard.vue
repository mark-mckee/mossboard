<script setup>
import { ref, computed } from 'vue';
import { ChevronDown, ChevronRight, CheckCircle } from 'lucide-vue-next';
import ServiceRow from './ServiceRow.vue';

const props = defineProps({ section: Object });

const allOperational = computed(() =>
  props.section.services?.length > 0 &&
  props.section.services.every(s => s.status === 'operational')
);

const open = ref(!allOperational.value);
</script>

<template>
  <div class="bg-white dark:bg-gray-900 border rounded-lg overflow-hidden shadow-sm dark:shadow-none"
    :class="allOperational ? 'border-gray-200 dark:border-gray-800' : 'border-orange-400/30 dark:border-orange-400/20'">
    <button
      class="w-full flex items-center gap-2 px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800/40 transition-colors text-left"
      :class="open ? 'border-b border-gray-200 dark:border-gray-800' : ''"
      @click="open = !open"
    >
      <component
        :is="open ? ChevronDown : ChevronRight"
        class="w-4 h-4 shrink-0"
        :class="allOperational ? 'text-gray-400 dark:text-gray-600' : 'text-orange-400'"
        :stroke-width="1.75"
      />
      <h2 class="text-sm font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider flex-1">
        {{ section.name }}
      </h2>
      <!-- All operational hint when collapsed -->
      <span v-if="allOperational && !open" class="flex items-center gap-1.5 text-xs text-green-600 dark:text-green-500 font-normal normal-case tracking-normal">
        <CheckCircle class="w-3.5 h-3.5" :stroke-width="2" />
        All services operational
      </span>
    </button>

    <div v-show="open">
      <div v-if="section.services && section.services.length">
        <ServiceRow v-for="service in section.services" :key="service.id" :service="service" />
      </div>
      <div v-else class="px-4 py-6 text-center text-gray-400 dark:text-gray-600 text-sm">
        No services in this section.
      </div>
    </div>
  </div>
</template>
