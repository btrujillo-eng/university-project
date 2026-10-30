<script setup>
import { computed, reactive, ref } from 'vue'
import {
  loginUser,
  registerUser,
  requestRestoreCode,
  resetPassword,
  verifyRestoreCode,
} from './services/api'

const screen = ref('login')
const busy = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const accessToken = ref('')
const currentUserEmail = ref('')

const login = reactive({ email: '', password: '' })
const registration = reactive({
  first_name: '',
  middle_name: '',
  first_surname: '',
  middle_surname: '',
  email: '',
  password: '',
  confirm_password: '',
})
const recovery = reactive({
  email: '',
  restore_code: '',
  new_password: '',
  confirm_password: '',
})
const recoveryStep = ref(1)
const showPassword = ref(false)
const showRegisterPassword = ref(false)

const screenTitle = computed(() => ({
  login: 'Bienvenido de vuelta',
  register: 'Crea tu cuenta',
  recovery: 'Recupera tu contraseña',
}[screen.value]))

function navigate(nextScreen) {
  screen.value = nextScreen
  errorMessage.value = ''
  successMessage.value = ''
  busy.value = false
  if (nextScreen === 'recovery') recoveryStep.value = 1
}

function getError(error) {
  return error instanceof Error ? error.message : 'Ocurrió un error inesperado.'
}

async function submitLogin() {
  errorMessage.value = ''
  successMessage.value = ''
  busy.value = true
  try {
    const result = await loginUser(login.email, login.password)
    accessToken.value = result.access_token
    currentUserEmail.value = login.email
    // El token queda en memoria durante esta sesión. No se guarda en localStorage.
    successMessage.value = 'Autenticación correcta. Tu sesión está iniciada.'
  } catch (error) {
    errorMessage.value = getError(error)
  } finally {
    busy.value = false
  }
}

async function submitRegistration() {
  errorMessage.value = ''
  successMessage.value = ''
  if (registration.password !== registration.confirm_password) {
    errorMessage.value = 'Las contraseñas no coinciden.'
    return
  }
  busy.value = true
  try {
    const result = await registerUser(registration)
    successMessage.value = result.message || 'Registro exitoso. Ya puedes iniciar sesión.'
    login.email = registration.email
    login.password = ''
    navigate('login')
    successMessage.value = result.message || 'Registro exitoso. Ya puedes iniciar sesión.'
  } catch (error) {
    errorMessage.value = getError(error)
  } finally {
    busy.value = false
  }
}

async function sendRestoreCode() {
  errorMessage.value = ''
  successMessage.value = ''
  busy.value = true
  try {
    const result = await requestRestoreCode(recovery.email)
    successMessage.value = result.message
    recoveryStep.value = 2
  } catch (error) {
    errorMessage.value = getError(error)
  } finally {
    busy.value = false
  }
}

async function checkRestoreCode() {
  errorMessage.value = ''
  successMessage.value = ''
  busy.value = true
  try {
    const result = await verifyRestoreCode(recovery.email, recovery.restore_code)
    successMessage.value = result.message
    recoveryStep.value = 3
  } catch (error) {
    errorMessage.value = getError(error)
  } finally {
    busy.value = false
  }
}

async function saveNewPassword() {
  errorMessage.value = ''
  successMessage.value = ''
  if (recovery.new_password !== recovery.confirm_password) {
    errorMessage.value = 'Las contraseñas no coinciden.'
    return
  }
  busy.value = true
  try {
    const result = await resetPassword(
      recovery.email,
      recovery.restore_code,
      recovery.new_password,
    )
    successMessage.value = result.message
    recoveryStep.value = 1
    recovery.restore_code = ''
    recovery.new_password = ''
    recovery.confirm_password = ''
  } catch (error) {
    errorMessage.value = getError(error)
  } finally {
    busy.value = false
  }
}

function signOut() {
  accessToken.value = ''
  currentUserEmail.value = ''
  login.password = ''
  successMessage.value = 'La sesión local se cerró.'
}
</script>

