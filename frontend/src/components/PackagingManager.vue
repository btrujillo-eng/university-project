<script setup>
import { computed, onMounted, ref } from 'vue'
import { getPackagingOrders, markOrderPackaged } from '../services/api'

const props = defineProps({ user: { type: Object, required: true }, token: { type: String, required: true } })
const emit = defineEmits(['logout'])
const orders = ref([])
const selected = ref(null)
const packedItemIds = ref([])
const returned = ref(false)
const loading = ref(false)
const busy = ref(false)
const error = ref('')
const success = ref('')
const displayName = [props.user.first_name, props.user.first_surname].filter(Boolean).join(' ') || 'Encargado de empaque'
const items = computed(() => Array.isArray(selected.value?.items) ? selected.value.items : [])
const itemKey = (item, index) => item.product_id ?? item.id ?? index
const allItemsPacked = computed(() => items.value.length > 0 && items.value.every((item, index) => packedItemIds.value.includes(itemKey(item, index))))
const money = value => new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(Number(value || 0))
const dateLabel = value => {
  const date = new Date(value)
  const parts = new Intl.DateTimeFormat('es-CO', { day: '2-digit', month: 'short', year: 'numeric' }).formatToParts(date)
  const part = type => parts.find(item => item.type === type)?.value ?? ''
  return `${part('day')} / ${part('month').replace('.', '')} / ${part('year')}`
}
function openOrderItems(order) {
  selected.value = order
  packedItemIds.value = []
  error.value = ''
}
function closeOrderItems() {
  if (!busy.value) {
    selected.value = null
    packedItemIds.value = []
    error.value = ''
  }
}
function toggleItem(item, index, checked) {
  const key = itemKey(item, index)
  packedItemIds.value = checked
    ? [...new Set([...packedItemIds.value, key])]
    : packedItemIds.value.filter(id => id !== key)
}
function toggleAllItems(checked) {
  packedItemIds.value = checked ? items.value.map(itemKey) : []
}
async function loadOrders() {
  loading.value = true
  error.value = ''
  success.value = ''
  selected.value = null
  packedItemIds.value = []
  try { orders.value = await getPackagingOrders(props.token, returned.value) }
  catch (e) { error.value = e.message || 'No fue posible consultar los pedidos.' }
  finally { loading.value = false }
}
async function packageOrder(order) {
  if (!allItemsPacked.value) {
    error.value = 'Debes marcar todos los productos como empacados antes de confirmar.'
    return
  }
  busy.value = true
  error.value = ''
  success.value = ''
  try {
    await markOrderPackaged(order.id, props.token)
    selected.value = null
    packedItemIds.value = []
    success.value = `El pedido #${order.id} quedó marcado como empacado.`
    await loadOrders()
  } catch (e) {
    error.value = e.message || 'No fue posible actualizar el pedido.'
  } finally {
    busy.value = false
  }
}
onMounted(loadOrders)
</script>

