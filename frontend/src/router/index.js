import { createRouter, createWebHistory } from 'vue-router';
import StatusPage from '../views/StatusPage.vue';
import ServiceDetail from '../views/ServiceDetail.vue';
import Monitor from '../views/Monitor.vue';
import Monitor2 from '../views/Monitor2.vue';
import AdminLayout from '../views/admin/AdminLayout.vue';
import Dashboard from '../views/admin/Dashboard.vue';
import Sections from '../views/admin/Sections.vue';
import Services from '../views/admin/Services.vue';
import Incidents from '../views/admin/Incidents.vue';
import Maintenance from '../views/admin/Maintenance.vue';
import Tokens from '../views/admin/Tokens.vue';
import Users from '../views/admin/Users.vue';
import Notifications from '../views/admin/Notifications.vue';
import Monitors from '../views/admin/Monitors.vue';
import Metrics  from '../views/admin/Metrics.vue';
import Settings from '../views/admin/Settings.vue';

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: StatusPage },
    { path: '/monitor', component: Monitor },
    { path: '/monitor2', component: Monitor2 },
    { path: '/services/:slug', component: ServiceDetail },
    {
      path: '/admin',
      component: AdminLayout,
      children: [
        { path: '',            component: Dashboard   },
        { path: 'sections',   component: Sections    },
        { path: 'services',   component: Services    },
        { path: 'incidents',  component: Incidents   },
        { path: 'maintenance',component: Maintenance },
        { path: 'monitors',      component: Monitors      },
        { path: 'metrics',       component: Metrics       },
        { path: 'notifications', component: Notifications },
        { path: 'tokens',        component: Tokens        },
        { path: 'users',      component: Users       },
        { path: 'settings',   component: Settings    },
      ],
    },
  ],
});
