<script setup>
import { onMounted, ref } from 'vue'
import { getPackagingOrders, markOrderPackaged } from '../services/api'

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
const dateLabel = value => new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
async function loadOrders() {
  loading.value = true; error.value = ''; selected.value = null
  try { orders.value = await getPackagingOrders(props.token, returned.value) }
  catch (e) { error.value = e.message || 'No fue posible consultar los pedidos.' }
  finally { loading.value = false }
}
async function packageOrder(order) {
  busy.value = true; error.value = ''; success.value = ''
  try { await markOrderPackaged(order.id, props.token); success.value = `El pedido #${order.id} quedó marcado como empacado.`; await loadOrders() }
  catch (e) { error.value = e.message || 'No fue posible actualizar el pedido.' }
  finally { busy.value = false }
}
function itemCount(order) { return order.items.reduce((n, item) => n + Number(item.quantity), 0) }
onMounted(loadOrders)
</script>

<template>
  <main class="operations-shell">
    <header class="operations-header">
      <a class="customer-brand" href="#" @click.prevent="loadOrders"><span class="customer-brand-mark">♧</span><span><strong>Canasta Express</strong><small>Legumbrería &amp; Verdulería Online</small></span></a>
      <div class="operations-user"><span>Hola, {{ displayName }}</span><button @click="emit('logout')">Salir</button></div>
    </header>
    <section class="operations-page">
      <div class="operations-title-row"><div><p class="operations-kicker">OPERACIONES · EMPAQUE</p><h1>Gestión de pedidos</h1><p>Consulta los pedidos pendientes y prepara los productos para su despacho.</p></div><button class="operations-refresh" @click="loadOrders">↻ Actualizar</button></div>
      <div class="operations-tabs"><button :class="{active: !returned}" @click="returned=false; loadOrders()">Pedidos pendientes</button><button :class="{active: returned}" @click="returned=true; loadOrders()">Devueltos a bodega</button></div>
      <p v-if="error" class="operations-alert error">{{ error }}</p><p v-if="success" class="operations-alert success">{{ success }}</p>
      <div v-if="loading" class="operations-empty">Cargando pedidos…</div>
      <div v-else-if="orders.length" class="operations-order-layout">
        <div class="operations-list">
          <button v-for="order in orders" :key="order.id" class="operations-order-row" :class="{selected: selected?.id===order.id}" @click="selected=order">
            <span class="operations-order-icon">▣</span><span class="operations-order-main"><strong>Pedido #{{ order.id }}</strong><small>{{ order.customer_name }} · {{ dateLabel(order.created_at) }}</small><small>{{ itemCount(order) }} unidades · {{ order.items.length }} productos</small></span><strong>{{ money(order.total_price) }}</strong>
          </button>
        </div>
        <aside v-if="selected" class="operations-detail">
          <div class="operations-detail-heading"><h2>Pedido #{{ selected.id }}</h2><span class="operations-status">{{ returned ? 'Devuelto' : 'Pendiente' }}</span></div>
          <p><strong>Cliente:</strong> {{ selected.customer_name }}</p><p><strong>Dirección:</strong> {{ selected.shipping_street }}, {{ selected.shipping_neighborhood }}, {{ selected.shipping_city }}</p><p><strong>Teléfono:</strong> {{ selected.phone_number }}</p><p><strong>Pago:</strong> {{ selected.payment_method === 'cash' ? 'Efectivo' : 'Tarjeta' }} · {{ selected.payment_status }}</p>
          <h3>Productos que debes preparar</h3>
          <div v-for="item in selected.items" :key="item.product_id" class="operations-item"><img v-if="item.image_path" :src="'/backend'+item.image_path" :alt="item.product_name"><span v-else>♧</span><div><strong>{{ item.product_name }}</strong><small>{{ item.quantity }} unidades</small></div></div>
          <div class="operations-total"><span>Total del pedido</span><strong>{{ money(selected.total_price) }}</strong></div>
          <button class="operations-primary" :disabled="busy" @click="packageOrder(selected)">{{ busy ? 'Actualizando…' : 'Marcar pedido como empacado' }}</button>
        </aside>
      </div>
      <div v-else class="operations-empty">{{ returned ? 'No hay pedidos devueltos a bodega.' : 'No hay pedidos pendientes de empaque.' }}</div>
    </section>
  </main>
</template>