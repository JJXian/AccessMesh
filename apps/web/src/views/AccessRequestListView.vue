<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listAccessRequests } from '../api/accessmesh'
import type { AccessRequest } from '../types'

const rows = ref<AccessRequest[]>([])
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    rows.value = await listAccessRequests()
  } finally {
    loading.value = false
  }
}

onMounted(load)
window.addEventListener('accessmesh:identity-changed', load)
</script>

<template>
  <section>
    <div class="page-heading compact"><div><p class="eyebrow">REQUESTS</p><h1>权限申请</h1></div></div>
    <el-card shadow="never">
      <el-table :data="rows" v-loading="loading">
        <el-table-column prop="subject_external_id" label="权限主体" min-width="160" />
        <el-table-column prop="raw_request" label="申请内容" min-width="360" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="150" />
        <el-table-column prop="created_at" label="创建时间" min-width="190" />
        <el-table-column label="操作" width="100">
          <template #default="scope">
            <el-button link type="primary" @click="$router.push(`/requests/${scope.row.id}`)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </section>
</template>
