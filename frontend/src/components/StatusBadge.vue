<script setup>
import { CheckCircle, Clock, AlertTriangle, XCircle, Wrench, HelpCircle, Search, Crosshair, Eye } from 'lucide-vue-next';

defineProps({ status: String });

const labels = {
  // service statuses
  operational:        'Operational',
  performance_issues: 'Performance Issues',
  partial_outage:     'Partial Outage',
  major_outage:       'Major Outage',
  under_maintenance:  'Under Maintenance',
  unknown:            'Unknown',
  // incident statuses
  investigating: 'Investigating',
  identified:    'Identified',
  monitoring:    'Monitoring',
  resolved:      'Resolved',
};

const icons = {
  operational:        CheckCircle,
  performance_issues: Clock,
  partial_outage:     AlertTriangle,
  major_outage:       XCircle,
  under_maintenance:  Wrench,
  unknown:            HelpCircle,
  investigating:      Search,
  identified:         Crosshair,
  monitoring:         Eye,
  resolved:           CheckCircle,
};

const classes = {
  operational:        'bg-green-500/15 text-green-600 dark:text-green-400 border-green-500/30',
  performance_issues: 'bg-yellow-400/15 text-yellow-600 dark:text-yellow-300 border-yellow-400/30',
  partial_outage:     'bg-orange-500/15 text-orange-600 dark:text-orange-400 border-orange-500/30',
  major_outage:       'bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/30',
  under_maintenance:  'bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-500/30',
  unknown:            'bg-gray-400/15 text-gray-600 dark:text-gray-400 border-gray-400/30',
  investigating:      'bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/30',
  identified:         'bg-orange-500/15 text-orange-600 dark:text-orange-400 border-orange-500/30',
  monitoring:         'bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-500/30',
  resolved:           'bg-green-500/15 text-green-600 dark:text-green-400 border-green-500/30',
};
</script>

<template>
  <span
    class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border"
    :class="classes[status] || classes.unknown"
  >
    <component :is="icons[status] || HelpCircle" :size="11" :stroke-width="2" />
    {{ labels[status] || status }}
  </span>
</template>
