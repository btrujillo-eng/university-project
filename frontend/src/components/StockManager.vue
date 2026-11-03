<script setup>
import { computed, onMounted, ref } from 'vue'
import { API_BASE_URL, listProducts, updateProductStock } from '../services/api'

const props = defineProps({ user: { type: Object, required: true }, token: { type: String, required: true } })
const emit = defineEmits(['logout'])
const products = ref([])
const search = ref('')
const drafts = ref({})
const editingProduct = ref(null)
const loading = ref(false)
const busyId = ref(null)
const error = ref('')
const success = ref('')
const failedImages = ref(new Set())

const unitLabels = { kilogram: 'kg', gram: 'g', pound: 'lb', unit: 'ud' }
const displayName = computed(() => [props.user.first_name, props.user.first_surname].filter(Boolean).join(' ') || 'Administrador de bodega')
const filtered = computed(() => {
  const query = search.value.trim().toLocaleLowerCase()
  return products.value.filter(product => !query || product.name.toLocaleLowerCase().includes(query))
})
const money = value => new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(Number(value || 0))
const unitLabel = product => unitLabels[product.unit_of_measure] || product.unit_of_measure || 'ud'
const imageUrl = product => product.image_path ? `${API_BASE_URL}${product.image_path.startsWith('/') ? '' : '/'}${product.image_path}` : ''

async function load() {
  loading.value = true
  error.value = ''
  success.value = ''
  try {
    products.value = await listProducts()
    drafts.value = Object.fromEntries(products.value.map(product => [product.id, String(product.stock)]))
    failedImages.value = new Set()
  } catch (exception) {
    error.value = exception.message || 'No fue posible cargar el inventario.'
  } finally {
    loading.value = false
  }
}

function startEditing(product) {
  drafts.value[product.id] = String(product.stock)
  editingProduct.value = product
  error.value = ''
  success.value = ''
}

function cancelEditing() {
  if (busyId.value === editingProduct.value?.id) return
  editingProduct.value = null
}

async function save(product) {
  const stock = Number(drafts.value[product.id])
  if (!Number.isFinite(stock) || stock < 0) {
    error.value = 'Ingresa una existencia válida.'
    return
  }
  busyId.value = product.id
  error.value = ''
  success.value = ''
  try {
    const updated = await updateProductStock(product.id, stock, props.token)
    const index = products.value.findIndex(item => item.id === product.id)
    if (index !== -1) products.value[index] = updated
    drafts.value[product.id] = String(updated.stock)
    editingProduct.value = null
    success.value = `Existencias de ${updated.name} actualizadas.`
  } catch (exception) {
    error.value = exception.message || 'No fue posible actualizar las existencias.'
  } finally {
    busyId.value = null
  }
}

function hideBrokenImage(productId) {
  failedImages.value = new Set([...failedImages.value, productId])
}

onMounted(load)
</script>

