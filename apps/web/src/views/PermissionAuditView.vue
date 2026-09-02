<script setup lang="ts">
import {
  onBeforeUnmount,
  onMounted,
  ref,
} from 'vue'
import { ElMessage } from 'element-plus'

import { listActivePermissions } from '../api/accessmesh'
import { useIdentityStore } from '../stores/identity'
import type { PermissionInstance } from '../types'
import { formatDateTime } from '../utils/dateTime'

const identity = useIdentityStore()

const rows = ref<PermissionInstance[]>([])
const loading = ref(false)

/** 加载当前身份可见的有效权限。 */
async function load() {
  loading.value = true

  try {
    rows.value = await listActivePermissions()
  } catch {
    ElMessage.error('有效权限加载失败，请确认后端已启动')
  } finally {
    loading.value = false
  }
}

/** 优先显示主体中文名，无法匹配时回退到外部身份标识。 */
function formatSubject(externalId: string): string {
  const subject = identity.users.find(
    (user) => user.external_id === externalId,
  )
  return subject?.display_name ?? externalId
}

onMounted(load)
window.addEventListener('accessmesh:identity-changed', load)

onBeforeUnmount(() => {
  window.removeEventListener(
    'accessmesh:identity-changed',
    load,
  )
})
</script>

<template>
  <section>
    <div class="page-heading compact">
      <div>
        <p class="eyebrow">PERMISSIONS & AUDIT</p>
        <h1>有效权限与审计</h1>
        <p>展示已经通过执行验证、当前仍处于生效状态的权限。</p>
      </div>
    </div>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>有效权限</span>
          <el-tag type="success">ACTIVE</el-tag>
        </div>
      </template>

      <el-table
        v-loading="loading"
        :data="rows"
        empty-text="当前没有有效权限"
      >
        <el-table-column label="权限主体" min-width="140">
          <template #default="scope">
            {{ formatSubject(scope.row.subject_external_id) }}
          </template>
        </el-table-column>

        <el-table-column
          prop="resource_name"
          label="资源"
          min-width="180"
        />

        <el-table-column
          prop="permission"
          label="权限"
          min-width="130"
        />

        <el-table-column label="状态" width="120">
          <template #default>
            <el-tag type="success">已生效</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="生效时间" min-width="190">
          <template #default="scope">
            {{ formatDateTime(scope.row.granted_at) }}
          </template>
        </el-table-column>

        <el-table-column label="到期时间" min-width="190">
          <template #default="scope">
            {{ formatDateTime(scope.row.expires_at) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never" class="section-card">
      <template #header>审计事件</template>
      <el-empty description="下一步将接入按申请、主体和资源筛选的审计时间线。" />
    </el-card>
  </section>
</template>