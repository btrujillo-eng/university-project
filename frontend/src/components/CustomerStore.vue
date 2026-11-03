<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import {
  API_BASE_URL,
  addCartItem,
  checkoutOrder,
  getCart,
  getMyOrders,
  listProducts,
  removeCartItem,
} from '../services/api'

const props = defineProps({
  user: { type: Object, required: true },
  token: { type: String, required: true },
})
const emit = defineEmits(['logout'])

const screen = ref('catalog')
const products = ref([])
const cart = ref({ cart_id: null, items: [], total: 0 })
const orders = ref([])
const selectedProduct = ref(null)
const selectedOrder = ref(null)
const buyNowAfterAdd = ref(false)
const checkoutIdempotencyKey = ref('')
const checkoutPaymentMethodId = ref('')
const searchTerm = ref('')
const quantityDraft = ref('1')
const quantityStep = computed(() => {
  const unit = selectedProduct.value?.unit_of_measure
  return unit === 'unit' ? 1 : unit === 'gram' ? 100 : 0.5
})
const quantityUnitLabel = computed(() => unitLabel(selectedProduct.value?.unit_of_measure || ''))
const quantityTitleUnit = computed(() => ({ kilogram: 'kilos', gram: 'gramos', pound: 'libras', unit: 'unidades' })[selectedProduct.value?.unit_of_measure] || 'unidades')
const selectedQuantityTotal = computed(() => Number(selectedProduct.value?.price || 0) * Number(quantityDraft.value || 0))
const busy = ref(false)
const loading = ref(true)
const errorMessage = ref('')
const successMessage = ref('')
const paymentMethod = ref('cash')
const receipt = ref(null)
const checkoutResult = ref(null)
const cardElementContainer = ref(null)
const stripeCardElement = ref(null)
const stripeInstance = ref(null)
const stripeReady = ref(false)
const stripeError = ref('')
const publishableKey = import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || ''

const shipping = reactive({
  street: '',
  neighborhood: '',
  department: 'Antioquia',
  details: '',
  delivery_instructions: '',
  city: 'Medellín',
  phone_number: '',
})

const displayName = computed(() => [props.user.first_name, props.user.first_surname].filter(Boolean).join(' ') || 'Cliente')
const cartCount = computed(() => cart.value.items.reduce((sum, item) => sum + Number(item.quantity), 0))
const minimumOrder = 20000
const canCheckout = computed(() => Number(cart.value.total) >= minimumOrder)
const formattedTotal = computed(() => money(cart.value.total))

