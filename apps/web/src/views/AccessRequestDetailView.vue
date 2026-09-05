<script setup lang="ts">
import {
  computed,
  onBeforeUnmount,
  onMounted,
  ref,
} from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'

import { getAccessRequestDetail } from '../api/accessmesh'
import { useIdentityStore } from '../stores/identity'
import type {
  AccessRequestDetail,
  AuditEvent,
  PolicyDecisionDetail,
  ProposedGrantDetail,
} from '../types'
import {
  formatAuditEventType,
  formatSystemActor,
  getAuditEventTagType,
} from '../utils/auditEvent'
import { formatDateTime } from '../utils/dateTime'
import { getRequestStatusMeta } from '../utils/requestStatus'

const route = useRoute()
const router = useRouter()
const identity = useIdentityStore()

const detail = ref<AccessRequestDetail>()
const loading = ref(false)

const request = computed(() => detail.value?.request)
const statusMeta = computed(() =>
  request.value
    ? getRequestStatusMeta(request.value.status)
    : getRequestStatusMeta('SUBMITTED'),
)

/** 根据申请状态计算当前已经到达的工作流步骤。 */
const workflowActive = computed(() => {
  const status = request.value?.status
  const stepByStatus: Record<string, number> = {
    SUBMITTED: 1,
    PARSING_REQUEST: 1,
    NEED_CLARIFICATION: 1,
    COLLECTING_CONTEXT: 1,
    PLANNING: 2,
    POLICY_DENIED: 3,
    PENDING_APPROVAL: 3,
    APPROVED: 4,
    REJECTED: 4,
    EXECUTING: 5,
    COMPENSATING: 5,
    VERIFYING: 5,
    FAILED: 5,
    ACTIVE: 5,
    REVOKED: 6,
  }
  return stepByStatus[status ?? 'SUBMITTED'] ?? 1
})

/** 失败和拒绝状态在工作流步骤上使用红色，其余使用默认进行中颜色。 */
const workflowProcessStatus = computed<'process' | 'error'>(() => {
  const failedStatuses = ['POLICY_DENIED', 'REJECTED', 'FAILED']
  return failedStatuses.includes(request.value?.status ?? '')
    ? 'error'
    : 'process'
})

/** 加载当前身份有权查看的申请聚合详情。 */
async function loadDetail() {
  loading.value = true

  try {
    detail.value = await getAccessRequestDetail(String(route.params.id))
  } catch {
    detail.value = undefined
    ElMessage.error('申请详情加载失败，或当前身份无权查看该申请')
  } finally {
    loading.value = false
  }
}

/** 将用户外部标识转换为演示身份的中文名称。 */
function formatUser(externalId: string): string {
  const user = identity.users.find(
    (item) => item.external_id === externalId,
  )
  return user?.display_name ?? externalId
}

/** 系统组件显示固定中文名称，用户操作者显示身份中文名。 */
function formatActor(externalId: string): string {
  return formatSystemActor(externalId) ?? formatUser(externalId)
}

/** 将资源环境转换为中文。 */
function formatEnvironment(environment: string): string {
  const labels: Record<string, string> = {
    development: '开发环境',
    test: '测试环境',
    staging: '预发布环境',
    production: '生产环境',
  }
  return labels[environment] ?? environment
}

/** 将演示权限编码转换为中文含义，同时保留未知权限的原值。 */
function formatPermission(permission: string): string {
  const labels: Record<string, string> = {
    connect: '允许连接',
    read_only: '只读',
    read_write: '读写',
    ddl_admin: '结构管理',
    guest: '访客',
    reporter: '代码只读',
    developer: '代码开发',
    maintainer: '仓库维护',
  }
  return labels[permission] ?? permission
}

/** 获取候选方案对应的 OPA 决策。 */
function findPolicyDecision(
  grant: ProposedGrantDetail,
): PolicyDecisionDetail | undefined {
  return detail.value?.policy_decisions.find(
    (decision) => decision.proposed_grant_id === grant.id,
  )
}

