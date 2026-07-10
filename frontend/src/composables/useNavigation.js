import { computed } from 'vue'
import { usePermissions } from './usePermissions'

/** @deprecated Utiliser usePermissions */
export function useNavigation() {
  const { mainNav } = usePermissions()
  return { mainNav: computed(() => mainNav.value) }
}
