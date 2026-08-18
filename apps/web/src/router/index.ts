import { createRouter, createWebHistory } from 'vue-router'

import AccessRequestCreateView from '../views/AccessRequestCreateView.vue'
import AccessRequestDetailView from '../views/AccessRequestDetailView.vue'
import AccessRequestListView from '../views/AccessRequestListView.vue'
import ApprovalListView from '../views/ApprovalListView.vue'
import DashboardView from '../views/DashboardView.vue'
import PermissionAuditView from '../views/PermissionAuditView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: DashboardView },
    { path: '/requests', component: AccessRequestListView },
    { path: '/requests/new', component: AccessRequestCreateView },
    { path: '/requests/:id', component: AccessRequestDetailView },
    { path: '/approvals', component: ApprovalListView },
    { path: '/permissions', component: PermissionAuditView },
  ],
})

export default router
