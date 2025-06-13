import Vue from 'vue'
import VueRouter from 'vue-router'

Vue.use(VueRouter)

const routes = [
  {
    path: '/',
    name: 'homepage',
    component: () => import('../views/mainPage/homePage.vue')
  },
  {
    path: '/chat',
    name: 'chatpage',
    component: () => import('../views/mainPage/chatPage.vue')
  },
  {
    path: '/summarize',
    name: 'summarizepage',
    component: () => import('../views/mainPage/summarizePage.vue')
  },
  {
    path: '/test',
    name: 'testpage',
    component: () => import('../views/mainPage/testPage.vue')
  },
  {
    path: '/demo',
    name: 'demopage',
    component: () => import('../views/mainPage/demoPage.vue')
  },
  {
    path:'/project',
    name:'project',
    component: () => import('../views/guidePage/createProject.vue')
  },
  {
    path:'/login',
    name:'login',
    component: () => import('../views/guidePage/loginPage.vue')
  },

  {
    path: '/about',
    name: 'about',
    // route level code-splitting
    // this generates a separate chunk (about.[hash].js) for this route
    // which is lazy-loaded when the route is visited.
    component: () => import(/* webpackChunkName: "about" */ '../views/AboutView.vue')
  }
]

const router = new VueRouter({
  routes
})

export default router