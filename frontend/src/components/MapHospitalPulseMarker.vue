<script setup>
defineProps({
  label: { type: String, default: 'SGHL — Dolisie' },
})
</script>

<template>
  <div
    class="map-hospital-marker pointer-events-none select-none"
    role="img"
    :aria-label="`Localisation exacte : ${label}`"
  >
    <!-- Halo lumineux sur la carte -->
    <div class="marker-spotlight" aria-hidden="true" />

    <!-- Ondes pulsantes (effet radar / GPS) -->
    <div class="marker-rings" aria-hidden="true">
      <span class="marker-ring marker-ring-1" />
      <span class="marker-ring marker-ring-2" />
      <span class="marker-ring marker-ring-3" />
    </div>

    <!-- Point lumineux central clignotant -->
    <div class="marker-beacon" aria-hidden="true">
      <span class="marker-beacon-core" />
      <span class="marker-beacon-glow" />
    </div>

    <!-- Épingle professionnelle type Google Maps -->
    <div class="marker-pin" aria-hidden="true">
      <svg viewBox="0 0 36 48" class="marker-pin-svg" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <filter id="pin-shadow" x="-20%" y="-10%" width="140%" height="130%">
            <feDropShadow dx="0" dy="2" stdDeviation="2" flood-opacity="0.35" />
          </filter>
        </defs>
        <path
          d="M18 0C9.716 0 3 6.716 3 15c0 10.5 15 33 15 33s15-22.5 15-33C33 6.716 26.284 0 18 0z"
          fill="#DC2626"
          filter="url(#pin-shadow)"
        />
        <circle cx="18" cy="15" r="9" fill="white" />
        <path
          d="M18 10v10M13 15h10"
          stroke="#DC2626"
          stroke-width="2.2"
          stroke-linecap="round"
        />
      </svg>
    </div>

    <!-- Étiquette -->
    <div class="marker-label">
      <span class="marker-label-dot" aria-hidden="true" />
      <span class="marker-label-text">{{ label }}</span>
    </div>
  </div>
</template>

<style scoped>
.map-hospital-marker {
  position: relative;
  width: 160px;
  height: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.marker-spotlight {
  position: absolute;
  width: 200px;
  height: 200px;
  border-radius: 50%;
  background: radial-gradient(
    circle,
    rgba(239, 68, 68, 0.35) 0%,
    rgba(251, 191, 36, 0.15) 35%,
    transparent 70%
  );
  animation: spotlight-pulse 2.4s ease-in-out infinite;
}

.marker-rings {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.marker-ring {
  position: absolute;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: 3px solid rgba(239, 68, 68, 0.75);
  box-shadow: 0 0 12px rgba(239, 68, 68, 0.5);
}

.marker-ring-1 {
  animation: ring-expand 2.4s ease-out infinite;
}

.marker-ring-2 {
  animation: ring-expand 2.4s ease-out infinite 0.8s;
}

.marker-ring-3 {
  animation: ring-expand 2.4s ease-out infinite 1.6s;
}

.marker-beacon {
  position: absolute;
  bottom: 52px;
  left: 50%;
  transform: translateX(-50%);
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.marker-beacon-core {
  position: absolute;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #fef08a;
  box-shadow:
    0 0 8px 3px rgba(254, 240, 138, 1),
    0 0 20px 8px rgba(239, 68, 68, 0.9),
    0 0 40px 16px rgba(239, 68, 68, 0.4);
  animation: beacon-blink 1.2s ease-in-out infinite;
  z-index: 2;
}

.marker-beacon-glow {
  position: absolute;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(239, 68, 68, 0.45);
  animation: beacon-glow 1.2s ease-in-out infinite;
  z-index: 1;
}

.marker-pin {
  position: absolute;
  bottom: 28px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 3;
}

.marker-pin-svg {
  width: 42px;
  height: 56px;
  display: block;
  animation: pin-bounce 2.4s ease-in-out infinite;
}

.marker-label {
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  background: rgba(15, 23, 42, 0.88);
  color: white;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.02em;
  padding: 6px 12px;
  border-radius: 999px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.15);
  z-index: 4;
}

.marker-label-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #fef08a;
  box-shadow: 0 0 8px 2px rgba(254, 240, 138, 0.9);
  animation: beacon-blink 1.2s ease-in-out infinite;
}

.marker-label-text {
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
}

@keyframes ring-expand {
  0% {
    transform: scale(0.4);
    opacity: 0.9;
  }
  100% {
    transform: scale(2.8);
    opacity: 0;
  }
}

@keyframes beacon-blink {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.65;
    transform: scale(1.15);
  }
}

@keyframes beacon-glow {
  0%,
  100% {
    opacity: 0.6;
    transform: scale(1);
  }
  50% {
    opacity: 1;
    transform: scale(1.35);
  }
}

@keyframes spotlight-pulse {
  0%,
  100% {
    opacity: 0.75;
    transform: scale(1);
  }
  50% {
    opacity: 1;
    transform: scale(1.12);
  }
}

@keyframes pin-bounce {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-4px);
  }
}
</style>
