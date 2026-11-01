<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import {
  API_BASE_URL,
  createProduct,
  listProductSections,
  listProducts,
  updateProductPrice,
} from '../services/api'

const props = defineProps({
  user: { type: Object, required: true },
  token: { type: String, required: true },
})
const emit = defineEmits(['logout'])

const screen = ref('catalog')
const products = ref([])
const sections = ref([])
const searchTerm = ref('')
const busy = ref(false)
const loading = ref(true)
const errorMessage = ref('')
const successMessage = ref('')
const editingProduct = ref(null)
const priceDraft = ref('')
const selectedImage = ref(null)
const imagePreview = ref('')
const fileInput = ref(null)

const form = reactive({
  name: '',
  section_id: '',
  price: '',
  stock: '0',
  unit_of_measure: 'kilogram',
})

const userDisplayName = computed(() => {
  const name = [props.user.first_name, props.user.first_surname].filter(Boolean).join(' ')
  return name || 'Administrador'
})

const unitLabels = {
  kilogram: 'kg',
  gram: 'g',
  pound: 'lb',
  unit: 'unidad',
}

function clearMessages() {
  errorMessage.value = ''
  successMessage.value = ''
}

function getError(error) {
  return error instanceof Error ? error.message : 'Ocurrió un error inesperado.'
}

function formatPrice(value) {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0,
  }).format(Number(value))
}

function formatQuantity(value) {
  return new Intl.NumberFormat('es-CO', {
    maximumFractionDigits: 3,
  }).format(Number(value))
}

function imageUrl(path) {
  if (!path) return ''
  return `${API_BASE_URL}${path}`
}

async function loadProducts() {
  loading.value = true
  clearMessages()
  try {
    products.value = await listProducts(searchTerm.value.trim())
  } catch (error) {
    errorMessage.value = getError(error)
  } finally {
    loading.value = false
  }
}

async function loadSections() {
  try {
    sections.value = await listProductSections()
  } catch (error) {
    errorMessage.value = getError(error)
  }
}

function openCreateProduct() {
  clearMessages()
  resetForm()
  screen.value = 'create'
}

function resetForm() {
  form.name = ''
  form.section_id = sections.value[0]?.id ? String(sections.value[0].id) : ''
  form.price = ''
  form.stock = '0'
  form.unit_of_measure = 'kilogram'
  selectedImage.value = null
  if (imagePreview.value) URL.revokeObjectURL(imagePreview.value)
  imagePreview.value = ''
  if (fileInput.value) fileInput.value.value = ''
}

function selectImage(event) {
  const file = event.target.files?.[0] || null
  if (imagePreview.value) URL.revokeObjectURL(imagePreview.value)
  selectedImage.value = file
  imagePreview.value = file ? URL.createObjectURL(file) : ''
}

async function submitProduct() {
  clearMessages()
  if (!selectedImage.value) {
    errorMessage.value = 'Debes seleccionar una imagen para el producto.'
    return
  }
  if (!form.section_id) {
    errorMessage.value = 'Selecciona una sección para el producto.'
    return
  }

  const payload = new FormData()
  payload.append('name', form.name.trim())
  payload.append('section_id', form.section_id)
  payload.append('price', form.price)
  payload.append('stock', form.stock)
  payload.append('unit_of_measure', form.unit_of_measure)
  payload.append('image', selectedImage.value)

  busy.value = true
  try {
    await createProduct(payload, props.token)
    successMessage.value = 'El producto se agregó correctamente al catálogo.'
    await loadProducts()
    resetForm()
    screen.value = 'catalog'
  } catch (error) {
    errorMessage.value = getError(error)
  } finally {
    busy.value = false
  }
}

function startPriceEdit(product) {
  clearMessages()
  editingProduct.value = product
  priceDraft.value = String(product.price)
}

function cancelPriceEdit() {
  editingProduct.value = null
  priceDraft.value = ''
}

