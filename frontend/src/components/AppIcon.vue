<script setup>
import {
  CheckCircle, Clock, AlertTriangle, XCircle, Wrench, HelpCircle,
  Search, Crosshair, Eye, Check, ChevronDown, ChevronRight,
  Calendar, LayoutGrid, Layers, Server, Bell, Key,
  Users, Sun, Moon, ArrowLeft, Activity, ShieldAlert,
  Trash2, Pencil, Plus, LogOut, ExternalLink, RefreshCw,
  Info, AlertCircle, Timer, History,
} from 'lucide-vue-next';

const props = defineProps({
  name: { type: String, required: true },
  class: { type: String, default: 'w-4 h-4' },
});

const iconMap = {
  'check-circle':    CheckCircle,
  'clock-warning':   Clock,
  'exclamation-tri': AlertTriangle,
  'x-circle':        XCircle,
  'wrench':          Wrench,
  'question-circle': HelpCircle,
  'search':          Search,
  'target':          Crosshair,
  'eye':             Eye,
  'check':           Check,
  'chevron-down':    ChevronDown,
  'chevron-right':   ChevronRight,
  'calendar':        Calendar,
  'grid':            LayoutGrid,
  'layers':          Layers,
  'server':          Server,
  'bell':            Bell,
  'key':             Key,
  'clock':           Clock,
  'exclamation':     AlertTriangle,
  'users':           Users,
  'sun':             Sun,
  'moon':            Moon,
  'arrow-left':      ArrowLeft,
  'activity':        Activity,
  'shield-alert':    ShieldAlert,
  'trash':           Trash2,
  'pencil':          Pencil,
  'plus':            Plus,
  'logout':          LogOut,
  'external-link':   ExternalLink,
  'refresh':         RefreshCw,
  'info':            Info,
  'alert-circle':    AlertCircle,
  'timer':           Timer,
  'history':         History,
};
</script>

<template>
  <component
    :is="iconMap[name] || HelpCircle"
    :class="$props.class"
    :stroke-width="1.75"
  />
</template>
