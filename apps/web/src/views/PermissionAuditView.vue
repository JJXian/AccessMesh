<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import {
  listActivePermissions,
  listAuditEvents,
  listResources,
} from '../api/accessmesh'
import { useIdentityStore } from '../stores/identity'
import type {
  AuditEvent,
  PermissionInstance,
  Resource,
} from '../types'
import { formatDateTime } from '../utils/dateTime'

const identity = useIdentityStore()

const rows = ref<PermissionInstance[]>([])
const permissionLoading = ref(false)
const auditRows = ref<AuditEvent[]>([])
const resources = ref<Resource[]>([])
const auditLoading = ref(false)
const auditTotal = ref(0)
const auditPage = ref(1)
const auditPageSize = ref(10)
const detailVisible = ref(false)
const selectedEvent = ref<AuditEvent | null>(null)

const filters = reactive({
  requestId: '',
  subjectExternalId: '',
  resourceExternalId: '',
  eventType: '',
})

const eventOptions = [
  { value: 'ACCESS_REQUEST_CREATED', label: '申请已创建' },
  { value: 'ACCESS_PLAN_CREATED', label: '权限方案已生成' },
  { value: 'ACCESS_POLICY_EVALUATED', label: '策略评估完成' },
  { value: 'ACCESS_REQUEST_APPROVED', label: '审批已通过' },
  { value: 'ACCESS_REQUEST_REJECTED', label: '审批已拒绝' },
  { value: 'ACCESS_EXECUTION_STARTED', label: '授权执行开始' },
  { value: 'ACCESS_EXECUTION_COMPLETED', label: '授权执行完成' },
  { value: 'ACCESS_EXECUTION_FAILED', label: '授权执行失败' },
]

/** 加载当前身份可见的有效权限。 */
async function loadPermissions() {
  permissionLoading.value = true

  try {
    rows.value = await listActivePermissions()
  } catch {
    ElMessage.error('有效权限加载失败，请确认后端已启动')
  } finally {
    permissionLoading.value = false
  }
}

/** 加载资源目录，为审计记录提供资源筛选项。 */
async function loadResources() {
  try {
    resources.value = await listResources()
  } catch {
    ElMessage.error('资源筛选项加载失败')
  }
}

/** 根据当前筛选条件加载一页审计事件。 */
async function loadAuditEvents() {
  auditLoading.value = true

  try {
    const result = await listAuditEvents({
      page: auditPage.value,
      page_size: auditPageSize.value,
      request_id: filters.requestId || undefined,
      subject_external_id: filters.subjectExternalId || undefined,
      resource_external_id: filters.resourceExternalId || undefined,
      event_type: filters.eventType || undefined,
    })
    auditRows.value = result.items
    auditTotal.value = result.total
  } catch {
    ElMessage.error('审计事件加载失败，请确认筛选条件是否正确')
  } finally {
    auditLoading.value = false
  }
}

/** 从第一页开始执行查询，避免筛选后停留在不存在的页码。 */
function searchAuditEvents() {
  auditPage.value = 1
  loadAuditEvents()
}

/** 清空全部查询条件并重新加载审计事件。 */
function resetAuditFilters() {
  filters.requestId = ''
  filters.subjectExternalId = ''
  filters.resourceExternalId = ''
  filters.eventType = ''
  searchAuditEvents()
}

/** 切换审计列表页码。 */
function changeAuditPage(page: number) {
  auditPage.value = page
  loadAuditEvents()
}

/** 切换每页条数，并从第一页重新查询。 */
function changeAuditPageSize(pageSize: number) {
  auditPageSize.value = pageSize
  auditPage.value = 1
  loadAuditEvents()
}

/** 优先显示主体中文名，无法匹配时回退到外部身份标识。 */
function formatSubject(externalId: string): string {
  const subject = identity.users.find(
    (user) => user.external_id === externalId,
  )
  return subject?.display_name ?? externalId
}

/** 将系统组件标识和用户标识转换成更容易理解的中文名称。 */
function formatActor(externalId: string): string {
  const systemActors: Record<string, string> = {
    'accessmesh-planner': '权限规划器',
    opa: 'OPA 策略引擎',
  }
  return systemActors[externalId] ?? formatSubject(externalId)
}

/** 将事件类型转换为中文业务动作。 */
function formatEventType(eventType: string): string {
  return eventOptions.find((item) => item.value === eventType)?.label ?? eventType
}

/** 用颜色区分正常、等待和失败事件。 */
function eventTagType(
  eventType: string,
): 'success' | 'warning' | 'danger' | 'primary' | 'info' {
  if (eventType.endsWith('COMPLETED') || eventType.endsWith('APPROVED')) {
    return 'success'
  }
  if (eventType.endsWith('FAILED') || eventType.endsWith('REJECTED')) {
    return 'danger'
  }
  if (eventType.includes('POLICY') || eventType.endsWith('STARTED')) {
    return 'warning'
  }
  return eventType.endsWith('CREATED') ? 'primary' : 'info'
}

