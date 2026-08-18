<template>
  <section>
    <div class="page-heading">
      <div>
        <p class="eyebrow">ACCESS GOVERNANCE</p>
        <h1>把Agent建议关在确定性策略边界内</h1>
        <p>自然语言申请、最小权限规划、OPA校验、人工审批、执行验证与审计闭环。</p>
      </div>
      <el-button type="primary" size="large" @click="$router.push('/requests/new')">
        创建申请
      </el-button>
    </div>
    <el-alert
      title="当前为个人开源仿真环境"
      description="演示身份通过请求头切换，资源适配器使用Mock实现，不可用于真实生产授权。"
      type="warning"
      show-icon
      :closable="false"
    />
    <div class="metric-grid">
      <el-card shadow="never"><span>Agent角色</span><strong>6</strong><small>规划与复核职责隔离</small></el-card>
      <el-card shadow="never"><span>策略决策</span><strong>OPA</strong><small>LLM不能覆盖拒绝</small></el-card>
      <el-card shadow="never"><span>资源适配器</span><strong>3</strong><small>GitLab / DB / Cloud</small></el-card>
      <el-card shadow="never"><span>可靠性</span><strong>Saga</strong><small>幂等、补偿、验证</small></el-card>
    </div>
  </section>
</template>
