import Vue from 'vue'
import VueRouter from 'vue-router'
import App from './App.vue'
import Program from './Program.vue'
import Metrics from './Metrics.vue'
import BootstrapVue from 'bootstrap-vue'
import feather from 'vue-icon'
import VueGoogleCharts from 'vue-google-charts'
var VueCookie = require('vue-cookie');
// Tell Vue to use the plugin
Vue.use(VueCookie);
Vue.use(VueRouter);
Vue.use(BootstrapVue);
Vue.use(feather, 'v-icon');
Vue.use(VueGoogleCharts);
import 'bootstrap/dist/css/bootstrap.css'
import 'bootstrap-vue/dist/bootstrap-vue.css'

Vue.config.productionTip = false

const router = new VueRouter({
    routes: [
        {
        	path: '/',
        	component: Program
    	},

    	{
        	path: '/metrics/:job_id?',
        	component: Metrics
    	},
    ]
})

new Vue({
  router,
  render: h => h(App),
  
}).$mount('#app')