/** 缩短表格中的申请编号，完整编号仍可在详情中查看。 */
function shortRequestId(requestId: string | null): string {
  return requestId?.slice(0, 8) ?? '系统事件'
}

/** 打开详情弹窗查看追踪编号和原始 JSON 载荷。 */
function showEventDetail(event: AuditEvent) {
  selectedEvent.value = event
  detailVisible.value = true
}

/** 以缩进 JSON 展示事件载荷，方便排查链路数据。 */
function formatPayload(payload: Record<string, unknown>): string {
  return JSON.stringify(payload, null, 2)
}

function reloadForIdentityChange() {
  auditPage.value = 1
  loadPermissions()
  loadAuditEvents()
}

onMounted(() => {
  loadPermissions()
  loadResources()
  loadAuditEvents()
})
window.addEventListener(
  'accessmesh:identity-changed',
  reloadForIdentityChange,
)

onBeforeUnmount(() => {
  window.removeEventListener(
    'accessmesh:identity-changed',
    reloadForIdentityChange,
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
        v-loading="permissionLoading"
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
      <template #header>
        <div class="card-header">
          <span>审计事件</span>
          <el-tag type="info">共 {{ auditTotal }} 条</el-tag>
        </div>
      </template>

      <el-form :inline="true" class="audit-filters">
        <el-form-item label="申请编号">
          <el-input
            v-model.trim="filters.requestId"
            clearable
            placeholder="输入完整 UUID"
            style="width: 220px"
            @keyup.enter="searchAuditEvents"
          />
        </el-form-item>

        <el-form-item label="权限主体">
          <el-select
            v-model="filters.subjectExternalId"
            clearable
            placeholder="全部主体"
            style="width: 160px"
          >
            <el-option
              v-for="user in identity.users"
              :key="user.external_id"
              :label="user.display_name"
              :value="user.external_id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="资源">
          <el-select
            v-model="filters.resourceExternalId"
            clearable
            placeholder="全部资源"
            style="width: 190px"
          >
            <el-option
              v-for="resource in resources"
              :key="resource.external_id"
              :label="resource.name"
              :value="resource.external_id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="事件类型">
          <el-select
            v-model="filters.eventType"
            clearable
            placeholder="全部事件"
            style="width: 180px"
          >
            <el-option
              v-for="event in eventOptions"
              :key="event.value"
              :label="event.label"
              :value="event.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="searchAuditEvents">查询</el-button>
          <el-button @click="resetAuditFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table
        v-loading="auditLoading"
        :data="auditRows"
        empty-text="没有符合条件的审计事件"
      >
        <el-table-column label="发生时间" min-width="180">
          <template #default="scope">
            {{ formatDateTime(scope.row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column label="事件" min-width="170">
          <template #default="scope">
            <el-tag :type="eventTagType(scope.row.event_type)">
              {{ formatEventType(scope.row.event_type) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作者" min-width="150">
          <template #default="scope">
            {{ formatActor(scope.row.actor_external_id) }}
          </template>
        </el-table-column>

        <el-table-column label="申请编号" min-width="120">
          <template #default="scope">
            <router-link
              v-if="scope.row.request_id"
              :to="`/requests/${scope.row.request_id}`"
              class="request-link"
            >
              {{ shortRequestId(scope.row.request_id) }}
            </router-link>
            <span v-else>系统事件</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="100" align="center">
          <template #default="scope">
            <el-button
              type="primary"
              link
              @click="showEventDetail(scope.row)"
            >
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="table-pagination">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next"
          :total="auditTotal"
          :current-page="auditPage"
          :page-size="auditPageSize"
          :page-sizes="[10, 20, 50]"
          @current-change="changeAuditPage"
          @size-change="changeAuditPageSize"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="detailVisible"
      title="审计事件详情"
      width="680px"
    >
      <el-descriptions v-if="selectedEvent" :column="1" border>
        <el-descriptions-item label="事件类型">
          {{ formatEventType(selectedEvent.event_type) }}
        </el-descriptions-item>
        <el-descriptions-item label="完整申请编号">
          {{ selectedEvent.request_id ?? '系统事件' }}
        </el-descriptions-item>
        <el-descriptions-item label="链路追踪编号">
          {{ selectedEvent.trace_id }}
        </el-descriptions-item>
        <el-descriptions-item label="操作者">
          {{ formatActor(selectedEvent.actor_external_id) }}
        </el-descriptions-item>
        <el-descriptions-item label="发生时间">
          {{ formatDateTime(selectedEvent.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="事件载荷">
          <pre class="audit-payload">{{ formatPayload(selectedEvent.payload) }}</pre>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </section>
</template>