<template>
  <main class="stock-page">
    <header class="stock-header">
      <a class="stock-brand" href="#" @click.prevent="load" aria-label="Canasta Express, actualizar inventario">
        <span class="stock-brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none"><path d="M12 20V9m0 0c-4.4 0-6.5-2.2-6.5-6 4.3 0 6.5 2.1 6.5 6Zm0 2c0-4.2 2.1-6.2 6.5-6.2 0 4.1-2.1 6.2-6.5 6.2Z" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </span>
        <span class="stock-brand-copy"><strong>Canasta Express</strong><small>Legumbrería &amp; Verdulería Online</small></span>
      </a>
      <div class="stock-user">
        <span>Hola, {{ displayName }}</span>
        <span class="stock-avatar" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="8" r="4" stroke="currentColor" stroke-width="1.5"/><path d="M4.5 21c.7-4.2 3.2-6.3 7.5-6.3s6.8 2.1 7.5 6.3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg></span>
        <button type="button" @click="emit('logout')">Salir</button>
      </div>
    </header>

    <section class="stock-content">
      <form class="stock-search" @submit.prevent>
        <input v-model="search" type="search" placeholder="Ingrese el nombre del producto o sección" aria-label="Buscar producto o sección">
        <button type="submit" aria-label="Buscar"><svg viewBox="0 0 24 24" fill="none"><circle cx="10.8" cy="10.8" r="6.8" stroke="currentColor" stroke-width="1.7"/><path d="m16 16 4.5 4.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg></button>
      </form>

      <div class="stock-heading">
        <h1>Panel de Gestión de Inventario (Bodega)</h1>
        <button class="stock-refresh" type="button" @click="load" :disabled="loading">
          <svg viewBox="0 0 24 24" fill="none"><path d="M20 7v5h-5M4.8 10a7.5 7.5 0 0 1 12.8-3L20 12M4 17v-5h5m10.2 2a7.5 7.5 0 0 1-12.8 3L4 12" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>
          Actualizar
        </button>
      </div>

      <p v-if="error" class="stock-message is-error" role="alert">{{ error }}</p>
      <p v-if="success" class="stock-message is-success" role="status">{{ success }}</p>
      <p v-if="loading" class="stock-empty">Cargando inventario…</p>
      <div v-else-if="filtered.length" class="stock-grid">
        <article v-for="product in filtered" :key="product.id" class="stock-card">
          <div class="stock-image">
            <img v-if="imageUrl(product) && !failedImages.has(product.id)" :src="imageUrl(product)" :alt="product.name" @error="hideBrokenImage(product.id)">
            <svg v-else viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 20V9m0 0c-4.4 0-6.5-2.2-6.5-6 4.3 0 6.5 2.1 6.5 6Zm0 2c0-4.2 2.1-6.2 6.5-6.2 0 4.1-2.1 6.2-6.5 6.2Z" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </div>
          <div class="stock-card-info">
            <h2>{{ product.name }}</h2>
            <p class="stock-price">{{ money(product.price) }} / {{ unitLabel(product) }}</p>
            <p class="stock-available">Disponible: <strong>{{ product.stock }} {{ unitLabel(product) }}</strong></p>
            <button type="button" class="stock-edit-button" @click="startEditing(product)">Actualizar cantidad disponible</button>
          </div>
        </article>
      </div>
      <p v-else class="stock-empty">No se encontraron productos.</p>
    </section>
      <div v-if="editingProduct" class="stock-modal-backdrop" @click.self="cancelEditing" @keydown.esc="cancelEditing">
        <section class="stock-modal" role="dialog" aria-modal="true" :aria-labelledby="'stock-modal-title'">
          <h2 id="stock-modal-title">Actualizar Inventario: {{ editingProduct.name }}</h2>
          <div class="stock-modal-product">
            <div class="stock-modal-image">
              <img v-if="imageUrl(editingProduct) && !failedImages.has(editingProduct.id)" :src="imageUrl(editingProduct)" :alt="editingProduct.name" @error="hideBrokenImage(editingProduct.id)">
              <svg v-else viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 20V9m0 0c-4.4 0-6.5-2.2-6.5-6 4.3 0 6.5 2.1 6.5 6Zm0 2c0-4.2 2.1-6.2 6.5-6.2 0 4.1-2.1 6.2-6.5 6.2Z" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </div>
            <div class="stock-modal-product-copy">
              <strong>{{ editingProduct.name }}</strong>
              <span>Cantidad disponible actual: {{ editingProduct.stock }} {{ unitLabel(editingProduct) }}</span>
            </div>
          </div>
          <form class="stock-modal-form" @submit.prevent="save(editingProduct)">
            <label :for="'stock-modal-input'">Nueva cantidad ({{ unitLabel(editingProduct) }}):</label>
            <div class="stock-modal-input-wrap">
              <input id="stock-modal-input" v-model="drafts[editingProduct.id]" type="number" min="0" max="9999999.999" step="0.001" required autofocus>
              <span>{{ unitLabel(editingProduct) }}</span>
            </div>
            <p v-if="error" class="stock-modal-error" role="alert">{{ error }}</p>
            <div class="stock-modal-actions">
              <button class="stock-save" type="submit" :disabled="busyId === editingProduct.id">{{ busyId === editingProduct.id ? 'Guardando…' : 'Guardar Cambios' }}</button>
              <button class="stock-cancel" type="button" :disabled="busyId === editingProduct.id" @click="cancelEditing">Cancelar</button>
            </div>
          </form>
        </section>
      </div>
    
  </main>
