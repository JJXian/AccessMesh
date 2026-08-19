<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { getAccessRequest } from '../api/accessmesh'
import type { AccessRequest } from '../types'

const route = useRoute()
const request = ref<AccessRequest>()

// 路由参数始终先归一化为字符串，再交由类型明确的 API 方法处理。
onMounted(async () => {
  request.value = await getAccessRequest(String(route.params.id))
})
</script>

<template>
  <section v-if="request" class="narrow-page">
    <div class="page-heading compact"><div><p class="eyebrow">REQUEST DETAIL</p><h1>申请详情</h1></div></div>
    <el-card shadow="never">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="申请ID">{{ request.id }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ request.status }}</el-descriptions-item>
        <el-descriptions-item label="权限主体">{{ request.subject_external_id }}</el-descriptions-item>
        <el-descriptions-item label="申请内容">{{ request.raw_request }}</el-descriptions-item>
        <el-descriptions-item label="Trace ID">{{ request.trace_id }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
    <el-card shadow="never" class="section-card">
      <template #header>工作流时间线</template>
      <el-steps :active="1" align-center>
        <el-step title="已提交" />
        <el-step title="Agent规划" />
        <el-step title="OPA策略" />
        <el-step title="人工审批" />
        <el-step title="执行验证" />
      </el-steps>
      <el-empty description="当前已完成基础框架，Agent执行节点将在后续阶段接入" />
    </el-card>
  </section>
</template>
