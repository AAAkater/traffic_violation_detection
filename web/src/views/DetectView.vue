<script setup lang="ts">
import DetectionList from '@/components/detect/DetectionList.vue'
import ImageUploader from '@/components/detect/ImageUploader.vue'
import JudgePanel from '@/components/detect/JudgePanel.vue'
import { useDetectStore } from '@/stores/detect'
import type { DetectData, JudgeData } from '@/types/api'
import { NCard, NSteps, NStep, NButton, NSpace } from 'naive-ui'
import { storeToRefs } from 'pinia'
import { shallowRef } from 'vue'

const detectStore = useDetectStore()
const { currentResult, isUploading } = storeToRefs(detectStore)

const currentStep = shallowRef(1)
const judgeResult = shallowRef<JudgeData | null>(null)

async function handleUpload(file: File) {
  await detectStore.upload(file)
  currentStep.value = 2
}

function handleJudged(result: JudgeData) {
  judgeResult.value = result
  currentStep.value = 3
}

function handleReset() {
  detectStore.reset()
  judgeResult.value = null
  currentStep.value = 1
}
</script>

<template>
  <div class="mx-auto max-w-4xl space-y-6">
    <h1 class="text-3xl font-bold text-gray-800 dark:text-white">交通违规检测</h1>

    <NCard>
      <NSteps :current="currentStep" class="mb-8">
        <NStep title="上传图片" description="上传交通现场图片" />
        <NStep title="YOLO 检测" description="AI 自动识别交通信号灯" />
        <NStep title="LLM 判定" description="AI 大模型判定是否违规" />
      </NSteps>

      <!-- Step 1: Upload -->
      <div v-if="currentStep === 1">
        <ImageUploader :disabled="isUploading" @upload="handleUpload" />
      </div>

      <!-- Step 2: Detection Results -->
      <div v-else-if="currentStep === 2 && currentResult">
        <DetectionList :detections="currentResult.detections" />
        <div class="mt-6">
          <JudgePanel :image-id="currentResult.image_id" @judged="handleJudged" />
        </div>
      </div>

      <!-- Step 3: Judge Result -->
      <div v-else-if="currentStep === 3 && judgeResult">
        <NCard
          :title="judgeResult.violated ? '违规判定' : '判定结果'"
          :class="judgeResult.violated ? 'border-red-300' : 'border-green-300'"
        >
          <div class="space-y-4">
            <div
              :class="[
                'rounded-lg p-6 text-center text-2xl font-bold',
                judgeResult.violated ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600',
              ]"
            >
              {{ judgeResult.violated ? '⚠️ 检测到违规行为' : '✅ 未检测到违规' }}
            </div>
            <div v-if="judgeResult.reason" class="rounded bg-gray-50 p-4 dark:bg-gray-800">
              <div class="mb-1 text-sm text-gray-500">判定理由</div>
              <div class="text-gray-800 dark:text-gray-200">{{ judgeResult.reason }}</div>
            </div>
          </div>
        </NCard>
      </div>

      <!-- Actions -->
      <div v-if="currentStep > 1" class="mt-6 flex gap-3">
        <NButton @click="handleReset">重新检测</NButton>
      </div>
    </NCard>
  </div>
</template>