<template>
  <main class="operations-shell packaging-mockup-shell">
    <header class="operations-header packaging-mockup-header">
      <a class="customer-brand" href="#" @click.prevent="loadOrders">
        <span class="customer-brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none"><path d="M12 20V9m0 0c-4.4 0-6.5-2.2-6.5-6 4.3 0 6.5 2.1 6.5 6Zm0 2c0-4.2 2.1-6.2 6.5-6.2 0 4.1-2.1 6.2-6.5 6.2Z" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </span>
        <span><strong>Canasta Express</strong><small>Legumbrería &amp; Verdulería Online</small></span>
      </a>
      <div class="packaging-account">
        <span class="packaging-account-avatar" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="8" r="4" stroke="currentColor" stroke-width="1.4"/><path d="M4.5 20c.8-3.5 3.3-5.3 7.5-5.3s6.7 1.8 7.5 5.3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>
        </span>
        <span>Hola {{ displayName }}</span>
        <button type="button" @click="emit('logout')">Salir</button>
      </div>
    </header>

    <section v-if="!selected" class="packaging-mockup-page">
      <h1>{{ returned ? 'PEDIDOS DEVUELTOS A BODEGA' : 'PEDIDOS PENDIENTES PARA EMPAQUE' }}</h1>
      <div class="packaging-table-panel">
        <div class="packaging-table-toolbar">
          <p class="packaging-count" v-if="!loading">Se encontraron {{ orders.length }} pedidos {{ returned ? 'devueltos' : 'pendientes' }}</p>
          <p class="packaging-count" v-else>Consultando pedidos…</p>
          <button class="packaging-switch-view" type="button" @click="returned = !returned; loadOrders()">
            {{ returned ? 'Ver pedidos pendientes' : 'Ver pedidos devueltos a bodega' }}
          </button>
        </div>
        <p v-if="error" class="operations-alert error">{{ error }}</p>
        <p v-if="success" class="operations-alert success">{{ success }}</p>
        <div v-if="loading" class="packaging-table-message">Cargando pedidos…</div>
        <div v-else-if="orders.length" class="packaging-table-scroll">
          <table class="packaging-table">
            <thead><tr><th>ID PEDIDO</th><th>FECHA EMISIÓN</th><th>ESTADO</th><th>ACCIONES</th></tr></thead>
            <tbody>
              <tr v-for="order in orders" :key="order.id">
                <td data-label="ID PEDIDO">{{ order.id }}</td>
                <td data-label="FECHA EMISIÓN">{{ dateLabel(order.created_at) }}</td>
                <td data-label="ESTADO">{{ returned ? 'Devuelto a bodega' : 'Pendiente' }}</td>
                <td data-label="ACCIONES"><button class="packaging-view-button" type="button" @click="openOrderItems(order)">Ver Ítems</button></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else-if="!loading" class="packaging-table-message">
          {{ returned ? 'No hay pedidos devueltos a bodega.' : 'No hay pedidos pendientes de empaque.' }}
        </div>
      </div>
    </section>

    <section v-else class="packaging-order-detail-page">
      <button class="packaging-back-button" type="button" @click="closeOrderItems" :disabled="busy">← Volver a pedidos</button>
      <h1>DETALLE DEL PEDIDO {{ selected.id }}</h1>
      <div class="packaging-checklist-panel">
        <table class="packaging-checklist">
          <thead>
            <tr>
              <th class="packaging-check-column">
                <label class="packaging-check-heading">
                  <input type="checkbox" :checked="allItemsPacked" :disabled="items.length === 0 || returned || busy" @change="toggleAllItems($event.target.checked)">
                  <span>EMPACADO</span>
                </label>
              </th>
              <th>PRODUCTO</th>
              <th>CANTIDAD</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in items" :key="itemKey(item, index)" :class="{ 'is-packed': packedItemIds.includes(itemKey(item, index)) }">
              <td class="packaging-check-column">
                <input
                  type="checkbox"
                  :aria-label="`Marcar ${item.product_name} como empacado`"
                  :checked="packedItemIds.includes(itemKey(item, index))"
                  :disabled="returned || busy"
                  @change="toggleItem(item, index, $event.target.checked)"
                >
              </td>
              <td>{{ item.product_name }}</td>
              <td>{{ item.quantity }} {{ item.unit || '' }}</td>
            </tr>
            <tr v-if="items.length === 0"><td colspan="3" class="packaging-checklist-empty">Este pedido no contiene artículos para preparar.</td></tr>
          </tbody>
        </table>
      </div>
      <p v-if="error" class="operations-alert error packaging-checklist-error">{{ error }}</p>
      <button class="packaging-confirm-button" type="button" :disabled="busy || returned || !allItemsPacked" @click="packageOrder(selected)">
        {{ busy ? 'Confirmando empaque…' : 'Confirmar Empaque del Pedido' }}
      </button>
    </section>
  </main>
</template>
