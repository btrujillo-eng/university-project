<script setup>
import { ref } from 'vue'
import AdminCatalog from './AdminCatalog.vue'
import StoreOperations from './StoreOperations.vue'

defineProps({
  user: { type: Object, required: true },
  token: { type: String, required: true },
})
const emit = defineEmits(['logout'])
const section = ref('catalog')
const menuOpen = ref(false)
</script>

<template>
  <main class="role-dashboard admin-dashboard">
    <header class="admin-dashboard-header">
      <a class="admin-dashboard-brand" href="#" @click.prevent="section = 'catalog'; menuOpen = false" aria-label="Canasta Express">
        <span class="admin-dashboard-brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M12 20V9m0 0c-4.4 0-6.5-2.2-6.5-6 4.3 0 6.5 2.1 6.5 6Zm0 2c0-4.2 2.1-6.2 6.5-6.2 0 4.1-2.1 6.2-6.5 6.2Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </span>
        <span class="admin-dashboard-brand-copy">
          <strong>Canasta Express</strong>
          <small>Legumbrería &amp; Verdulería Online</small>
        </span>
      </a>

      <div class="admin-dashboard-account">
        <span>Hola, Administrador</span>
        <button
          type="button"
          class="admin-dashboard-menu-toggle"
          :aria-expanded="menuOpen"
          aria-label="Abrir menú de administración"
          @click="menuOpen = !menuOpen"
        >
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="m6 9 6 6 6-6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        <div v-if="menuOpen" class="admin-dashboard-menu">
          <button type="button" :class="{ active: section === 'catalog' }" @click="section = 'catalog'; menuOpen = false">Catálogo</button>
          <button type="button" :class="{ active: section === 'dispatch' }" @click="section = 'dispatch'; menuOpen = false">Asignación de pedidos</button>
          <button type="button" class="logout-option" @click="emit('logout')">Cerrar sesión</button>
        </div>
      </div>
    </header>

    <AdminCatalog
      v-if="section === 'catalog'"
      :user="user"
      :token="token"
      @logout="emit('logout')"
    />
    <StoreOperations
      v-else
      :user="user"
      :token="token"
      @logout="emit('logout')"
    />
  </main>
</template>
