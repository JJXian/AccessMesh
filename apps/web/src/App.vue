<script setup lang="ts">
import DemoIdentitySwitcher from './components/DemoIdentitySwitcher.vue'
</script>

<template>
  <el-container class="app-shell">
    <el-aside width="236px" class="sidebar">
      <div class="brand">
        <div class="brand-mark">A</div>
        <div>
          <strong>AccessMesh</strong>
          <span>Policy-governed Agents</span>
        </div>
      </div>
      <el-menu router :default-active="$route.path" class="nav-menu">
        <el-menu-item index="/">概览</el-menu-item>
        <el-menu-item index="/requests/new">创建权限申请</el-menu-item>
        <el-menu-item index="/requests">申请记录</el-menu-item>
        <el-menu-item index="/approvals">待审批任务</el-menu-item>
        <el-menu-item index="/permissions">有效权限与审计</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="topbar">
        <div>
          <strong>最小权限治理工作台</strong>
          <span class="environment-badge">仿真环境</span>
        </div>
        <DemoIdentitySwitcher />
      </el-header>
      <el-main class="content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>
