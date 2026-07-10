<script setup>
defineProps({
  size: { type: String, default: 'md' }, // sm | md | lg | xl
  variant: { type: String, default: 'default' }, // default | light | solid
})
</script>

<template>
  <span
    class="inline-flex shrink-0 items-center justify-center rounded-2xl"
    :class="{
      'h-8 w-8': size === 'sm',
      'h-11 w-11': size === 'md',
      'h-14 w-14': size === 'lg',
      'h-20 w-20 rounded-3xl': size === 'xl',
      'bg-teal-50 text-teal-700 ring-1 ring-teal-100': variant === 'default',
      'bg-white/20 text-white ring-1 ring-white/30 backdrop-blur-sm': variant === 'light',
      'bg-teal-600 text-white shadow-lg shadow-teal-600/30': variant === 'solid',
    }"
    role="img"
    aria-label="Hôpital"
  >
    <svg
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      :class="{
        'h-5 w-5': size === 'sm',
        'h-7 w-7': size === 'md',
        'h-9 w-9': size === 'lg',
        'h-12 w-12': size === 'xl',
      }"
      aria-hidden="true"
    >
      <!-- Bâtiment -->
      <path
        d="M8 42V18l16-10 16 10v24H8z"
        fill="currentColor"
        fill-opacity="0.15"
        stroke="currentColor"
        stroke-width="2"
        stroke-linejoin="round"
      />
      <!-- Croix médicale -->
      <path
        d="M24 14v8M20 18h8"
        stroke="currentColor"
        stroke-width="2.5"
        stroke-linecap="round"
      />
      <!-- Porte -->
      <path
        d="M20 42V30h8v12"
        stroke="currentColor"
        stroke-width="2"
        stroke-linejoin="round"
      />
      <!-- Fenêtres -->
      <rect x="13" y="24" width="5" height="5" rx="1" fill="currentColor" fill-opacity="0.35" />
      <rect x="30" y="24" width="5" height="5" rx="1" fill="currentColor" fill-opacity="0.35" />
    </svg>
  </span>
</template>
