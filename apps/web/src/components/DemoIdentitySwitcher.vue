<script setup lang="ts">
import { onMounted } from 'vue'
import { ElMessage } from 'element-plus'

import { listDemoUsers } from '../api/accessmesh'
import { useIdentityStore } from '../stores/identity'

const identity = useIdentityStore()

// 组件挂载后加载可选身份；失败时保留默认身份并提示后端连接问题。
onMounted(async () => {
  try {
    identity.setUsers(await listDemoUsers())
  } catch {
    ElMessage.warning('演示身份加载失败，请确认后端已启动')
  }
})
</script>

<template>
  <div class="identity-switcher">
    <span>当前模拟身份</span>
    <el-select
      :model-value="identity.subjectId"
      size="small"
      style="width: 180px"
      @update:model-value="identity.selectSubject"
    >
      <el-option
        v-for="user in identity.users"
        :key="user.external_id"
        :label="`${user.display_name} · ${user.role}`"
        :value="user.external_id"
      />
    </el-select>
  </div>
</template>
