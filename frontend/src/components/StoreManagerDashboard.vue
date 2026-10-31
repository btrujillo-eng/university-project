<script setup>
import { ref } from 'vue'
import AdminCatalog from './AdminCatalog.vue'
import StoreOperations from './StoreOperations.vue'
const props=defineProps({user:{type:Object,required:true},token:{type:String,required:true}})
const emit=defineEmits(['logout'])
const section=ref('catalog')
</script>
<template><main class="role-dashboard"><header class="role-dashboard-nav"><div class="role-dashboard-brand"><span class="customer-brand-mark">♧</span><span><strong>Canasta Express</strong><small>Panel de administración</small></span></div><nav><button :class="{active:section==='catalog'}" @click="section='catalog'">Catálogo</button><button :class="{active:section==='dispatch'}" @click="section='dispatch'">Asignación de pedidos</button></nav><button class="role-dashboard-exit" @click="emit('logout')">Cerrar sesión</button></header><AdminCatalog v-if="section==='catalog'" :user="user" :token="token" @logout="emit('logout')"/><StoreOperations v-else :user="user" :token="token" @logout="emit('logout')"/></main></template>