</template>

<style scoped>
.stock-page{min-height:100vh;background:#e8c5a5;color:#211b16;font-family:inherit}
.stock-header{height:78px;padding:0 2%;display:flex;align-items:center;justify-content:space-between;background:#f5e7c9;box-shadow:0 5px 14px #4a321b25}
.stock-brand{display:flex;align-items:center;gap:10px;color:#17140f;text-decoration:none}
.stock-brand-mark{width:50px;height:50px;border-radius:13px;background:#51543a;color:#f8eed8;display:grid;place-items:center}
.stock-brand-mark svg{width:25px;height:25px}
.stock-brand-copy{display:flex;flex-direction:column;line-height:1.05}
.stock-brand-copy strong{font-family:Georgia,serif;font-size:25px}
.stock-brand-copy small{font-family:Georgia,serif;font-size:14px;margin-top:4px}
.stock-user{display:flex;align-items:center;gap:14px;font-size:23px}
.stock-avatar{width:48px;height:48px;border-radius:50%;background:#55583d;color:#f7ecd5;display:grid;place-items:center}
.stock-avatar svg{width:38px;height:38px}
.stock-user button{display:inline-flex;align-items:center;justify-content:center;min-height:42px;padding:0 0 0 16px;border:0;border-left:1px solid #b7a17e;background:transparent;color:#292318;font:inherit;font-size:16px;cursor:pointer;transition:color .15s ease}.stock-user button:hover{color:#666b45}.stock-user button:focus-visible{outline:2px solid #666b45;outline-offset:4px;border-radius:3px}
.stock-content{max-width:1500px;margin:0 auto;padding:20px 24px 64px}
.stock-search{width:min(580px,100%);height:44px;margin:0 auto 28px;display:flex;align-items:center;background:#fff;border:1px solid #cbb89e;border-radius:15px;padding:3px 5px 3px 14px;box-shadow:0 3px 10px #51351d14}
.stock-search input{min-width:0;flex:1;border:0;outline:0;background:transparent;font:inherit;font-size:16px;color:#241c16}
.stock-search input::placeholder{color:#6d655b}
.stock-search button{width:34px;height:34px;border:0;border-radius:50%;background:#55583d;color:white;display:grid;place-items:center}
.stock-search button svg{width:20px;height:20px}
.stock-heading{position:relative;text-align:center;margin:0 0 20px}
.stock-heading h1{margin:0;font-family:Georgia,serif;font-weight:500;font-size:29px;line-height:1.25}
.stock-refresh{position:absolute;right:0;top:0;border:1px solid #4e5136;border-radius:9px;background:#f5e7c9;color:#272317;padding:9px 14px;display:flex;align-items:center;gap:7px;font:inherit;font-size:14px}
.stock-refresh svg{width:17px;height:17px}
.stock-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px}
.stock-card{min-width:0;min-height:170px;display:grid;grid-template-columns: minmax(130px,48%) minmax(0,1fr);overflow:hidden;border-radius:20px;background:#f1dfb8;box-shadow:0 7px 14px #52381f24;border:1px solid #d8c39f}
.stock-image{min-height:170px;background:#dfc9a4;display:grid;place-items:center;overflow:hidden}
.stock-image img{width:100%;height:100%;min-height:170px;object-fit:cover;display:block}
.stock-image>svg{width:52px;height:52px;color:#56583d}
.stock-card-info{padding:10px 12px;display:flex;flex-direction:column;align-items:flex-start;justify-content:center;min-width:0}
.stock-card-info h2{font-family:Georgia,serif;font-size:23px;font-weight:500;line-height:1.15;margin:0 0 5px}
.stock-price,.stock-available{font-size:16px;line-height:1.3;margin:0 0 4px}
.stock-available strong{font-weight:600}
.stock-edit-button{width:100%;min-height:56px;margin-top:12px;padding:7px 10px;border:1px solid #53563a;border-radius:12px;background:#77795b;color:#fff8e9;font:inherit;font-size:17px;line-height:1.1;cursor:pointer}
.stock-edit-button:hover,.stock-save:hover{background:#55583d}
.stock-modal-backdrop{position:fixed;inset:0;z-index:1000;display:grid;place-items:center;padding:20px;background:#211a13a8;backdrop-filter:blur(2px)}
.stock-modal{width:min(548px,100%);box-sizing:border-box;padding:25px 24px 20px;border:1px solid #d6bd94;border-radius:23px;background:#f3e2bd;box-shadow:0 18px 55px #21170f55;color:#211b16}
.stock-modal>h2{margin:0 0 20px;text-align:center;font-family:Georgia,serif;font-size:30px;font-weight:500;line-height:1.2}
.stock-modal-product{display:flex;align-items:center;gap:16px;margin-bottom:20px}
.stock-modal-image{width:116px;height:96px;flex:0 0 116px;overflow:hidden;border-radius:17px;background:#e5d1ad;box-shadow:0 4px 10px #52381f24;display:grid;place-items:center}
.stock-modal-image img{width:100%;height:100%;object-fit:cover;display:block}
.stock-modal-image svg{width:48px;height:48px;color:#55583d}
.stock-modal-product-copy{min-width:0;display:flex;flex-direction:column;gap:4px;font-size:21px;line-height:1.25}
.stock-modal-product-copy strong{font-family:Georgia,serif;font-size:24px;font-weight:500}
.stock-modal-form{display:grid;gap:8px}
.stock-modal-form>label{font-size:21px}
.stock-modal-input-wrap{height:50px;display:flex;align-items:center;overflow:hidden;border:2px solid #b7a17e;border-radius:9px;background:#fff}
.stock-modal-input-wrap:focus-within{border-color:#656b45;box-shadow:0 0 0 3px #77795b30}
.stock-modal-input-wrap input{width:100%;min-width:0;height:100%;box-sizing:border-box;padding:7px 10px;border:0;outline:0;background:transparent;font:inherit;font-size:23px;color:#211b16}
.stock-modal-input-wrap span{padding:0 12px;font-size:20px;color:#3d372e}
.stock-modal-actions{display:flex;justify-content:flex-end;gap:12px;margin-top:13px}
.stock-modal-actions button{min-height:47px;padding:8px 15px;border-radius:12px;font:inherit;font-size:17px;cursor:pointer}
.stock-modal-actions .stock-save{border:1px solid #55583d;background:#77795b;color:#fff8e9}
.stock-modal-actions .stock-cancel{border:1px solid #777;color:#fff;background:#858585}
.stock-modal-actions button:disabled{opacity:.6;cursor:wait}
.stock-modal-error{margin:0;color:#982d22;font-size:14px}
.stock-message,.stock-empty{margin:14px 0;text-align:center;font-size:15px}
.is-error{color:#8d251d}.is-success{color:#245d32}
@media(max-width:1050px){.stock-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.stock-refresh{position:static;margin:12px auto 0}.stock-heading{display:flex;flex-direction:column}}
@media(max-width:650px){.stock-modal{padding:20px 16px 16px;border-radius:18px}.stock-modal>h2{font-size:24px}.stock-modal-image{width:88px;height:82px;flex-basis:88px}.stock-modal-product-copy{font-size:16px}.stock-modal-product-copy strong{font-size:20px}.stock-modal-form>label{font-size:17px}.stock-modal-actions{gap:8px}.stock-modal-actions button{font-size:14px;padding:8px 11px}.stock-header{height:auto;min-height:70px;padding:10px 14px}.stock-brand-copy strong{font-size:19px}.stock-brand-copy small{font-size:11px}.stock-user{font-size:0;gap:8px}.stock-avatar{width:40px;height:40px}.stock-user button{min-height:36px;padding-left:10px;font-size:13px}.stock-content{padding:18px 12px 40px}.stock-heading h1{font-size:24px}.stock-grid{grid-template-columns:1fr;gap:15px}.stock-card{grid-template-columns:42% minmax(0,1fr);min-height:155px}.stock-image,.stock-image img{min-height:155px}.stock-card-info h2{font-size:20px}.stock-price,.stock-available{font-size:14px}.stock-edit-button{font-size:15px;min-height:48px}}
</style>
