<script setup lang="ts">
import {
  onBeforeUnmount,
  onMounted,
  ref,
} from 'vue'
import { ElMessage } from 'element-plus'

import { listAccessRequests } from '../api/accessmesh'
import { useIdentityStore } from '../stores/identity'
import type { AccessRequest } from '../types'
import { getRequestStatusMeta } from '../utils/requestStatus'

const identity = useIdentityStore()

const rows = ref<AccessRequest[]>([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)

/** 加载当前页的申请记录。 */
async function load() {
  loading.value = true

  try {
    const result = await listAccessRequests(
      currentPage.value,
      pageSize.value,
    )
    rows.value = result.items
    total.value = result.total
  } catch {
    ElMessage.error('申请记录加载失败，请确认后端已启动')
  } finally {
    loading.value = false
  }
}

/** 权限主体优先显示中文名称；用户目录尚未加载时回退显示外部标识。 */
function formatSubject(externalId: string): string {
  const subject = identity.users.find(
    (user) => user.external_id === externalId,
  )
  return subject?.display_name ?? externalId
}

/** 切换页码时只重新获取对应页的数据。 */
function handleCurrentPageChange(page: number) {
  currentPage.value = page
  void load()
}

/** 修改每页条数后回到第 1 页，避免当前页超出最大页数。 */
function handlePageSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  void load()
}

/** 切换演示身份后，从第 1 页重新加载该身份可见的申请。 */
function handleIdentityChanged() {
  currentPage.value = 1
  void load()
}

onMounted(load)
window.addEventListener(
  'accessmesh:identity-changed',
  handleIdentityChanged,
)

onBeforeUnmount(() => {
  window.removeEventListener(
    'accessmesh:identity-changed',
    handleIdentityChanged,
  )
})
</script>

<template>
  <section>
    <div class="page-heading compact">
      <div>
        <p class="eyebrow">REQUESTS</p>
        <h1>权限申请</h1>
        <p>查看当前身份有权限访问的申请记录。</p>
      </div>
    </div>

    <el-card shadow="never">
      <el-table
        v-loading="loading"
        :data="rows"
        empty-text="暂无申请记录"
      >
        <el-table-column label="权限主体" min-width="150">
          <template #default="scope">
            {{ formatSubject(scope.row.subject_external_id) }}
          </template>
        </el-table-column>

        <el-table-column
          prop="raw_request"
          label="申请内容"
          min-width="360"
          show-overflow-tooltip
        />

        <el-table-column label="状态" width="150">
          <template #default="scope">
            <el-tag
              :type="getRequestStatusMeta(scope.row.status).type"
              effect="light"
            >
              {{ getRequestStatusMeta(scope.row.status).label }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column
          prop="created_at"
          label="创建时间"
          min-width="190"
        />

        <el-table-column label="操作" width="100">
          <template #default="scope">
            <el-button
              link
              type="primary"
              @click="$router.push(`/requests/${scope.row.id}`)"
            >
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="table-pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @current-change="handleCurrentPageChange"
          @size-change="handlePageSizeChange"
        />
      </div>
    </el-card>
  </section>
</template>