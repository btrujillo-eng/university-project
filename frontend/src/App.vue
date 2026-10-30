<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import {
  loginUser,
  loginWithGoogle,
  registerUser,
  requestRestoreCode,
  resetPassword,
  verifyRestoreCode,
} from './services/api'

const screen = ref('login')
const busy = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const accessToken = ref(localStorage.getItem('canasta_access_token') || '')
const currentUserEmail = ref('')
const rememberSession = ref(localStorage.getItem('canasta_remember_session') === 'true')
const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''

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
const codeSent = ref(false)
const showPassword = ref(false)
const showRegisterPassword = ref(false)
const showNewPassword = ref(false)

const screenTitle = computed(() => ({
  login: 'Bienvenido de vuelta',
  register: 'Crea tu cuenta',
  recovery: '¿Olvidaste tu contraseña?',
  newPassword: 'Crear nueva contraseña',
}[screen.value]))

const subtitle = computed(() => ({
  login: 'Ingresa a tu cuenta para hacer tus pedidos.',
  register: 'Completa el formulario para registrarte.',
  recovery: 'Ingresa tu correo electrónico asociado y el código de 6 dígitos que te enviamos para continuar.',
  newPassword: 'Establece tu nueva contraseña para volver a acceder a tu cuenta.',
}[screen.value]))

function clearMessages() {
  errorMessage.value = ''
  successMessage.value = ''
}

function navigate(nextScreen) {
  screen.value = nextScreen
  clearMessages()
  if (nextScreen === 'recovery') {
    recovery.restore_code = ''
    codeSent.value = false
  }
}

function getError(error) {
  return error instanceof Error ? error.message : 'Ocurrió un error inesperado.'
}

function saveToken(token) {
  accessToken.value = token
  if (rememberSession.value) {
    localStorage.setItem('canasta_access_token', token)
    localStorage.setItem('canasta_remember_session', 'true')
  } else {
    localStorage.removeItem('canasta_access_token')
    localStorage.removeItem('canasta_remember_session')
  }
}

async function submitLogin() {
  clearMessages()
  busy.value = true
  try {
    const result = await loginUser(login.email, login.password)
    saveToken(result.access_token)
    currentUserEmail.value = login.email
  } catch (error) {
    errorMessage.value = getError(error)
  } finally {
    busy.value = false
  }
}

