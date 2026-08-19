import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import type { DemoUser } from '../types'

const STORAGE_KEY = 'accessmesh.demoSubjectId'

/** 管理演示身份，并在页面刷新后恢复上次选择。 */
export const useIdentityStore = defineStore('identity', () => {
  const users = ref<DemoUser[]>([])
  const subjectId = ref(localStorage.getItem(STORAGE_KEY) ?? 'user-requester')
  const currentUser = computed(() => users.value.find((user) => user.external_id === subjectId.value))

  function setUsers(value: DemoUser[]) {
    users.value = value
  }

  function selectSubject(value: string) {
    subjectId.value = value
    localStorage.setItem(STORAGE_KEY, value)
    // 通知已挂载的业务页面重新按新身份加载数据。
    window.dispatchEvent(new CustomEvent('accessmesh:identity-changed'))
  }

  return { users, subjectId, currentUser, setUsers, selectSubject }
})
