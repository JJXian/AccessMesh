<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { formatDateTime } from "../utils/dateTime";
import { createApproval, listPendingApprovals } from "../api/accessmesh";
import { useIdentityStore } from "../stores/identity";
import type { AccessRequest, ApprovalDecision } from "../types";

const identity = useIdentityStore();

const rows = ref<AccessRequest[]>([]);
const loading = ref(false);
const submitting = ref(false);

const dialogVisible = ref(false);
const selectedRequest = ref<AccessRequest>();
const selectedDecision = ref<ApprovalDecision>("APPROVED");
const comment = ref("");

const isApprover = computed(() => identity.currentUser?.role === "approver");

/** 重新从后端读取待审批任务，后端仍会校验当前身份是否具备 approver 角色。 */
async function load() {
  loading.value = true;

  try {
    rows.value = await listPendingApprovals();
  } catch {
    rows.value = [];

    // 普通申请人进入此页面时，接口会返回 403。
    // 前端提示只是改善体验，真正的权限控制仍在后端。
    if (isApprover.value) {
      ElMessage.error("待审批任务加载失败，请确认后端已启动");
    }
  } finally {
    loading.value = false;
  }
}

/** 打开审批对话框；拒绝时必须填写意见，规则由后端再次校验。 */
function openApprovalDialog(
  request: AccessRequest,
  decision: ApprovalDecision
) {
  selectedRequest.value = request;
  selectedDecision.value = decision;
  comment.value = "";
  dialogVisible.value = true;
}

/** 提交审批决定；成功后重新加载，而不是在前端手动修改列表。 */
async function submitApproval() {
  if (!selectedRequest.value) {
    return;
  }

  if (selectedDecision.value === "REJECTED" && !comment.value.trim()) {
    ElMessage.warning("拒绝申请时必须填写审批意见");
    return;
  }

  submitting.value = true;

  try {
    await createApproval(selectedRequest.value.id, {
      decision: selectedDecision.value,
      comment: comment.value.trim() || undefined,
    });

    ElMessage.success(
      selectedDecision.value === "APPROVED" ? "申请已通过审批" : "申请已拒绝"
    );

    dialogVisible.value = false;
    await load();
  } catch {
    // 常见原因：该申请已被其他审批人处理，或当前身份不再是审批人。
    ElMessage.error("审批失败，请刷新列表后重试");
  } finally {
    submitting.value = false;
  }
}

onMounted(load);

// 顶部身份切换器切换为 approver 后，自动刷新待审批列表。
window.addEventListener("accessmesh:identity-changed", load);

onBeforeUnmount(() => {
  window.removeEventListener("accessmesh:identity-changed", load);
});
</script>

<template>
  <section>
    <div class="page-heading compact">
      <div>
        <p class="eyebrow">APPROVALS</p>
        <h1>待审批任务</h1>
        <p>OPA 已通过的申请将在此等待人工最终决定。</p>
      </div>
    </div>

    <el-alert
      v-if="!isApprover"
      title="当前身份不是审批人"
      type="warning"
      :closable="false"
      show-icon
    >
      请在右上角将模拟身份切换为“演示审批人 · approver”。
    </el-alert>

    <el-card shadow="never" class="section-card">
      <el-table
        v-loading="loading"
        :data="rows"
        empty-text="当前没有待审批申请"
      >
        <el-table-column
          prop="subject_external_id"
          label="权限主体"
          min-width="160"
        />
        <el-table-column
          prop="raw_request"
          label="申请内容"
          min-width="360"
          show-overflow-tooltip
        />
        <el-table-column label="申请时间" min-width="190">
          <template #default="scope">
            {{ formatDateTime(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="160">
          <template #default>
            <el-tag type="warning">等待审批</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="190">
          <template #default="scope">
            <el-button
              type="success"
              :disabled="!isApprover"
              @click="openApprovalDialog(scope.row, 'APPROVED')"
            >
              通过
            </el-button>
            <el-button
              type="danger"
              plain
              :disabled="!isApprover"
              @click="openApprovalDialog(scope.row, 'REJECTED')"
            >
              拒绝
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="selectedDecision === 'APPROVED' ? '确认通过审批' : '确认拒绝申请'"
      width="520px"
    >
      <p v-if="selectedRequest">申请内容：{{ selectedRequest.raw_request }}</p>

      <el-form label-position="top">
        <el-form-item
          :label="
            selectedDecision === 'APPROVED'
              ? '审批意见（可选）'
              : '拒绝原因（必填）'
          "
        >
          <el-input
            v-model="comment"
            type="textarea"
            :rows="4"
            maxlength="2000"
            show-word-limit
            :placeholder="
              selectedDecision === 'APPROVED'
                ? '例如：同意用于支付问题排查。'
                : '请说明拒绝原因，便于申请人修改后重新提交。'
            "
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button
          :type="selectedDecision === 'APPROVED' ? 'success' : 'danger'"
          :loading="submitting"
          @click="submitApproval"
        >
          确认{{ selectedDecision === "APPROVED" ? "通过" : "拒绝" }}
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>