<template>
  <main class="app-shell">
    <section class="visual-panel" aria-label="Canasta Express">
      <div class="visual-image"></div>
      <div class="visual-shade"></div>
      <div class="visual-content">
        <div class="eyebrow"><span class="leaf-mark">✳</span> PRODUCTO FRESCO · COSECHA DIARIA</div>
        <h2>Del campo a tu <em>mesa</em>,<br />directo y sin rodeos.</h2>
        <p>Legumbres, granos y verduras de temporada seleccionados cada mañana por nuestros proveedores locales.</p>
      </div>
      <div class="visual-bottom">CANASTA EXPRESS <span>·</span> FRESCURA QUE SE NOTA</div>
    </section>

    <section class="form-panel">
      <div class="form-wrap">
        <header class="brand">
          <div class="brand-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none"><path d="M7 20h10M10 20c5.5-2.5.8-6.4 3-10M9.5 9.4c1.1.8 1.8 2.2 2.3 3.7-2 .4-3.5.4-4.8-.3-1.2-.6-2.3-1.9-3-4.2 2.8-.5 4.4 0 5.5.8ZM14.1 6a7 7 0 0 1 3.5 5c-1.4.5-2.8.6-4.1.3-1.1-.3-2.2-1-3.5-2.5 1.5-1.5 3-2.3 4.1-2.8Z" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </div>
          <div><strong>Canasta Express</strong><span>Legumbrería &amp; Verdulería Online</span></div>
        </header>

        <template v-if="!accessToken">
          <div class="heading">
            <p class="section-kicker">TU MERCADO, MÁS CERCA</p>
            <h1>{{ screenTitle }}</h1>
            <p class="subtitle">
              <template v-if="screen === 'login'">Ingresa a tu cuenta para gestionar tus pedidos.</template>
              <template v-else-if="screen === 'register'">Regístrate y recibe productos frescos en casa.</template>
              <template v-else>Te ayudaremos a recuperar el acceso a tu cuenta.</template>
            </p>
          </div>

          <div v-if="errorMessage" class="alert alert-error" role="alert">{{ errorMessage }}</div>
          <div v-if="successMessage" class="alert alert-success" role="status">{{ successMessage }}</div>

          <form v-if="screen === 'login'" class="form-fields" @submit.prevent="submitLogin">
            <label class="field"><span>Correo electrónico</span><input v-model.trim="login.email" type="email" autocomplete="email" placeholder="tu@correo.com" maxlength="255" required /></label>
            <label class="field">
              <span class="field-row"><span>Contraseña</span><button class="text-action" type="button" @click="navigate('recovery')">¿Olvidaste tu contraseña?</button></span>
              <span class="password-control"><input v-model="login.password" :type="showPassword ? 'text' : 'password'" autocomplete="current-password" placeholder="Tu contraseña" required /><button type="button" class="eye-button" :aria-label="showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'" @click="showPassword = !showPassword">◉</button></span>
            </label>
            <button class="primary-button" type="submit" :disabled="busy">{{ busy ? 'Ingresando…' : 'Iniciar sesión' }} <span>→</span></button>
          </form>

          <form v-else-if="screen === 'register'" class="form-fields compact-form" @submit.prevent="submitRegistration">
            <div class="two-columns">
              <label class="field"><span>Primer nombre</span><input v-model.trim="registration.first_name" autocomplete="given-name" minlength="3" maxlength="15" pattern="[a-zA-ZáéíóúÁÉÍÓÚñÑ]+" placeholder="Tu nombre" required /></label>
              <label class="field"><span>Segundo nombre <small>Opcional</small></span><input v-model.trim="registration.middle_name" minlength="3" maxlength="15" pattern="[a-zA-ZáéíóúÁÉÍÓÚñÑ]+" placeholder="Segundo nombre" /></label>
              <label class="field"><span>Primer apellido</span><input v-model.trim="registration.first_surname" autocomplete="family-name" minlength="3" maxlength="17" pattern="[a-zA-ZáéíóúÁÉÍÓÚñÑ]+" placeholder="Tu apellido" required /></label>
              <label class="field"><span>Segundo apellido <small>Opcional</small></span><input v-model.trim="registration.middle_surname" minlength="3" maxlength="17" pattern="[a-zA-ZáéíóúÁÉÍÓÚñÑ]+" placeholder="Segundo apellido" /></label>
            </div>
            <label class="field"><span>Correo electrónico</span><input v-model.trim="registration.email" type="email" autocomplete="email" maxlength="255" placeholder="tu@correo.com" required /></label>
            <label class="field"><span>Contraseña</span><input v-model="registration.password" :type="showRegisterPassword ? 'text' : 'password'" autocomplete="new-password" minlength="8" maxlength="128" placeholder="Mínimo 8 caracteres" required /></label>
            <label class="field"><span>Confirmar contraseña</span><input v-model="registration.confirm_password" type="password" autocomplete="new-password" minlength="8" maxlength="128" placeholder="Repite tu contraseña" required /></label>
            <button class="primary-button" type="submit" :disabled="busy">{{ busy ? 'Creando cuenta…' : 'Crear cuenta' }} <span>→</span></button>
          </form>

          <div v-else class="form-fields">
            <div class="step-indicator"><span :class="{ active: recoveryStep >= 1 }">1</span><i></i><span :class="{ active: recoveryStep >= 2 }">2</span><i></i><span :class="{ active: recoveryStep >= 3 }">3</span></div>
            <form v-if="recoveryStep === 1" class="form-fields" @submit.prevent="sendRestoreCode">
              <p class="helper-copy">Ingresa el correo asociado a tu cuenta. Si existe, recibirás un código de verificación de seis dígitos.</p>
              <label class="field"><span>Correo electrónico</span><input v-model.trim="recovery.email" type="email" autocomplete="email" placeholder="tu@correo.com" maxlength="255" required /></label>
              <button class="primary-button" type="submit" :disabled="busy">{{ busy ? 'Enviando…' : 'Enviar código' }} <span>→</span></button>
            </form>
            <form v-else-if="recoveryStep === 2" class="form-fields" @submit.prevent="checkRestoreCode">
              <p class="helper-copy">Introduce el código de seis dígitos enviado a <strong>{{ recovery.email }}</strong>.</p>
              <label class="field"><span>Código de verificación</span><input v-model.trim="recovery.restore_code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6}" minlength="6" maxlength="6" placeholder="000000" required /></label>
              <button class="primary-button" type="submit" :disabled="busy">{{ busy ? 'Verificando…' : 'Verificar código' }} <span>→</span></button>
              <button class="secondary-button" type="button" @click="recoveryStep = 1">Cambiar correo</button>
            </form>
            <form v-else class="form-fields" @submit.prevent="saveNewPassword">
              <p class="helper-copy">Código validado. Define una contraseña nueva para tu cuenta.</p>
              <label class="field"><span>Nueva contraseña</span><input v-model="recovery.new_password" type="password" autocomplete="new-password" minlength="8" maxlength="128" required /></label>
              <label class="field"><span>Confirmar contraseña</span><input v-model="recovery.confirm_password" type="password" autocomplete="new-password" minlength="8" maxlength="128" required /></label>
              <button class="primary-button" type="submit" :disabled="busy">{{ busy ? 'Actualizando…' : 'Actualizar contraseña' }} <span>→</span></button>
            </form>
          </div>

          <p class="switch-copy" v-if="screen === 'login'">¿No tienes cuenta? <button class="text-action strong" type="button" @click="navigate('register')">Regístrate gratis</button></p>
          <p class="switch-copy" v-else-if="screen === 'register'">¿Ya tienes cuenta? <button class="text-action strong" type="button" @click="navigate('login')">Inicia sesión</button></p>
          <p class="switch-copy" v-else>¿Recordaste tu contraseña? <button class="text-action strong" type="button" @click="navigate('login')">Volver al inicio de sesión</button></p>
          <p class="legal-copy">Al continuar aceptas nuestros <a href="#" @click.prevent>términos de uso</a> y <a href="#" @click.prevent>política de privacidad</a>.</p>
        </template>

        <section v-else class="signed-in">
          <div class="success-mark">✓</div>
          <p class="section-kicker">ACCESO CONFIRMADO</p>
          <h1>¡Bienvenido!</h1>
          <p class="subtitle">Has iniciado sesión como <strong>{{ currentUserEmail }}</strong>.</p>
          <p class="helper-copy">El backend entregó un token JWT. Esta primera entrega cubre registro, autenticación y recuperación de contraseña; el área de pedidos se integrará en los siguientes requisitos.</p>
          <button class="primary-button" type="button" @click="signOut">Cerrar sesión <span>→</span></button>
        </section>
      </div>
      <footer class="mobile-footer">© 2026 Canasta Express · Frescura local</footer>
    </section>
  </main>
</template>
