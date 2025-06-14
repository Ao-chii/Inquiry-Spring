import Vue from 'vue'
import App from './App.vue'
import router from './router'
import ElementUI from 'element-ui';
import Vuetify from 'vuetify'
import store from './store'
import 'vuetify/dist/vuetify.min.css';
import 'element-ui/lib/theme-chalk/index.css';

Vue.use(ElementUI);
Vue.use(Vuetify);
Vue.prototype.HOST = '/api';

const vuetify=new Vuetify()

Vue.config.productionTip = false

new Vue({
  store,
  router,
  vuetify,
  render: h => h(App)
}).$mount('#app')
