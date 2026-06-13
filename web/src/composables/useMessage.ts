import { useMessage as useNMessage } from 'naive-ui'

export function useMessage() {
  const message = useNMessage()

  function showSuccess(content: string) {
    message.success(content)
  }

  function showError(content: string) {
    message.error(content)
  }

  function showWarning(content: string) {
    message.warning(content)
  }

  return { showSuccess, showError, showWarning }
}