/** 将 OPA 违规代码转换成申请人容易理解的中文说明。 */
function formatPolicyViolation(violation: Record<string, unknown>): string {
  const code = typeof violation.code === 'string' ? violation.code : ''
  const message = typeof violation.message === 'string'
    ? violation.message
    : ''
  const labels: Record<string, string> = {
    SUBJECT_INACTIVE: '权限主体当前不是在职状态',
    RESOURCE_DISABLED: '目标资源已停用，暂时不能申请',
    INVALID_PERMISSION: '候选权限不在该资源允许申请的范围内',
    DURATION_EXCEEDED: '申请期限超过当前环境允许的最长时间',
    CONTRACTOR_PRODUCTION_DENIED: '外包人员禁止访问生产环境资源',
  }

  return labels[code] || message || code || 'OPA 未返回具体拒绝原因'
}

/** 返回一条候选权限在页面上需要展示的策略说明。 */
function getPolicyExplanations(grant: ProposedGrantDetail): string[] {
  const decision = findPolicyDecision(grant)
  if (!decision) return ['尚未进行策略评估']
  if (decision.allow) return ['已通过全部策略检查']
  if (decision.violations.length === 0) return ['OPA 拒绝了申请，但未返回具体原因']

  return decision.violations.map(formatPolicyViolation)
}

/** 获取执行任务对应的候选资源名称。 */
function findGrantResource(proposedGrantId: string): string {
  return detail.value?.proposed_grants.find(
    (grant) => grant.id === proposedGrantId,
  )?.resource_name ?? proposedGrantId
}

/** 将风险等级转换为中文。 */
function formatRiskLevel(riskLevel: string): string {
  const labels: Record<string, string> = {
    low: '低风险',
    medium: '中风险',
    high: '高风险',
    critical: '严重风险',
    unknown: '未知',
  }
  return labels[riskLevel] ?? riskLevel
}

function riskTagType(
  riskLevel: string,
): 'success' | 'warning' | 'danger' | 'info' {
  if (riskLevel === 'low') return 'success'
  if (riskLevel === 'medium') return 'warning'
  if (riskLevel === 'high' || riskLevel === 'critical') return 'danger'
  return 'info'
}

/** 将审批决定转换为中文。 */
function formatApprovalDecision(decision: string): string {
  return decision === 'APPROVED' ? '审批通过' : '审批拒绝'
}

/** 将执行任务状态转换为中文。 */
function formatExecutionStatus(status: string): string {
  const labels: Record<string, string> = {
    PENDING: '等待执行',
    RUNNING: '正在执行',
    SUCCEEDED: '执行成功',
    FAILED: '执行失败',
    COMPENSATED: '已补偿撤销',
  }
  return labels[status] ?? status
}

function executionTagType(
  status: string,
): 'success' | 'warning' | 'danger' | 'info' | 'primary' {
  if (status === 'SUCCEEDED') return 'success'
  if (status === 'FAILED') return 'danger'
  if (status === 'RUNNING') return 'primary'
  if (status === 'COMPENSATED') return 'warning'
  return 'info'
}

/** 以格式化 JSON 展示策略、执行和审计原始数据。 */
function formatJson(value: unknown): string {
  return JSON.stringify(value, null, 2)
}

/** 审计时间线节点颜色与审计列表保持一致。 */
function timelineType(
  event: AuditEvent,
): 'success' | 'warning' | 'danger' | 'primary' | 'info' {
  return getAuditEventTagType(event.event_type)
}

onMounted(loadDetail)
window.addEventListener('accessmesh:identity-changed', loadDetail)

onBeforeUnmount(() => {
  window.removeEventListener('accessmesh:identity-changed', loadDetail)
})
</script>

