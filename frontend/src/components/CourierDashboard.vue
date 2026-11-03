<script setup>
import { onMounted, ref } from 'vue'
import { API_BASE_URL, confirmCashPayment, getAssignedOrders, updateDeliveryStatus } from '../services/api'

const props = defineProps({ user: { type: Object, required: true }, token: { type: String, required: true } })
const emit = defineEmits(['logout'])
const orders = ref([])
const selected = ref(null)
const loading = ref(false)
const busy = ref(false)
const error = ref('')
const success = ref('')
const modalMode = ref('delivery')

const displayName = [props.user.first_name, props.user.first_surname].filter(Boolean).join(' ') || 'Domiciliario'
const money = value => new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(Number(value || 0))
const dateLabel = value => {
  if (!value) return 'Fecha no disponible'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Fecha no disponible' : new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}
const deliveryLabel = value => ({
  packaged: 'Empacado',
  in_transit: 'En camino',
  delivered: 'Entregado',
  returned_to_warehouse: 'Devuelto a bodega',
  pending: 'Pendiente',
}[value] || value || 'Sin estado')
const paymentLabel = value => ({ pending: 'Pendiente', succeeded: 'Pagado', failed: 'Fallido', refunded: 'Reembolsado' }[value] || value || 'Sin estado')
const paymentMethodLabel = value => ({ cash: 'Efectivo', card: 'Tarjeta' }[value] || value || 'No especificado')

async function loadOrders() {
  loading.value = true
  error.value = ''
  try {
    orders.value = await getAssignedOrders(props.token)
    if (selected.value) selected.value = orders.value.find(order => order.id === selected.value.id) || null
  } catch (exception) {
    error.value = exception.message || 'No fue posible cargar tus entregas.'
  } finally {
    loading.value = false
  }
}
function openDetails(order, mode = 'delivery') {
  selected.value = order
  modalMode.value = mode
  error.value = ''
}
function closeDetails() {
  if (!busy.value) selected.value = null
}
function allowedStatuses(order) {
  return (order?.allowed_delivery_statuses || []).filter(status => status !== order.delivery_status)
}
async function updateStatus(status) {
  if (!selected.value) return
  busy.value = true
  error.value = ''
  success.value = ''
  try {
    await updateDeliveryStatus(selected.value.id, status, props.token)
    success.value = 'Estado de entrega actualizado.'
    await loadOrders()
    selected.value = null
  } catch (exception) {
    error.value = exception.message || 'No fue posible actualizar el estado de entrega.'
  } finally {
    busy.value = false
  }
}
async function confirmPayment(order) {
  if (order.payment_method !== 'cash' || order.payment_status !== 'pending' || order.delivery_status !== 'in_transit') return
  busy.value = true
  error.value = ''
  success.value = ''
  try {
    await confirmCashPayment(order.id, props.token)
    success.value = `Pago del pedido #${order.id} confirmado.`
    await loadOrders()
  } catch (exception) {
    error.value = exception.message || 'No fue posible confirmar el pago.'
  } finally {
    busy.value = false
  }
}
onMounted(loadOrders)
</script>

<template>
  <main class="operations-shell courier-shell">
    <header class="operations-header courier-header">
      <a class="customer-brand" href="#" @click.prevent="loadOrders">
        <span class="customer-brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><path d="M12 20V9m0 0c-4.4 0-6.5-2.2-6.5-6 4.3 0 6.5 2.1 6.5 6Zm0 2c0-4.2 2.1-6.2 6.5-6.2 0 4.1-2.1 6.2-6.5 6.2Z" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
        <span><strong>Canasta Express</strong><small>Legumbrería &amp; Verdulería Online</small></span>
      </a>
      <div class="courier-user">
        <span>Hola, {{ displayName }}</span>
        <span class="courier-avatar" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="8" r="4" stroke="currentColor" stroke-width="1.6"/><path d="M4.5 21a7.5 7.5 0 0 1 15 0" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg></span>
        <button @click="emit('logout')">Salir</button>
      </div>
    </header>

    <section class="operations-page courier-page">
      <div class="operations-title-row courier-title-row">
        <div>
          <p class="operations-kicker">OPERACIONES · DOMICILIOS</p>
          <h1>Panel de Control de Entregas (Domiciliario)</h1>
          <p>Consulta tus pedidos asignados y actualiza sus estados durante la entrega.</p>
        </div>
        <button class="operations-refresh" :disabled="loading" @click="loadOrders">↻ Actualizar</button>
      </div>

      <p v-if="error && !selected" class="operations-alert error">{{ error }}</p>
      <p v-if="success" class="operations-alert success">{{ success }}</p>
      <div v-if="loading && !orders.length" class="operations-empty">Cargando entregas…</div>
      <div v-else-if="orders.length" class="courier-grid">
        <article v-for="order in orders" :key="order.id" class="courier-card">
          <h2>Pedido #{{ order.id }}</h2>
          <div class="courier-card-content">
            <div class="courier-card-main">
              <div class="courier-status-line">
                <span>Estado de Entrega actual:</span>
                <span class="courier-status" :class="'delivery-' + order.delivery_status">{{ deliveryLabel(order.delivery_status) }}</span>
              </div>
              <button class="courier-action" @click="openDetails(order, 'delivery')">Actualizar estado de entrega</button>

              <div class="courier-payment-line">
                <span>Estado de Pago actual:</span>
                <span class="courier-status" :class="'payment-' + order.payment_status">{{ paymentLabel(order.payment_status) }}</span>
              </div>
              <button
                class="courier-action"
                :disabled="busy || order.payment_method !== 'cash' || order.payment_status !== 'pending' || order.delivery_status !== 'in_transit'"
                :title="order.payment_method !== 'cash' ? 'El pago con tarjeta se confirma automáticamente' : order.delivery_status !== 'in_transit' ? 'Confirma el efectivo cuando el pedido esté en camino' : ''"
                @click="confirmPayment(order)"
              >{{ order.payment_method === 'cash' && order.payment_status === 'pending' ? 'Actualizar estado de pago' : 'Información del pago' }}</button>
            </div>
            <button class="courier-info-button" @click="openDetails(order, 'info')">Ver información de domicilio</button>
          </div>
        </article>
      </div>
      <div v-else-if="!loading" class="operations-empty">No tienes pedidos asignados en este momento.</div>
    </section>

    <div v-if="selected" class="courier-modal-backdrop" @click.self="closeDetails" @keydown.esc="closeDetails">
      <section class="courier-modal" role="dialog" aria-modal="true" :aria-label="'Información del pedido ' + selected.id">
        <button class="courier-modal-close" aria-label="Cerrar" @click="closeDetails">×</button>
        <p class="operations-kicker">DETALLE DEL DOMICILIO</p>
        <h2>Pedido #{{ selected.id }}</h2>
        <div class="courier-modal-meta">
          <p><strong>Cliente:</strong> {{ selected.customer_name || 'No disponible' }}</p>
          <p><strong>Fecha:</strong> {{ dateLabel(selected.created_at) }}</p>
          <p><strong>Dirección:</strong> {{ [selected.shipping_street, selected.shipping_neighborhood, selected.shipping_city, selected.shipping_department].filter(Boolean).join(', ') || 'No disponible' }}</p>
          <p><strong>Teléfono:</strong> <a v-if="selected.phone_number" :href="'tel:' + selected.phone_number">{{ selected.phone_number }}</a><span v-else>No disponible</span></p>
          <p><strong>Referencia:</strong> {{ selected.shipping_details || 'Sin referencia adicional' }}</p>
          <p><strong>Instrucciones:</strong> {{ selected.shipping_instructions || 'Sin instrucciones adicionales' }}</p>
          <p><strong>Método de pago:</strong> {{ paymentMethodLabel(selected.payment_method) }}</p>
        </div>
        <h3>Productos del pedido</h3>
        <div v-if="selected.items?.length" class="courier-items">
          <div v-for="item in selected.items" :key="item.product_id" class="courier-item">
            <img v-if="item.image_path" :src="API_BASE_URL + item.image_path" :alt="item.product_name">
            <span v-else class="courier-item-placeholder">♧</span>
            <div><strong>{{ item.product_name }}</strong><small>{{ item.quantity }} · {{ money(item.unit_price) }} c/u</small></div>
          </div>
        </div>
        <p v-else class="courier-no-items">No hay artículos disponibles para mostrar.</p>
        <div class="courier-modal-total"><span>Total del pedido</span><strong>{{ money(selected.total_price) }}</strong></div>
        <div v-if="modalMode === 'delivery'" class="courier-modal-actions">
          <p v-if="!allowedStatuses(selected).length" class="courier-no-items">No hay transiciones de entrega disponibles para este pedido.</p>
          <button v-for="status in allowedStatuses(selected)" :key="status" class="courier-action courier-modal-action" :disabled="busy" @click="updateStatus(status)">
            {{ ({ in_transit: 'Marcar en camino', delivered: 'Marcar como entregado', returned_to_warehouse: 'Devolver a bodega' })[status] || deliveryLabel(status) }}
          </button>
        </div>
        <p v-if="error && selected" class="operations-alert error">{{ error }}</p>
      </section>
    </div>
  </main>
</template>

<style scoped>
.courier-header { min-height: 88px; }
.courier-user { display:flex; align-items:center; justify-content:flex-end; gap:13px; min-width:0; color:#211b16; font:500 17px var(--display); }
.courier-user button { padding:7px 0 7px 16px; border:0; border-left:1px solid #998a70; color:#625b49; background:transparent; cursor:pointer; font:inherit; font-size:14px; white-space:nowrap; }
.courier-avatar { display:grid; width:42px; height:42px; flex:0 0 42px; place-items:center; border-radius:50%; color:#f7ebd1; background:#55583d; }
.courier-avatar svg { width:27px; height:27px; }
.courier-page { width:min(100%,1600px); padding-top:42px; }
.courier-title-row { margin-bottom:28px; }
.courier-title-row h1 { max-width:900px; }
.courier-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:22px; align-items:stretch; }
.courier-card { display:flex; min-width:0; flex-direction:column; gap:9px; padding:19px 17px 17px; border:1px solid #dfc39c; border-radius:17px; background:#f1dfbb; box-shadow:0 7px 17px #67482b20; }
.courier-card h2 { margin:0 0 2px; color:#211b16; font:500 29px/1.15 var(--body); }
.courier-card-content { display:grid; grid-template-columns:minmax(112px,.38fr) minmax(0,1fr); gap:10px; align-items:stretch; }
.courier-card-main { display:flex; min-width:0; flex-direction:column; gap:8px; }
.courier-status-line,.courier-payment-line { display:flex; flex-wrap:wrap; align-items:center; gap:6px; color:#211b16; font-size:clamp(16px,1.35vw,21px); line-height:1.35; }
.courier-status { display:inline-flex; align-items:center; padding:2px 7px; border-radius:9px; color:#302719; background:#d8d8d8; white-space:nowrap; }
.courier-status.delivery-in_transit { background:#e7b34f; }
.courier-status.delivery-delivered,.courier-status.payment-succeeded { background:#b9d99a; }
.courier-status.delivery-pending,.courier-status.payment-pending { background:#d0d0d0; }
.courier-status.delivery-packaged { background:#f1d99b; }
.courier-status.delivery-returned_to_warehouse,.courier-status.payment-failed { background:#e7a16b; }
.courier-action,.courier-info-button { min-height:43px; padding:7px 12px; border:0; border-radius:11px; color:#fff8e9; background:#55583d; cursor:pointer; font:500 17px var(--body); line-height:1.2; }
.courier-action:hover,.courier-info-button:hover { background:#41442e; }
.courier-action:disabled { opacity:.58; cursor:not-allowed; }
.courier-payment-line { margin-top:3px; }
.courier-info-button { align-self:stretch; min-height:100%; margin:0; border:1px solid #41442e; background:#77795b; }
.courier-modal-backdrop { position:fixed; z-index:50; inset:0; display:grid; place-items:center; overflow-y:auto; padding:22px; background:#211a13a8; backdrop-filter:blur(3px); }
.courier-modal { position:relative; width:min(760px,100%); max-height:min(90vh,900px); overflow-y:auto; padding:28px; border:1px solid #d6bd94; border-radius:20px; color:#292318; background:#fff8eb; box-shadow:0 18px 55px #21170f55; }
.courier-modal-close { position:absolute; top:18px; right:18px; width:38px; height:38px; border:1px solid #cbb997; border-radius:50%; color:#292318; background:#f3e5c9; cursor:pointer; font-size:25px; line-height:1; }
.courier-modal h2 { margin:0 45px 18px 0; color:#064526; font:600 27px var(--display); }
.courier-modal-meta { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:0 20px; padding:13px 0; border-top:1px solid #dfd0b5; border-bottom:1px solid #dfd0b5; }
.courier-modal-meta p { margin:7px 0; color:#554b3c; font-size:14px; line-height:1.5; overflow-wrap:anywhere; }
.courier-modal-meta a { color:#42613b; }
.courier-modal h3 { margin:20px 0 8px; color:#064526; font:600 19px var(--display); }
.courier-items { display:grid; gap:0; }
.courier-item { display:flex; align-items:center; gap:13px; padding:10px 0; border-bottom:1px solid #e4d7c1; }
.courier-item img,.courier-item-placeholder { display:grid; width:56px; height:54px; flex:0 0 56px; place-items:center; border-radius:9px; object-fit:cover; background:#eee1c9; }
.courier-item div { display:flex; flex-direction:column; gap:4px; }
.courier-item small { color:#756b5a; }
.courier-no-items { color:#756b5a; font-size:14px; }
.courier-modal-total { display:flex; justify-content:space-between; margin-top:16px; padding-top:14px; border-top:1px solid #d9cbb2; font:600 18px var(--display); }
.courier-modal-actions { display:flex; flex-wrap:wrap; gap:9px; margin-top:18px; }
.courier-modal-action { flex:1 1 180px; }
@media(max-width:1050px) { .courier-grid { grid-template-columns:repeat(2,minmax(0,1fr)); } }
@media(max-width:650px) {
  .courier-header { align-items:flex-start; }
  .courier-user { gap:7px; font-size:12px; }
  .courier-avatar { width:34px; height:34px; flex-basis:34px; }
  .courier-user button { padding-left:9px; font-size:12px; }
  .courier-page { padding:25px 14px 45px; }
  .courier-title-row { align-items:flex-start; }
  .courier-title-row h1 { font-size:25px; }
  .courier-grid { grid-template-columns:1fr; gap:14px; }
  .courier-card h2 { font-size:25px; }
  .courier-status-line,.courier-payment-line { font-size:17px; }
  .courier-card-content { grid-template-columns:minmax(0,1fr); }
  .courier-info-button { min-height:43px; }
  .courier-action,.courier-info-button { font-size:16px; }
  .courier-modal { padding:22px 17px; }
  .courier-modal-meta { grid-template-columns:1fr; }
}
</style>
