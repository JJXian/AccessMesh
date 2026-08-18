import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import type { DemoUser } from '../types'

const STORAGE_KEY = 'accessmesh.demoSubjectId'

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
    window.dispatchEvent(new CustomEvent('accessmesh:identity-changed'))
  }

  return { users, subjectId, currentUser, setUsers, selectSubject }
})