async function savePrice() {
  if (!editingProduct.value) return
  clearMessages()
  busy.value = true
  try {
    const product = editingProduct.value
    const updated = await updateProductPrice(product.id, priceDraft.value, props.token)
    const index = products.value.findIndex((item) => item.id === product.id)
    if (index !== -1) products.value[index] = updated
    cancelPriceEdit()
    successMessage.value = `Precio de ${updated.name} actualizado.`
  } catch (error) {
    errorMessage.value = getError(error)
  } finally {
    busy.value = false
  }
}

function returnToCatalog() {
  clearMessages()
  resetForm()
  screen.value = 'catalog'
}

onMounted(async () => {
  await Promise.all([loadSections(), loadProducts()])
})

onUnmounted(() => {
  if (imagePreview.value) URL.revokeObjectURL(imagePreview.value)
})
</script>

<template>
  <main class="admin-shell">
    <section v-if="screen === 'catalog'" class="admin-content">
      <div class="catalog-toolbar">
        <form class="catalog-search" @submit.prevent="loadProducts">
          <input v-model="searchTerm" type="search" placeholder="Ingrese el nombre del producto o sección" aria-label="Buscar producto o sección" />
          <button type="submit" aria-label="Buscar productos">
            <svg viewBox="0 0 24 24" fill="none"><circle cx="10.8" cy="10.8" r="6.8" stroke="currentColor" stroke-width="1.7"/><path d="m16 16 4.5 4.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>
          </button>
        </form>
        <button type="button" class="add-product-button" @click="openCreateProduct">
          <span aria-hidden="true">＋</span> Añadir Nuevo Producto
        </button>
      </div>

      <h1 class="catalog-title">Gestión de Catálogo de Productos (Admin)</h1>

      <div v-if="errorMessage" class="admin-notice error" role="alert">{{ errorMessage }}</div>
      <div v-if="successMessage" class="admin-notice success" role="status">{{ successMessage }}</div>

      <div v-if="loading" class="catalog-state">Cargando productos…</div>
      <div v-else-if="products.length" class="product-grid">
        <article v-for="product in products" :key="product.id" class="admin-product-card">
          <div class="admin-product-image">
            <img v-if="product.image_path" :src="imageUrl(product.image_path)" :alt="product.name" />
            <div v-else class="product-image-placeholder"><span aria-hidden="true">♧</span><small>Sin imagen</small></div>
          </div>
          <div class="admin-product-info">
            <h2>{{ product.name }}</h2>
            <p>{{ formatPrice(product.price) }} / {{ unitLabels[product.unit_of_measure] || product.unit_of_measure }} disponible: {{ formatQuantity(product.stock) }} {{ unitLabels[product.unit_of_measure] || product.unit_of_measure }}</p>
            <button type="button" class="edit-price-button" @click="startPriceEdit(product)">Editar precio</button>
          </div>
        </article>
      </div>
      <div v-else class="catalog-state">No se encontraron productos. Puedes agregar el primero con “Añadir Nuevo Producto”.</div>
    </section>

    <section v-else class="create-product-area">
      <form class="create-product-card" @submit.prevent="submitProduct">
        <h1>Añadir Nuevo Producto</h1>
        <div class="create-product-layout">
          <div class="create-product-fields">
            <label class="admin-field">
              <span>Nombre</span>
              <input v-model.trim="form.name" type="text" minlength="2" maxlength="120" placeholder="Nombre del producto" required />
            </label>
            <label class="admin-field">
              <span>Precio (COP)</span>
              <input v-model="form.price" type="number" min="0.01" max="99999999.99" step="0.01" placeholder="$ 0.00" required />
            </label>
            <label class="admin-field">
              <span>Cantidad disponible</span>
              <input v-model="form.stock" type="number" min="0" max="9999999.999" step="0.001" placeholder="0" required />
            </label>
            <label class="admin-field">
              <span>Sección</span>
              <select v-model="form.section_id" required>
                <option value="" disabled>Selecciona una sección</option>
                <option v-for="section in sections" :key="section.id" :value="String(section.id)">{{ section.name }}</option>
              </select>
            </label>
            <label class="admin-field">
              <span>Unidad de medida</span>
              <select v-model="form.unit_of_measure" required>
                <option value="kilogram">Kilogramo (kg)</option>
                <option value="gram">Gramo (g)</option>
                <option value="pound">Libra (lb)</option>
                <option value="unit">Unidad</option>
              </select>
            </label>
          </div>

          <label class="image-upload-card" :class="{ 'has-image': imagePreview }">
            <input ref="fileInput" type="file" accept="image/jpeg,image/png,image/webp" @change="selectImage" />
            <img v-if="imagePreview" :src="imagePreview" alt="Vista previa de la imagen seleccionada" />
            <template v-else>
              <svg viewBox="0 0 48 48" fill="none" aria-hidden="true"><path d="M8 15a4 4 0 0 1 4-4h5l3-4h8l3 4h5a4 4 0 0 1 4 4v21a4 4 0 0 1-4 4H12a4 4 0 0 1-4-4V15Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><circle cx="24" cy="25" r="8" stroke="currentColor" stroke-width="1.7"/><circle cx="24" cy="25" r="3" fill="currentColor"/></svg>
              <strong>Añadir imagen</strong>
              <small>JPEG, PNG o WebP · Máximo 5 MB</small>
            </template>
            <span v-if="imagePreview" class="replace-image-label">Cambiar imagen</span>
          </label>
        </div>

        <p v-if="errorMessage" class="admin-notice error" role="alert">{{ errorMessage }}</p>
        <div class="create-product-actions">
          <button type="button" class="create-cancel-button" @click="returnToCatalog">× Cancelar</button>
          <button type="submit" class="create-save-button" :disabled="busy || !sections.length">{{ busy ? 'Guardando…' : '✓ Guardar' }}</button>
        </div>
        <p v-if="!sections.length" class="admin-form-hint">No hay secciones disponibles. Debes registrar una sección antes de crear productos.</p>
      </form>
    </section>

    <div v-if="editingProduct" class="price-modal-backdrop" @click.self="!busy && cancelPriceEdit()" @keydown.esc="!busy && cancelPriceEdit()">
      <section class="price-modal" role="dialog" aria-modal="true" :aria-labelledby="'price-modal-title'">
        <header class="price-modal-header">
          <h2 id="price-modal-title">Actualizar Precio</h2>
        </header>
        <form class="price-modal-content" @submit.prevent="savePrice">
          <h3>Actualizar Precio: <strong>{{ editingProduct.name }}</strong></h3>
          <div class="price-modal-product">
            <img v-if="editingProduct.image_path" :src="imageUrl(editingProduct.image_path)" :alt="editingProduct.name" />
            <div v-else class="price-modal-image-placeholder">♧</div>
            <div>
              <p class="price-modal-product-name">{{ editingProduct.name }}</p>
              <p>Disponible: {{ formatQuantity(editingProduct.stock) }} {{ unitLabels[editingProduct.unit_of_measure] || editingProduct.unit_of_measure }}</p>
            </div>
          </div>
          <p class="price-modal-current">Precio actual por {{ unitLabels[editingProduct.unit_of_measure] || editingProduct.unit_of_measure }}: {{ formatPrice(editingProduct.price) }}</p>
          <label class="price-modal-field" :for="'price-modal-input'">
            <input id="price-modal-input" v-model="priceDraft" type="number" min="0.01" max="99999999.99" step="0.01" placeholder="Nuevo precio" required autofocus />
            <span>Introduce el nuevo precio por {{ unitLabels[editingProduct.unit_of_measure] || editingProduct.unit_of_measure }}</span>
          </label>
          <p v-if="errorMessage" class="admin-notice error" role="alert">{{ errorMessage }}</p>
          <div class="price-modal-actions">
            <button type="submit" class="price-modal-confirm" :disabled="busy">{{ busy ? 'Guardando…' : '✓ Confirmar Cambios' }}</button>
            <button type="button" class="price-modal-cancel" :disabled="busy" @click="cancelPriceEdit">Cancelar</button>
          </div>
        </form>
      </section>
    </div>
  </main>
</template>