async function submitRegistration() {
  clearMessages()
  if (registration.password !== registration.confirm_password) {
    errorMessage.value = 'Las contraseñas no coinciden.'
    return
  }
  busy.value = true
  try {
    const result = await registerUser(registration)
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
  if (!recovery.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(recovery.email)) return
  clearMessages()
  busy.value = true
  try {
    const result = await requestRestoreCode(recovery.email)
    codeSent.value = true
    successMessage.value = result.message || 'Si el correo está registrado, recibirás un código de verificación.'
  } catch (error) {
    errorMessage.value = getError(error)
  } finally {
    busy.value = false
  }
}

async function submitRecovery() {
  clearMessages()
  if (!codeSent.value) {
    await sendRestoreCode()
    return
  }
  busy.value = true
  try {
    const result = await verifyRestoreCode(recovery.email, recovery.restore_code)
    successMessage.value = result.message || 'Código verificado correctamente.'
    screen.value = 'newPassword'
  } catch (error) {
    errorMessage.value = getError(error)
  } finally {
    busy.value = false
  }
}

async function submitNewPassword() {
  clearMessages()
  if (recovery.new_password !== recovery.confirm_password) {
    errorMessage.value = 'Las contraseñas no coinciden.'
    return
  }
  busy.value = true
  try {
    const result = await resetPassword(recovery.email, recovery.restore_code, recovery.new_password)
    navigate('login')
    successMessage.value = result.message || 'Tu contraseña fue actualizada. Ya puedes iniciar sesión.'
    recovery.new_password = ''
    recovery.confirm_password = ''
    recovery.restore_code = ''
    codeSent.value = false
  } catch (error) {
    errorMessage.value = getError(error)
  } finally {
    busy.value = false
  }
}

function handleRememberChange() {
  if (!rememberSession.value) {
    localStorage.removeItem('canasta_access_token')
    localStorage.removeItem('canasta_remember_session')
  } else if (accessToken.value) {
    localStorage.setItem('canasta_access_token', accessToken.value)
    localStorage.setItem('canasta_remember_session', 'true')
  }
}

function handleGoogleCredential(response) {
  if (!response?.credential) {
    errorMessage.value = 'No fue posible obtener las credenciales de Google.'
    return
  }
  busy.value = true
  clearMessages()
  loginWithGoogle(response.credential)
    .then((result) => {
      saveToken(result.access_token)
      currentUserEmail.value = 'tu cuenta de Google'
    })
    .catch((error) => { errorMessage.value = getError(error) })
    .finally(() => { busy.value = false })
}

function startGoogleLogin() {
  clearMessages()
  if (!googleClientId) {
    errorMessage.value = 'El inicio de sesión con Google requiere configurar VITE_GOOGLE_CLIENT_ID.'
    return
  }
  if (!window.google?.accounts?.id) {
    errorMessage.value = 'No se pudo cargar el servicio de inicio de sesión de Google.'
    return
  }
  window.google.accounts.id.initialize({
    client_id: googleClientId,
    callback: handleGoogleCredential,
  })
  window.google.accounts.id.prompt()
}

function signOut() {
  accessToken.value = ''
  currentUserEmail.value = ''
  login.password = ''
  localStorage.removeItem('canasta_access_token')
  localStorage.removeItem('canasta_remember_session')
  rememberSession.value = false
  successMessage.value = 'Has cerrado sesión.'
}

onMounted(() => {
  if (accessToken.value) currentUserEmail.value = 'tu cuenta'
})
</script>

<template>
  <main class="auth-layout">
    <section class="story-panel" aria-label="Canasta Express">
      <div class="story-overlay"></div>
      <div class="story-copy">
        <p class="eyebrow"><span class="sprout">♧</span> PRODUCTO FRESCO <i></i> COSECHA DIARIA</p>
        <h2>Del campo a tu <em>mesa</em>,<br />directo y sin rodeos.</h2>
        <p class="story-description">Legumbres, granos y verduras de temporada seleccionadas cada mañana por nuestros proveedores locales.</p>
      </div>
    </section>

    <section class="form-panel">
      <div class="form-content">
        <header class="brand">
          <div class="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none"><path d="M12 20V9m0 0c-4.4 0-6.5-2.2-6.5-6 4.3 0 6.5 2.1 6.5 6Zm0 2c0-4.2 2.1-6.2 6.5-6.2 0 4.1-2.1 6.2-6.5 6.2Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </div>
          <div class="brand-copy"><strong>Canasta Express</strong><span>Legumbrería &amp; Verdulería Online</span></div>
        </header>

        <template v-if="!accessToken">
          <div class="heading">
            <h1>{{ screenTitle }}</h1>
            <p class="subtitle">{{ subtitle }}</p>
          </div>

          <div v-if="errorMessage" class="notice error" role="alert">{{ errorMessage }}</div>
          <div v-if="successMessage" class="notice success" role="status">{{ successMessage }}</div>

          <form v-if="screen === 'login'" class="fields login-fields" @submit.prevent="submitLogin">
            <label class="field">
              <span>Correo electrónico</span>
              <input v-model.trim="login.email" type="email" autocomplete="email" placeholder="tu@correo.com" maxlength="255" required />
            </label>
            <label class="field">
              <span class="field-heading"><span>Contraseña</span><button type="button" class="inline-link" @click="navigate('recovery')">¿Olvidaste tu contraseña?</button></span>
              <span class="password-wrap"><input v-model="login.password" :type="showPassword ? 'text' : 'password'" autocomplete="current-password" placeholder="••••••••" required /><button type="button" class="eye-toggle" :aria-label="showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'" @click="showPassword = !showPassword"><svg viewBox="0 0 24 24" fill="none"><path d="M2.5 12s3.3-6 9.5-6 9.5 6 9.5 6-3.3 6-9.5 6-9.5-6-9.5-6Z" stroke="currentColor" stroke-width="1.5"/><circle cx="12" cy="12" r="2.7" stroke="currentColor" stroke-width="1.5"/></svg></button></span>
            </label>
            <label class="remember-row"><input v-model="rememberSession" type="checkbox" @change="handleRememberChange" /><span>Recordar sesión</span></label>
            <button class="primary-button" type="submit" :disabled="busy">{{ busy ? 'Ingresando…' : 'Iniciar sesión' }}</button>
          </form>

          <form v-else-if="screen === 'register'" class="fields register-fields" @submit.prevent="submitRegistration">
            <div class="name-grid">
              <label class="field"><span>Primer nombre</span><input v-model.trim="registration.first_name" autocomplete="given-name" minlength="3" maxlength="15" placeholder="Tu nombre" required /></label>
              <label class="field"><span>Segundo nombre <small>Opcional</small></span><input v-model.trim="registration.middle_name" minlength="3" maxlength="15" placeholder="Segundo nombre" /></label>
              <label class="field"><span>Primer apellido</span><input v-model.trim="registration.first_surname" autocomplete="family-name" minlength="3" maxlength="17" placeholder="Tu apellido" required /></label>
              <label class="field"><span>Segundo apellido <small>Opcional</small></span><input v-model.trim="registration.middle_surname" minlength="3" maxlength="17" placeholder="Segundo apellido" /></label>
            </div>
            <label class="field"><span>Correo electrónico</span><input v-model.trim="registration.email" type="email" autocomplete="email" maxlength="255" placeholder="tu@correo.com" required /></label>
            <label class="field"><span>Contraseña</span><span class="password-wrap"><input v-model="registration.password" :type="showRegisterPassword ? 'text' : 'password'" autocomplete="new-password" minlength="8" maxlength="128" placeholder="••••••••" required /><button type="button" class="eye-toggle" aria-label="Mostrar u ocultar contraseña" @click="showRegisterPassword = !showRegisterPassword"><svg viewBox="0 0 24 24" fill="none"><path d="M2.5 12s3.3-6 9.5-6 9.5 6 9.5 6-3.3 6-9.5 6-9.5-6-9.5-6Z" stroke="currentColor" stroke-width="1.5"/><circle cx="12" cy="12" r="2.7" stroke="currentColor" stroke-width="1.5"/></svg></button></span></label>
            <label class="field"><span>Confirmar contraseña</span><input v-model="registration.confirm_password" type="password" autocomplete="new-password" minlength="8" maxlength="128" placeholder="••••••••" required /></label>
            <button class="primary-button" type="submit" :disabled="busy">{{ busy ? 'Registrando…' : 'Registrarse' }}</button>
          </form>

          <form v-else-if="screen === 'recovery'" class="fields recovery-fields" @submit.prevent="submitRecovery">
            <label class="field"><span>Correo electrónico</span><input v-model.trim="recovery.email" type="email" autocomplete="email" maxlength="255" placeholder="tu@correo.com" required @blur="sendRestoreCode" /></label>
            <div class="field">
              <span>Código de verificación (6 dígitos)</span>
              <div class="code-inputs" @paste.prevent="(event) => recovery.restore_code = event.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)">
                <input v-for="index in 6" :key="index" :value="recovery.restore_code[index - 1] || ''" inputmode="numeric" maxlength="1" :aria-label="'Dígito ' + index + ' del código'" @input="(event) => { const digits = recovery.restore_code.split(''); digits[index - 1] = event.target.value.replace(/\D/g, '').slice(-1); recovery.restore_code = digits.join('').slice(0, 6) }" />
              </div>
              <p v-if="!codeSent" class="field-hint">Ingresa tu correo para enviarte el código de verificación.</p>
            </div>
            <button class="primary-button" type="submit" :disabled="busy || !recovery.email || (codeSent && recovery.restore_code.length !== 6)">{{ busy ? 'Procesando…' : 'Verificar código' }}</button>
          </form>

          <form v-else class="fields new-password-fields" @submit.prevent="submitNewPassword">
            <label class="field"><span>Nueva contraseña</span><span class="password-wrap"><input v-model="recovery.new_password" :type="showNewPassword ? 'text' : 'password'" autocomplete="new-password" minlength="8" maxlength="128" placeholder="••••••••" required /><button type="button" class="eye-toggle" aria-label="Mostrar u ocultar contraseña" @click="showNewPassword = !showNewPassword"><svg viewBox="0 0 24 24" fill="none"><path d="M2.5 12s3.3-6 9.5-6 9.5 6 9.5 6-3.3 6-9.5 6-9.5-6-9.5-6Z" stroke="currentColor" stroke-width="1.5"/><circle cx="12" cy="12" r="2.7" stroke="currentColor" stroke-width="1.5"/></svg></button></span></label>
            <label class="field"><span>Confirmar nueva contraseña</span><input v-model="recovery.confirm_password" type="password" autocomplete="new-password" minlength="8" maxlength="128" placeholder="••••••••" required /></label>
            <button class="primary-button" type="submit" :disabled="busy">{{ busy ? 'Actualizando…' : 'Actualizar contraseña' }}</button>
          </form>

          <div v-if="screen !== 'newPassword'" class="social-divider"><span></span><p>o continuar con</p><span></span></div>
          <button v-if="screen !== 'newPassword'" class="google-button" type="button" :disabled="busy" @click="startGoogleLogin"><svg viewBox="0 0 48 48" aria-hidden="true"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5Z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.24 5.48-4.7 7.18l7.2 5.59c4.2-3.88 7.54-9.6 7.54-17.24Z"/><path fill="#FBBC05" d="M10.54 28.59A14.4 14.4 0 0 1 9.75 24c0-1.59.27-3.13.75-4.59l-7.98-6.19A23.9 23.9 0 0 0 0 24c0 3.88.93 7.55 2.56 10.78l7.98-6.19Z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.9-5.79l-7.2-5.59c-2 1.35-4.55 2.15-8.7 2.15-6.26 0-11.57-4.22-13.46-9.91l-7.98 6.19C6.51 43.62 14.62 48 24 48Z"/></svg>Iniciar con Google</button>

          <p v-if="screen === 'login'" class="switch-copy">¿No tienes cuenta? <button type="button" class="inline-link" @click="navigate('register')">Registrate gratis</button></p>
          <p v-else-if="screen === 'register'" class="switch-copy">¿Ya tienes cuenta? <button type="button" class="inline-link" @click="navigate('login')">Inicia sesión</button></p>
          <p v-else-if="screen === 'recovery'" class="switch-copy">¿Recordaste tu contraseña? <button type="button" class="inline-link" @click="navigate('login')">Volver a Iniciar sesión</button></p>
          <p v-else class="switch-copy"><button type="button" class="inline-link" @click="navigate('login')">Volver a Iniciar sesión</button></p>
        </template>

        <section v-else class="signed-in">
          <div class="success-icon">✓</div>
          <h1>¡Bienvenido!</h1>
          <p class="subtitle">Has iniciado sesión como <strong>{{ currentUserEmail }}</strong>.</p>
          <p class="signed-in-copy">Tu sesión se inició correctamente. Ya puedes continuar con Canasta Express.</p>
          <button class="primary-button" type="button" @click="signOut">Cerrar sesión</button>
        </section>
      </div>
    </section>
  </main>
</template>
