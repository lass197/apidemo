<template>
  <div class="flex flex-col items-center justify-center py-24 px-4 text-center">
    <div class="text-8xl font-bold text-slate-200 mb-4 select-none" aria-hidden="true">404</div>
    <h1 class="text-2xl font-bold text-slate-800">Page introuvable</h1>
    <p class="text-slate-500 mt-2 max-w-md">
      La route demandée n'existe pas ou vous n'avez pas les permissions pour y accéder.
    </p>
    <router-link to="/dashboard" class="btn-primary mt-8">
      Retour au tableau de bord
    </router-link>
  </div>
</template>