<template>
  <section v-loading="loading" class="request-detail-page">
    <div class="page-heading compact">
      <div>
        <p class="eyebrow">REQUEST DETAIL</p>
        <h1>申请全链路详情</h1>
        <p>查看权限规划、策略判断、人工审批、授权执行和回收记录。</p>
      </div>
      <el-button @click="router.push('/requests')">返回申请记录</el-button>
    </div>

    <template v-if="detail && request">
      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>申请信息</span>
            <el-tag :type="statusMeta.type" size="large">
              {{ statusMeta.label }}
            </el-tag>
          </div>
        </template>

        <el-descriptions :column="2" border>
          <el-descriptions-item label="申请编号">
            {{ request.id }}
          </el-descriptions-item>
          <el-descriptions-item label="链路追踪编号">
            {{ request.trace_id }}
          </el-descriptions-item>
          <el-descriptions-item label="申请人">
            {{ formatUser(request.requester_external_id) }}
          </el-descriptions-item>
          <el-descriptions-item label="权限主体">
            {{ formatUser(request.subject_external_id) }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDateTime(request.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="最后更新时间">
            {{ formatDateTime(request.updated_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="申请内容" :span="2">
            {{ request.raw_request }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card shadow="never" class="section-card">
        <template #header>工作流进度</template>
        <el-steps
          :active="workflowActive"
          :process-status="workflowProcessStatus"
          finish-status="success"
          align-center
        >
          <el-step title="提交申请" description="保存原始需求" />
          <el-step title="权限规划" description="生成最小权限方案" />
          <el-step title="策略评估" description="OPA 确定性校验" />
          <el-step title="人工审批" description="审批人确认风险" />
          <el-step title="执行验证" description="授权并验证结果" />
          <el-step title="到期回收" description="自动撤销权限" />
        </el-steps>
      </el-card>

      <el-card shadow="never" class="section-card">
        <template #header>
          <div class="card-header">
            <span>候选权限与策略决策</span>
            <el-tag type="info">{{ detail.proposed_grants.length }} 项</el-tag>
          </div>
        </template>

        <el-table
          :data="detail.proposed_grants"
          empty-text="当前没有候选权限方案"
        >
          <el-table-column prop="resource_name" label="资源" min-width="170" />
          <el-table-column label="环境" width="110">
            <template #default="scope">
              {{ formatEnvironment(scope.row.environment) }}
            </template>
          </el-table-column>
          <el-table-column prop="sensitivity" label="敏感等级" width="100" />
          <el-table-column label="建议权限" width="120">
            <template #default="scope">
              {{ formatPermission(scope.row.permission) }}
            </template>
          </el-table-column>
          <el-table-column label="期限" width="90">
            <template #default="scope">{{ scope.row.duration_days }} 天</template>
          </el-table-column>
          <el-table-column label="OPA 决策" width="110">
            <template #default="scope">
              <el-tag
                v-if="findPolicyDecision(scope.row)"
                :type="findPolicyDecision(scope.row)?.allow ? 'success' : 'danger'"
              >
                {{ findPolicyDecision(scope.row)?.allow ? '允许' : '拒绝' }}
              </el-tag>
              <span v-else>未评估</span>
            </template>
          </el-table-column>
          <el-table-column label="风险" width="100">
            <template #default="scope">
              <el-tag
                v-if="findPolicyDecision(scope.row)"
                :type="riskTagType(findPolicyDecision(scope.row)?.risk_level ?? '')"
                effect="plain"
              >
                {{ formatRiskLevel(findPolicyDecision(scope.row)?.risk_level ?? '') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="策略说明" min-width="250">
            <template #default="scope">
              <ul
                class="policy-explanation-list"
                :class="{
                  'is-denied': findPolicyDecision(scope.row)?.allow === false,
                }"
              >
                <li
                  v-for="explanation in getPolicyExplanations(scope.row)"
                  :key="explanation"
                >
                  {{ explanation }}
                </li>
              </ul>
            </template>
          </el-table-column>
          <el-table-column prop="reason" label="规划理由" min-width="260" />
          <el-table-column type="expand" width="48">
            <template #default="scope">
              <div class="detail-expand">
                <p><strong>资源标识：</strong>{{ scope.row.resource_external_id }}</p>
                <p><strong>规划版本：</strong>{{ scope.row.plan_version }}</p>
                <p>
                  <strong>证据引用：</strong>
                  {{ scope.row.evidence_refs.join('、') || '无' }}
                </p>
                <pre
                  v-if="findPolicyDecision(scope.row)"
                  class="audit-payload"
                >{{ formatJson(findPolicyDecision(scope.row)) }}</pre>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card shadow="never" class="section-card">
        <template #header>人工审批</template>
        <el-descriptions v-if="detail.approval" :column="2" border>
          <el-descriptions-item label="审批结果">
            <el-tag
              :type="detail.approval.decision === 'APPROVED' ? 'success' : 'danger'"
            >
              {{ formatApprovalDecision(detail.approval.decision) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="审批人">
            {{ formatUser(detail.approval.approver_external_id) }}
          </el-descriptions-item>
          <el-descriptions-item label="审批时间">
            {{ formatDateTime(detail.approval.decided_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="审批意见">
            {{ detail.approval.comment || '未填写审批意见' }}
          </el-descriptions-item>
        </el-descriptions>
        <el-empty v-else description="当前申请还没有人工审批记录" />
      </el-card>

      <el-card shadow="never" class="section-card">
        <template #header>授权执行</template>
        <el-table
          :data="detail.execution_tasks"
          empty-text="当前申请还没有执行任务"
        >
          <el-table-column label="资源" min-width="170">
            <template #default="scope">
              {{ findGrantResource(scope.row.proposed_grant_id) }}
            </template>
          </el-table-column>
          <el-table-column label="执行状态" width="120">
            <template #default="scope">
              <el-tag :type="executionTagType(scope.row.status)">
                {{ formatExecutionStatus(scope.row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="attempt_count" label="尝试次数" width="100" />
          <el-table-column label="执行时间" min-width="180">
            <template #default="scope">
              {{ formatDateTime(scope.row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column prop="error_message" label="错误信息" min-width="180">
            <template #default="scope">
              {{ scope.row.error_message || '无' }}
            </template>
          </el-table-column>
          <el-table-column type="expand" width="48">
            <template #default="scope">
              <div class="detail-expand">
                <strong>适配器执行结果</strong>
                <pre class="audit-payload">{{ formatJson(scope.row.result) }}</pre>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card shadow="never" class="section-card">
        <template #header>权限生命周期</template>
        <el-table
          :data="detail.permissions"
          empty-text="当前申请还没有生成权限实例"
        >
          <el-table-column prop="resource_name" label="资源" min-width="170" />
          <el-table-column label="权限" width="120">
            <template #default="scope">
              {{ formatPermission(scope.row.permission) }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="scope">
              <el-tag :type="scope.row.status === 'ACTIVE' ? 'success' : 'info'">
                {{ scope.row.status === 'ACTIVE' ? '已生效' : '已回收' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="生效时间" min-width="180">
            <template #default="scope">
              {{ formatDateTime(scope.row.granted_at) }}
            </template>
          </el-table-column>
          <el-table-column label="到期时间" min-width="180">
            <template #default="scope">
              {{ formatDateTime(scope.row.expires_at) }}
            </template>
          </el-table-column>
          <el-table-column label="回收信息" min-width="190">
            <template #default="scope">
              <template v-if="scope.row.revoked_at">
                {{ formatDateTime(scope.row.revoked_at) }}
                · {{ scope.row.revocation_reason || '已回收' }}
              </template>
              <span v-else>尚未回收</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card shadow="never" class="section-card">
        <template #header>
          <div class="card-header">
            <span>审计时间线</span>
            <el-tag type="info">{{ detail.audit_events.length }} 个事件</el-tag>
          </div>
        </template>

        <el-timeline class="request-audit-timeline">
          <el-timeline-item
            v-for="event in detail.audit_events"
            :key="event.id"
            :timestamp="formatDateTime(event.created_at)"
            :type="timelineType(event)"
            placement="top"
          >
            <div class="timeline-event">
              <div class="card-header">
                <el-tag :type="getAuditEventTagType(event.event_type)">
                  {{ formatAuditEventType(event.event_type) }}
                </el-tag>
                <span>操作者：{{ formatActor(event.actor_external_id) }}</span>
              </div>
              <el-collapse>
                <el-collapse-item title="查看事件载荷" :name="event.id">
                  <pre class="audit-payload">{{ formatJson(event.payload) }}</pre>
                </el-collapse-item>
              </el-collapse>
            </div>
          </el-timeline-item>
        </el-timeline>
      </el-card>
    </template>

    <el-empty
      v-else-if="!loading"
      description="没有找到申请详情，或当前身份无权查看"
    />
  </section>
</template>