function money(value) {
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(Number(value || 0))
}
function quantity(value) {
  return new Intl.NumberFormat('es-CO', { maximumFractionDigits: 3 }).format(Number(value || 0))
}
function unitLabel(value) {
  return ({ kilogram: 'kg', gram: 'g', pound: 'lb', unit: 'unidad' })[value] || value
}
function imageUrl(path) {
  return path ? `${API_BASE_URL}${path}` : ''
}
function dateLabel(value) {
  return new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium' }).format(new Date(value))
}
function receiptDateLabel(value) {
  return new Intl.DateTimeFormat('es-CO', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(new Date(value))
}
function statusLabel(value) {
  return ({
    pending: 'Pendiente',
    packaged: 'Empacado',
    in_transit: 'En camino',
    delivered: 'Entregado',
    canceled: 'Cancelado',
    returned_to_warehouse: 'Devuelto a bodega',
  })[value] || value
}
function statusClass(value) {
  return ({
    pending: 'pending',
    packaged: 'packaged',
    in_transit: 'in-transit',
    delivered: 'delivered',
    canceled: 'canceled',
    returned_to_warehouse: 'returned',
  })[value] || 'pending'
}
function paymentLabel(value) {
  return value === 'card' ? 'Tarjeta' : 'Efectivo contraentrega'
}
function resetCheckoutAttempt() {
  checkoutIdempotencyKey.value = ''
  checkoutPaymentMethodId.value = ''
}

function clearMessages() {
  errorMessage.value = ''
  successMessage.value = ''
}
function showError(error) {
  const detail = error?.message || 'Ocurrió un error inesperado.'
  errorMessage.value = detail
}
async function loadProducts() {
  loading.value = true
  clearMessages()
  try {
    products.value = await listProducts(searchTerm.value.trim())
  } catch (error) {
    showError(error)
  } finally {
    loading.value = false
  }
}
async function loadCart() {
  try {
    cart.value = await getCart(props.token)
  } catch (error) {
    showError(error)
  }
}
async function loadOrders() {
  loading.value = true
  clearMessages()
  try {
    orders.value = await getMyOrders(props.token)
  } catch (error) {
    showError(error)
  } finally {
    loading.value = false
  }
}
async function openCart() {
  clearMessages()
  await loadCart()
  screen.value = 'cart'
}
function openQuantityDialog(product, buyNow = false) {
  clearMessages()
  buyNowAfterAdd.value = buyNow
  selectedProduct.value = product
  quantityDraft.value = product.unit_of_measure === 'unit' ? '1' : product.unit_of_measure === 'gram' ? '100' : '0.5'
}
function adjustSelectedQuantity(direction) {
  if (!selectedProduct.value) return
  const next = Number(quantityDraft.value || 0) + quantityStep.value * direction
  const bounded = Math.min(Number(selectedProduct.value.stock), Math.max(quantityStep.value, next))
  quantityDraft.value = String(Number(bounded.toFixed(3)))
}
function closeQuantityDialog() {
  selectedProduct.value = null
}
async function addSelectedProduct() {
  if (!selectedProduct.value) return
  const amount = Number(quantityDraft.value)
  if (!Number.isFinite(amount) || amount <= 0 || amount > Number(selectedProduct.value.stock)) {
    errorMessage.value = 'Ingresa una cantidad válida que no supere las existencias disponibles.'
    return
  }
  busy.value = true
  clearMessages()
  try {
    cart.value = await addCartItem(selectedProduct.value.id, amount, props.token)
    resetCheckoutAttempt()
    selectedProduct.value = null
    successMessage.value = 'Producto agregado al carrito.'
    if (buyNowAfterAdd.value) {
      buyNowAfterAdd.value = false
      await openCart()
    }
  } catch (error) {
    showError(error)
  } finally {
    busy.value = false
  }
}
async function deleteCartItem(productId) {
  busy.value = true
  clearMessages()
  try {
    cart.value = await removeCartItem(productId, props.token)
    resetCheckoutAttempt()
  } catch (error) {
    showError(error)
  } finally {
    busy.value = false
  }
}
async function goToDelivery() {
  await loadCart()
  if (!cart.value.items.length) {
    errorMessage.value = 'Tu carrito está vacío.'
    return
  }
  if (!canCheckout.value) {
    errorMessage.value = `El pedido mínimo es de ${money(minimumOrder)}.`
    return
  }
  screen.value = 'delivery'
}
async function goToPayment() {
  clearMessages()
  if (!shipping.street || !shipping.neighborhood || !shipping.department || !shipping.details || !shipping.city || !/^\d{10}$/.test(shipping.phone_number)) {
    errorMessage.value = 'Completa los datos obligatorios. El teléfono debe tener 10 dígitos.'
    return
  }
  screen.value = 'payment'
  if (paymentMethod.value === 'card') await mountStripeCard()
}
async function mountStripeCard() {
  await nextTick()
  stripeError.value = ''
  if (!publishableKey) {
    stripeError.value = 'Configura VITE_STRIPE_PUBLISHABLE_KEY para habilitar pagos con tarjeta.'
    return
  }
  if (!window.Stripe) {
    stripeError.value = 'No se pudo cargar Stripe.js. Verifica tu conexión e inténtalo de nuevo.'
    return
  }
  if (!stripeInstance.value) stripeInstance.value = window.Stripe(publishableKey)
  if (!stripeCardElement.value) {
    const elements = stripeInstance.value.elements()
    stripeCardElement.value = elements.create('card', {
      hidePostalCode: true,
      style: {
        base: { fontFamily: 'DM Sans, sans-serif', fontSize: '16px', color: '#29271f', '::placeholder': { color: '#918a7d' } },
        invalid: { color: '#b33b2e' },
      },
    })
  }
  if (cardElementContainer.value && !stripeReady.value) {
    stripeCardElement.value.mount(cardElementContainer.value)
    stripeReady.value = true
  }
}
watch(paymentMethod, async (value) => {
  resetCheckoutAttempt()
  if (value === 'card' && screen.value === 'payment') {
    await mountStripeCard()
  } else if (value !== 'card' && stripeCardElement.value && stripeReady.value) {
    stripeCardElement.value.unmount()
    stripeReady.value = false
  }
})
async function submitCheckout() {
  clearMessages()
  if (!canCheckout.value) {
    errorMessage.value = `El pedido mínimo es de ${money(minimumOrder)}.`
    return
  }
  busy.value = true
  try {
    let payment
    if (paymentMethod.value === 'card') {
      if (!stripeInstance.value || !stripeCardElement.value) {
        throw new Error(stripeError.value || 'El formulario de tarjeta no está disponible.')
      }
      // Reuse the same PaymentMethod and idempotency key when retrying an
      // uncertain request. A fresh PaymentMethod with the old key changes the
      // Stripe request parameters and triggers an IdempotencyError.
      if (!checkoutPaymentMethodId.value) {
        const result = await stripeInstance.value.createPaymentMethod({
          type: 'card',
          card: stripeCardElement.value,
          billing_details: { name: displayName.value, phone: shipping.phone_number },
        })
        if (result.error) throw new Error(result.error.message)
        checkoutPaymentMethodId.value = result.paymentMethod.id
      }
      payment = { method: 'card', payment_method_id: checkoutPaymentMethodId.value }
    } else {
      payment = { method: 'cash' }
    }
    if (!checkoutIdempotencyKey.value) checkoutIdempotencyKey.value = crypto.randomUUID()
    const result = await checkoutOrder({
      shipping: { ...shipping },
      payment_method: payment,
    }, checkoutIdempotencyKey.value, props.token)
    resetCheckoutAttempt()
    checkoutResult.value = result
    receipt.value = result.receipt
    cart.value = { cart_id: null, items: [], total: 0 }
    if (paymentMethod.value === 'card' && stripeCardElement.value && stripeReady.value) {
      stripeCardElement.value.clear()
      stripeCardElement.value.unmount()
      stripeReady.value = false
    }
    screen.value = 'confirmation'
  } catch (error) {
    // A 402 is a definitive payment failure from the API. The next attempt
    // must use a new PaymentMethod and a new Stripe idempotency key.
    if (error?.status === 402) resetCheckoutAttempt()
    if (error?.status === 409 && error?.detail && typeof error.detail === 'object' && error.detail.order_id) {
      screen.value = 'history'
      await loadOrders()
      successMessage.value = `El pedido #${error.detail.order_id} ya había sido registrado. Puedes consultar su estado en tu historial.`
    } else {
      showError(error)
      if (error?.message?.includes('mínimo')) screen.value = 'cart'
    }
  } finally {
    busy.value = false
  }
}
function openHistory() {
  screen.value = 'history'
  loadOrders()
}
function openOrder(order) {
  selectedOrder.value = order
  screen.value = 'order-detail'
}
function returnToHistory() {
  selectedOrder.value = null
  screen.value = 'history'
}
function returnToCatalog() {
  screen.value = 'catalog'
  clearMessages()
  loadProducts()
}
function startShoppingAgain() {
  checkoutResult.value = null
  receipt.value = null
  screen.value = 'catalog'
  loadProducts()
}
function logout() {
  emit('logout')
}
onMounted(async () => {
  await Promise.all([loadProducts(), loadCart()])
})
onBeforeUnmount(() => {
  if (stripeCardElement.value) {
    try { stripeCardElement.value.destroy() } catch { /* Stripe may already have unmounted it. */ }
  }
})
</script>

<template>
  <main class="customer-app" :class="{ 'customer-payment-mode': screen === 'payment', 'customer-confirmation-mode': screen === 'confirmation' }">
    <header class="customer-header">
      <a href="#" class="customer-brand" @click.prevent="returnToCatalog">
        <span class="customer-brand-mark" aria-hidden="true"><svg viewBox="0 0 32 32" fill="none"><path d="M16 25V12m0 4c-6.2 0-9-3.1-9-8.2 5.9 0 9 2.9 9 8.2Zm0-2.2c0-5.8 2.9-8.5 9-8.5 0 5.7-2.9 8.5-9 8.5Z" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/><path d="M11.5 26h9" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg></span>
        <span><strong>Canasta Express</strong><small>Legumbrería &amp; Verdulería Online</small></span>
      </a>
      <form class="customer-search" @submit.prevent="screen = 'catalog'; loadProducts()">
        <input v-model="searchTerm" type="search" placeholder="Ingrese el nombre del producto o sección" aria-label="Buscar productos" />
        <button type="submit" aria-label="Buscar"><svg viewBox="0 0 24 24" fill="none"><circle cx="10.8" cy="10.8" r="6.8" stroke="currentColor" stroke-width="1.7"/><path d="m16 16 4.5 4.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg></button>
      </form>
      <button type="button" class="customer-cart-shortcut" aria-label="Abrir carrito" @click="openCart">
        <svg viewBox="0 0 24 24" fill="none"><path d="M2.5 4h2l2.2 11.2a2 2 0 0 0 2 1.6h8.7a2 2 0 0 0 1.9-1.5L21.5 8H5.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/><circle cx="9.5" cy="20" r="1.4" fill="currentColor"/><circle cx="18" cy="20" r="1.4" fill="currentColor"/></svg><span>{{ quantity(cartCount) }}</span>
      </button>
      <div class="customer-account">
        <span class="customer-avatar" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="8" r="3.4" stroke="currentColor" stroke-width="1.5"/><path d="M5.2 20c.5-3.6 3-5.5 6.8-5.5s6.3 1.9 6.8 5.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg></span>
        <span>Hola, {{ displayName }}</span>
        <button type="button" @click="logout">Salir</button>
      </div>
    </header>

    <div v-if="errorMessage" class="customer-alert error" role="alert">{{ errorMessage }}</div>
    <div v-if="successMessage" class="customer-alert success" role="status">{{ successMessage }}</div>

    <section v-if="screen === 'catalog'" class="customer-page">
      <div class="customer-page-actions"><button type="button" class="customer-history-link" @click="openHistory">Ver Historial de Pedidos</button></div>
      <h1 class="customer-page-title">Catálogo de Productos disponibles</h1>
      <div v-if="loading" class="customer-empty">Cargando catálogo…</div>
      <div v-else-if="products.length" class="customer-product-grid">
        <article v-for="product in products" :key="product.id" class="customer-product-card">
          <div class="customer-product-image">
            <img v-if="product.image_path" :src="imageUrl(product.image_path)" :alt="product.name" />
            <span v-else aria-hidden="true">♧</span>
          </div>
          <div class="customer-product-copy">
            <h2>{{ product.name }}</h2>
            <p class="customer-product-price">{{ money(product.price) }} / {{ unitLabel(product.unit_of_measure) }}</p>
            <p class="customer-stock">Disponible: {{ quantity(product.stock) }} {{ unitLabel(product.unit_of_measure) }}</p>
            <div class="customer-product-actions"><button type="button" class="customer-add-button" :disabled="Number(product.stock) <= 0" @click="openQuantityDialog(product)">Agregar al carrito</button><button type="button" class="customer-buy-button" :disabled="Number(product.stock) <= 0" @click="openQuantityDialog(product, true)">Comprar ahora</button></div>
          </div>
        </article>
      </div>
      <div v-else class="customer-empty">No hay productos disponibles para esta búsqueda.</div>
    </section>

    <section v-else-if="screen === 'cart'" class="customer-page checkout-page">
      <div class="customer-back-row"><button type="button" @click="returnToCatalog">← Regresar al catálogo</button></div>
      <h1 class="customer-page-title">Tu Carrito</h1>
      <div v-if="cart.items.length" class="cart-layout">
        <div class="cart-items">
          <article v-for="item in cart.items" :key="item.product_id" class="cart-item">
            <input type="checkbox" disabled :aria-label="`La selección individual de ${item.product_name} no está disponible`" />
            <img v-if="item.image_path" :src="imageUrl(item.image_path)" :alt="item.product_name" />
            <span v-else class="cart-placeholder">♧</span>
            <div class="cart-item-name"><strong>{{ item.product_name }}</strong><small>{{ unitLabel(item.unit_of_measure) }}</small></div>
            <span>{{ quantity(item.quantity) }} {{ unitLabel(item.unit_of_measure) }}</span>
            <strong>{{ money(item.line_total) }}</strong>
            <button type="button" class="remove-cart-item" :disabled="busy" :aria-label="`Eliminar ${item.product_name} del carrito`" :title="`Eliminar ${item.product_name}`" @click="deleteCartItem(item.product_id)">
              <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3m3 0-.8 13H6.8L6 7m4 4v5m4-5v5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>
          </article>
        </div>
        <aside class="cart-summary">
          <p>Total del pedido <strong>{{ formattedTotal }}</strong></p>
          <small v-if="!canCheckout" class="minimum-warning">Pedido mínimo: {{ money(minimumOrder) }}</small>
          <button type="button" class="customer-primary-button" :disabled="!canCheckout" @click="goToDelivery">Finalizar Compra</button>
        </aside>
      </div>
      <div v-else class="customer-empty">Tu carrito está vacío. Regresa al catálogo para agregar productos.</div>
    </section>

    <section v-else-if="screen === 'delivery'" class="customer-page checkout-page">
      <div class="customer-back-row"><button type="button" @click="screen = 'cart'">← Volver al carrito</button></div>
      <p class="checkout-breadcrumb">Catálogo &gt; Mi Carrito &gt; Datos de Domicilio</p>
      <h1 class="customer-page-title">Datos de tu domicilio</h1>
      <p class="checkout-subtitle">Por favor, completa los siguientes datos para la entrega de tu pedido.</p>
      <form class="checkout-form" @submit.prevent="goToPayment">
        <label class="customer-field"><span>Dirección de entrega</span><input v-model.trim="shipping.street" maxlength="80" placeholder="Ej. Carrera 45 # 50-10" required /></label>
        <label class="customer-field"><span>Barrio</span><input v-model.trim="shipping.neighborhood" maxlength="60" placeholder="Ej. El Poblado" required /></label>
        <label class="customer-field"><span>Departamento</span><input v-model.trim="shipping.department" maxlength="60" required /></label>
        <label class="customer-field"><span>Ciudad</span><input v-model.trim="shipping.city" maxlength="60" required /></label>
        <label class="customer-field"><span>Teléfono de contacto</span><input v-model.trim="shipping.phone_number" inputmode="numeric" pattern="[0-9]{10}" maxlength="10" placeholder="3001234567" required /></label>
        <label class="customer-field"><span>Detalles adicionales</span><input v-model.trim="shipping.details" maxlength="120" placeholder="Apartamento, torre, punto de referencia" required /></label>
        <label class="customer-field customer-field-wide"><span>Instrucciones de entrega (opcional)</span><textarea v-model.trim="shipping.delivery_instructions" maxlength="250" rows="3" placeholder="Indicaciones para encontrar tu domicilio"></textarea></label>
        <div class="checkout-form-actions"><button type="button" class="customer-secondary-button" @click="screen = 'cart'">Cancelar</button><button type="submit" class="customer-primary-button">Continuar a Datos de Pago</button></div>
      </form>
    </section>

    <section v-else-if="screen === 'payment'" class="customer-page checkout-page payment-page">
      <div class="customer-back-row"><button type="button" @click="screen = 'delivery'">← Volver a Datos de Domicilio</button></div>
      <p class="checkout-breadcrumb">Catálogo &gt; Mi Carrito &gt; Datos de Domicilio &gt; Datos de Pago</p>
      <h1 class="customer-page-title">Datos de Pago</h1>
      <p class="checkout-subtitle">Por favor, selecciona tu método de pago y revisa el resumen de tu compra.</p>
      <div class="payment-layout">
        <form id="checkout-payment-form" class="payment-form" @submit.prevent="submitCheckout">
          <label class="customer-field payment-method-field"><span>Selecciona tu Método de Pago</span>
            <select v-model="paymentMethod">
              <option value="card">Tarjeta de Crédito / Débito</option>
              <option value="cash">Efectivo (Contraentrega)</option>
            </select>
          </label>
          <div v-if="paymentMethod === 'card'" class="stripe-card-section">
            <p>Datos de tarjeta</p>
            <div ref="cardElementContainer" class="stripe-card-element"></div>
            <small>Los datos de tu tarjeta son procesados directamente por Stripe. Canasta Express no almacena el número ni el código de seguridad.</small>
            <p v-if="stripeError" class="stripe-error" role="alert">{{ stripeError }}</p>
          </div>
          <div v-else class="cash-instructions">
            <strong>Instrucciones de Pago en Efectivo (Contraentrega)</strong>
            <p>• Pagarás en efectivo directamente al domiciliario autorizado al momento de recibir tu pedido.</p>
            <p>• Por favor, ten el monto exacto completo de <b>{{ formattedTotal }}</b> listo para agilizar la entrega.</p>
            <p>• Esto ayuda a que el proceso de entrega sea más rápido y seguro para todos.</p>
          </div>
        </form>
        <aside class="order-cost-summary">
          <h2>Resumen de tu Compra</h2>
          <div v-for="item in cart.items" :key="item.product_id" class="cost-line"><span>{{ item.product_name }} × {{ quantity(item.quantity) }}</span><strong>{{ money(item.line_total) }}</strong></div>
          <div class="cost-line"><span>Envío a domicilio ({{ shipping.city }})</span><strong>Gratis</strong></div>
          <div class="cost-total"><span>Total a pagar</span><strong>{{ formattedTotal }}</strong></div>
        </aside>
      </div>
      <button form="checkout-payment-form" type="submit" class="customer-primary-button payment-submit" :disabled="busy || (paymentMethod === 'card' && (!stripeReady || Boolean(stripeError)))">{{ busy ? 'Procesando pedido…' : 'Proceder al Pago' }}</button>
      <footer class="payment-footer">© Copyright | Canasta Express -- Links · Privacy Policies</footer>
    </section>

    <section v-else-if="screen === 'confirmation'" class="customer-page confirmation-page">
      <article class="digital-receipt">
        <div class="receipt-brand">
          <span class="receipt-brand-mark" aria-hidden="true">
            <svg viewBox="0 0 32 32" fill="none">
              <path d="M16 25V12m0 4c-6.2 0-9-3.1-9-8.2 5.9 0 9 2.9 9 8.2Zm0-2.2c0-5.8 2.9-8.5 9-8.5 0 5.7-2.9 8.5-9 8.5Z" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M11.5 26h9" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
            </svg>
          </span>
          <strong>Canasta Express</strong>
        </div>
        <p class="receipt-kicker">Pedido confirmado</p>
        <h1>¡Gracias por tu compra!</h1>
        <p class="receipt-number">Pedido #{{ checkoutResult?.order?.id }}</p>
        <p class="receipt-message">Tu pedido fue registrado correctamente.</p>

        <div class="receipt-meta">
          <span>Fecha</span><strong>{{ receiptDateLabel(checkoutResult.order.created_at) }}</strong>
          <span>Estado del pago</span>
          <strong>{{ checkoutResult.order.payment_status === 'succeeded' ? 'Pagado' : 'Pendiente contraentrega' }}</strong>
          <span>Método de pago</span><strong>{{ paymentLabel(checkoutResult.order.payment_method) }}</strong>
        </div>

        <div class="receipt-lines">
          <div v-for="item in checkoutResult.order.items" :key="item.product_id">
            <span>{{ item.product_name }} × {{ quantity(item.quantity) }}</span>
            <strong>{{ money(Number(item.unit_price) * Number(item.quantity)) }}</strong>
          </div>
        </div>
        <div class="receipt-total">
          <span>Total del pedido</span>
          <strong>{{ money(checkoutResult.order.total_price) }}</strong>
        </div>
        <p v-if="receipt" class="receipt-reference">
          Comprobante {{ receipt.receipt_number }} · Transacción {{ checkoutResult.payment.transaction_id }}
        </p>
        <p v-else class="receipt-reference">
          Recuerda tener listo el efectivo para pagar al domiciliario cuando recibas tu pedido.
        </p>
        <button type="button" class="customer-primary-button" @click="startShoppingAgain">Regresar al Catálogo</button>
        <button type="button" class="customer-text-button" @click="openHistory">Ver Mis Pedidos</button>
      </article>
    </section>

    <section v-else-if="screen === 'history'" class="customer-page history-page">
      <div class="customer-page-actions"><button type="button" class="customer-history-link" @click="returnToCatalog">Volver al Catálogo</button></div>
      <h1 class="customer-page-title">Historial de mis Pedidos</h1>
      <div v-if="loading" class="customer-empty">Cargando historial…</div>
      <div v-else-if="orders.length" class="customer-order-grid">
        <article v-for="(order, index) in orders" :key="order.id" class="customer-order-card">
          <div class="order-parcel-icon" aria-hidden="true">▣</div>
          <div class="order-card-content">
            <div class="order-card-heading"><h2>Pedido #{{ index + 1 }}</h2><span class="order-status" :class="statusClass(order.delivery_status)">{{ statusLabel(order.delivery_status) }}</span></div>
            <strong class="order-public-id">#{{ order.id }}</strong>
            <p>Fecha: {{ dateLabel(order.created_at) }}</p>
            <p>Total: {{ money(order.total_price) }}</p>
            <button type="button" class="customer-order-detail-button" @click="openOrder(order)">Ver Detalles del Pedido</button>
          </div>
        </article>
      </div>
      <div v-else class="customer-empty">Aún no tienes pedidos registrados. Explora el catálogo para realizar tu primera compra.</div>
    </section>

    <section v-else-if="screen === 'order-detail' && selectedOrder" class="customer-page order-detail-page">
      <div class="customer-page-actions"><button type="button" class="customer-history-link" @click="returnToHistory">← Volver al Historial de Pedidos</button></div>
      <h1 class="customer-page-title">Detalles de mi Pedido ({{ selectedOrder.id }})</h1>
      <div class="order-detail-grid">
        <article class="order-detail-panel">
          <h2>Información del Pedido</h2>
          <p>Estado de Entrega:</p><span class="order-status detail-status" :class="statusClass(selectedOrder.delivery_status)">{{ statusLabel(selectedOrder.delivery_status) }}</span>
          <p>Fecha de Compra: {{ dateLabel(selectedOrder.created_at) }}</p>
          <p>Método de Pago: {{ paymentLabel(selectedOrder.payment_method) }}</p>
          <p>Estado del Pago: {{ selectedOrder.payment_status === 'succeeded' ? 'Pagado' : selectedOrder.payment_status === 'pending' ? 'Pendiente' : 'Fallido' }}</p>
          <p>Dirección: {{ selectedOrder.shipping_street }}, {{ selectedOrder.shipping_neighborhood }}, {{ selectedOrder.shipping_city }}</p>
          <p>Teléfono: {{ selectedOrder.phone_number }}</p>
        </article>
        <article class="order-detail-panel purchased-items-panel">
          <h2>Artículos Comprados ({{ selectedOrder.items.length }})</h2>
          <div v-for="item in selectedOrder.items" :key="item.product_id" class="purchased-item">
            <img v-if="item.image_path" :src="imageUrl(item.image_path)" :alt="item.product_name" />
            <span v-else class="purchased-placeholder">♧</span>
            <div><strong>{{ item.product_name }}</strong><small>{{ quantity(item.quantity) }} unidades</small></div>
            <div class="purchased-price"><strong>{{ money(item.unit_price) }}</strong><small>Subtotal: {{ money(Number(item.unit_price) * Number(item.quantity)) }}</small></div>
          </div>
        </article>
        <article class="order-detail-panel cost-detail-panel">
          <h2>Resumen de Costos</h2>
          <p><span>Subtotal:</span><strong>{{ money(selectedOrder.subtotal) }}</strong></p>
          <p><span>Costo de Envío:</span><strong>{{ Number(selectedOrder.shipping_cost) === 0 ? 'Gratis' : money(selectedOrder.shipping_cost) }}</strong></p>
          <hr />
          <p class="order-detail-total"><span>Total del Pedido:</span><strong>{{ money(selectedOrder.total_price) }}</strong></p>
        </article>
      </div>
    </section>

    <div v-if="selectedProduct" class="customer-modal-backdrop quantity-dialog-backdrop" @click.self="closeQuantityDialog">
      <form class="customer-quantity-modal quantity-dialog" @submit.prevent="addSelectedProduct">
        <button type="button" class="modal-close" aria-label="Cerrar" @click="closeQuantityDialog">×</button>
        <header class="quantity-dialog-heading">
          <h2>¿Cuántos {{ quantityTitleUnit }} de {{ selectedProduct.name }} necesitas?</h2>
        </header>
        <section class="quantity-product-summary">
          <img v-if="selectedProduct.image_path" :src="imageUrl(selectedProduct.image_path)" :alt="selectedProduct.name" />
          <div class="quantity-product-details">
            <h3>{{ selectedProduct.name }}</h3>
            <p>{{ money(selectedProduct.price) }} / {{ quantityUnitLabel }}</p>
            <small>Disponible: {{ quantity(selectedProduct.stock) }} {{ quantityUnitLabel }}</small>
          </div>
        </section>
        <div class="quantity-control-section">
          <div class="quantity-stepper">
            <button type="button" aria-label="Disminuir cantidad" :disabled="Number(quantityDraft) <= quantityStep || busy" @click="adjustSelectedQuantity(-1)">−</button>
            <output aria-live="polite">{{ quantity(quantityDraft) }} {{ quantityUnitLabel }}</output>
            <button type="button" aria-label="Aumentar cantidad" :disabled="Number(quantityDraft) + quantityStep > Number(selectedProduct.stock) || busy" @click="adjustSelectedQuantity(1)">+</button>
          </div>
          <label class="quantity-manual-entry"><span>O ingresa otra cantidad</span><input v-model="quantityDraft" type="number" min="0.001" :max="selectedProduct.stock" step="0.001" required /></label>
        </div>
        <div class="quantity-price-summary">
          <span>Precio por {{ quantityUnitLabel }}: <strong>{{ money(selectedProduct.price) }}</strong></span>
          <p>Total: <strong>{{ money(selectedQuantityTotal) }}</strong></p>
        </div>
        <button type="submit" class="customer-primary-button quantity-add-button" :disabled="busy || !Number.isFinite(Number(quantityDraft)) || Number(quantityDraft) <= 0 || Number(quantityDraft) > Number(selectedProduct.stock)">{{ busy ? 'Agregando…' : 'Agregar al carrito' }}</button>
        <button type="button" class="quantity-cancel-button" :disabled="busy" @click="closeQuantityDialog">Cancelar</button>
      </form>
    </div>
  </main>
</template>
