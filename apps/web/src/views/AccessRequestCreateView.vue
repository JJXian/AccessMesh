<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { createAccessRequest, listDemoUsers } from '../api/accessmesh'
import type { DemoUser } from '../types'

const router = useRouter()
const loading = ref(false)
const users = ref<DemoUser[]>([])
const form = reactive({
  subject_external_id: 'user-requester',
  request_text: '我需要支付项目GitLab只读权限和测试数据库查询权限，有效期30天，用于排查对账问题。',
})

onMounted(async () => {
  users.value = await listDemoUsers()
})

/** 为每次用户提交生成唯一请求号，随后跳转到新申请详情。 */
async function submit() {
  loading.value = true
  try {
    const result = await createAccessRequest({
      ...form,
      // 后端使用该值实现创建接口幂等，避免网络重试产生重复申请。
      client_request_id: `web-${crypto.randomUUID()}`,
    })
    ElMessage.success('权限申请已创建')
    await router.push(`/requests/${result.id}`)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="narrow-page">
    <div class="page-heading compact">
      <div><p class="eyebrow">NEW REQUEST</p><h1>创建权限申请</h1></div>
    </div>
    <el-card shadow="never">
      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="权限主体">
          <el-select v-model="form.subject_external_id" style="width: 100%">
            <el-option
              v-for="user in users"
              :key="user.external_id"
              :label="`${user.display_name} · ${user.department}`"
              :value="user.external_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="任务与权限需求">
          <el-input v-model="form.request_text" type="textarea" :rows="7" maxlength="4000" show-word-limit />
        </el-form-item>
        <el-alert
          title="请描述任务、目标资源、所需操作和期限。Agent会提出候选方案，但不能直接授权。"
          type="info"
          :closable="false"
        />
        <div class="form-actions">
          <el-button type="primary" :loading="loading" @click="submit">提交申请</el-button>
        </div>
      </el-form>
    </el-card>
  </section>
</template>
