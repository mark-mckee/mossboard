<script setup>
import { computed, getCurrentInstance } from 'vue';

const props = defineProps({
  points: { type: Array,  default: () => [] },
  height: { type: Number, default: 56 },
  color:  { type: String, default: '#6366f1' }, // indigo-500
});

// Unique gradient ID per component instance
const uid   = getCurrentInstance().uid;
const gradId = `mcg-${uid}`;

const W   = 400;
const PAD = { x: 2, y: 4 };

const coords = computed(() => {
  const pts = props.points;
  if (pts.length < 2) return [];
  const times = pts.map(p => new Date(p.timestamp).getTime());
  const vals  = pts.map(p => p.value);
  const minT  = Math.min(...times), maxT = Math.max(...times);
  const minV  = Math.min(...vals),  maxV = Math.max(...vals);
  const rangeT = maxT - minT || 1;
  const rangeV = maxV - minV || 1;
  const H = props.height;
  return pts.map(p => ({
    x: PAD.x + ((new Date(p.timestamp).getTime() - minT) / rangeT) * (W - PAD.x * 2),
    y: PAD.y + (1 - (p.value - minV) / rangeV) * (H - PAD.y * 2),
  }));
});

const linePath = computed(() => {
  const c = coords.value;
  if (!c.length) return '';
  return c.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');
});

const fillPath = computed(() => {
  const c = coords.value;
  if (!c.length) return '';
  const H = props.height;
  return `${linePath.value} L ${c[c.length - 1].x.toFixed(1)} ${H} L ${c[0].x.toFixed(1)} ${H} Z`;
});
</script>

<template>
  <div class="w-full" :style="`height:${height}px`">
    <svg
      v-if="points.length >= 2"
      :viewBox="`0 0 ${W} ${height}`"
      preserveAspectRatio="none"
      class="w-full h-full"
    >
      <defs>
        <linearGradient :id="gradId" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   :stop-color="color" stop-opacity="0.25" />
          <stop offset="100%" :stop-color="color" stop-opacity="0"    />
        </linearGradient>
      </defs>
      <path :d="fillPath" :fill="`url(#${gradId})`" />
      <path :d="linePath" fill="none" :stroke="color" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" />
    </svg>
    <div v-else class="flex items-center justify-center h-full text-xs text-gray-400 dark:text-gray-600 italic">
      No data
    </div>
  </div>
</template>
