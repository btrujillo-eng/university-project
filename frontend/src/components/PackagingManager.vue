<script setup>
import { onMounted, ref } from 'vue'
import { API_BASE_URL, getPackagingOrders, markOrderPackaged } from '../services/api'

const props = defineProps({ user: { type: Object, required: true }, token: { type: String, required: true } })
const emit = defineEmits(['logout'])
const orders = ref([])
const selected = ref(null)
const returned = ref(false)
const loading = ref(false)
const busy = ref(false)
const error = ref('')
const success = ref('')
const displayName = [props.user.first_name, props.user.first_surname].filter(Boolean).join(' ') || 'Encargado de empaque'
const money = value => new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(Number(value || 0))
const dateLabel = value => {
  const date = new Date(value)
  const parts = new Intl.DateTimeFormat('es-CO', { day: '2-digit', month: 'short', year: 'numeric' }).formatToParts(date)
  const part = type => parts.find(item => item.type === type)?.value ?? ''
  return `${part('day')} / ${part('month').replace('.', '')} / ${part('year')}`
}
async function loadOrders() {
  loading.value = true
  error.value = ''
  success.value = ''
  selected.value = null
  try { orders.value = await getPackagingOrders(props.token, returned.value) }
  catch (e) { error.value = e.message || 'No fue posible consultar los pedidos.' }
  finally { loading.value = false }
}
async function packageOrder(order) {
  busy.value = true
  error.value = ''
  success.value = ''
  try {
    await markOrderPackaged(order.id, props.token)
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

    <section class="packaging-mockup-page">
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
            <thead>
              <tr><th>ID PEDIDO</th><th>FECHA EMISIÓN</th><th>ESTADO</th><th>ACCIONES</th></tr>
            </thead>
            <tbody>
              <tr v-for="order in orders" :key="order.id">
                <td data-label="ID PEDIDO">{{ order.id }}</td>
                <td data-label="FECHA EMISIÓN">{{ dateLabel(order.created_at) }}</td>
                <td data-label="ESTADO">{{ returned ? 'Devuelto a bodega' : 'Pendiente' }}</td>
                <td data-label="ACCIONES"><button class="packaging-view-button" type="button" @click="selected = order">Ver Ítems</button></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else-if="!loading" class="packaging-table-message">
          {{ returned ? 'No hay pedidos devueltos a bodega.' : 'No hay pedidos pendientes de empaque.' }}
        </div>
      </div>

      <aside v-if="selected" class="operations-detail packaging-detail">
        <div class="operations-detail-heading">
          <h2>Pedido #{{ selected.id }}</h2>
          <button class="packaging-close-detail" type="button" @click="selected = null">Cerrar</button>
        </div>
        <p><strong>Cliente:</strong> {{ selected.customer_name }}</p>
        <p><strong>Dirección:</strong> {{ selected.shipping_street }}, {{ selected.shipping_neighborhood }}, {{ selected.shipping_city }}</p>
        <p><strong>Teléfono:</strong> {{ selected.phone_number }}</p>
        <p><strong>Pago:</strong> {{ selected.payment_method === 'cash' ? 'Efectivo' : 'Tarjeta' }} · {{ selected.payment_status }}</p>
        <h3>Productos que debes preparar</h3>
        <div v-for="item in selected.items" :key="item.product_id" class="operations-item">
          <img v-if="item.image_path" :src="API_BASE_URL + item.image_path" :alt="item.product_name">
          <span v-else>♧</span>
          <div><strong>{{ item.product_name }}</strong><small>{{ item.quantity }} unidades</small></div>
        </div>
        <div class="operations-total"><span>Total del pedido</span><strong>{{ money(selected.total_price) }}</strong></div>
        <button class="operations-primary" :disabled="busy || returned" @click="packageOrder(selected)">
          {{ busy ? 'Actualizando…' : 'Marcar pedido como empacado' }}
        </button>
      </aside>
    </section>
  </main>
</template>
