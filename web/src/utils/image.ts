const TARGET_1080P = 1080

/** 标注框数据 */
export interface DetectionBox {
  /** 绝对像素坐标 [x1, y1, x2, y2]，相对象限 */
  bbox: [number, number, number, number]
  class_name: string
  confidence: number
}

const BOX_FILL: Record<string, string> = {
  red: 'rgba(239,68,68,0.25)',
  green: 'rgba(34,197,94,0.25)',
  yellow: 'rgba(234,179,8,0.25)',
}

const BOX_STROKE: Record<string, string> = {
  red: '#EF4444',
  green: '#22C55E',
  yellow: '#EAB308',
}

const BOX_LABEL_BG: Record<string, string> = {
  red: '#EF4444',
  green: '#22C55E',
  yellow: '#EAB308',
}

function getBoxColor(key: string) {
  return {
    fill: BOX_FILL[key] ?? 'rgba(59,130,246,0.25)',
    stroke: BOX_STROKE[key] ?? '#3B82F6',
    labelBg: BOX_LABEL_BG[key] ?? '#3B82F6',
  }
}

/** 在 canvas 上绘制标注框 */
function drawBoxes(
  ctx: CanvasRenderingContext2D,
  canvasW: number,
  canvasH: number,
  boxes: DetectionBox[],
  srcW: number,
  srcH: number,
) {
  const scaleX = canvasW / srcW
  const scaleY = canvasH / srcH

  const padding = Math.max(4, Math.ceil(canvasW / 200))

  for (const box of boxes) {
    const [x1, y1, x2, y2] = box.bbox
    const left = x1 * scaleX - padding
    const top = y1 * scaleY - padding
    const w = (x2 - x1) * scaleX + padding * 2
    const h = (y2 - y1) * scaleY + padding * 2
    const { fill, stroke, labelBg } = getBoxColor(box.class_name)

    // 填充
    ctx.fillStyle = fill
    ctx.fillRect(left, top, w, h)

    // 边框
    ctx.strokeStyle = stroke
    ctx.lineWidth = Math.max(1, Math.ceil(canvasW / 600))
    ctx.strokeRect(left, top, w, h)

    // 标签（放在框下方，避免遮挡检测目标）
    const text = `${box.class_name} ${(box.confidence * 100).toFixed(0)}%`
    const fontSize = Math.max(14, Math.ceil(canvasW / 120))
    ctx.font = `bold ${fontSize}px sans-serif`
    const metrics = ctx.measureText(text)
    const labelH = Math.ceil(fontSize * 1.4)
    const labelW = metrics.width + labelH / 2
    const labelX = left
    const labelY = top + h + 2

    ctx.fillStyle = labelBg
    ctx.beginPath()
    ctx.roundRect(labelX, labelY, labelW, labelH, 3)
    ctx.fill()

    ctx.fillStyle = '#fff'
    ctx.fillText(text, labelX + labelH / 4, labelY + fontSize * 1.1)
  }
}

/**
 * 将图片的指定区域裁剪 → 在原图画框 → 压缩到长边不超过 1080px。
 * 对齐后端：先画框再压缩，保证框线/文字在原分辨率下渲染清晰。
 */
export function cropAndCompressTo1080p(
  img: HTMLImageElement,
  sx: number,
  sy: number,
  sw: number,
  sh: number,
  quality = 0.9,
  boxes?: DetectionBox[],
): string {
  // Step 1: 原分辨率裁剪 + 画框
  const fullCanvas = document.createElement('canvas')
  fullCanvas.width = sw
  fullCanvas.height = sh
  const fullCtx = fullCanvas.getContext('2d')!
  fullCtx.drawImage(img, sx, sy, sw, sh, 0, 0, sw, sh)

  if (boxes && boxes.length > 0) {
    drawBoxes(fullCtx, sw, sh, boxes, sw, sh)
  }

  // Step 2: 压缩到 1080p
  let dstW = sw
  let dstH = sh
  const maxEdge = Math.max(sw, sh)
  if (maxEdge > TARGET_1080P) {
    const scale = TARGET_1080P / maxEdge
    dstW = Math.round(sw * scale)
    dstH = Math.round(sh * scale)
  }

  const outCanvas = document.createElement('canvas')
  outCanvas.width = dstW
  outCanvas.height = dstH
  const outCtx = outCanvas.getContext('2d')!
  outCtx.drawImage(fullCanvas, 0, 0, sw, sh, 0, 0, dstW, dstH)

  return outCanvas.toDataURL('image/jpeg', quality)
}

/**
 * 将整张图等分为 4 个象限，每象限裁剪 + 压缩 + 绘制标注框。
 * detections 按 quadrant 字段分组后画到对应象限上。
 */
export function splitAndCompressQuadrants(
  img: HTMLImageElement,
  boxesByQuadrant: Record<string, DetectionBox[]>,
  quality = 0.9,
): Record<string, string> {
  const w = img.naturalWidth
  const h = img.naturalHeight
  const hw = Math.floor(w / 2)
  const hh = Math.floor(h / 2)

  const quadrants: Record<string, [number, number, number, number]> = {
    top_left: [0, 0, hw, hh],
    top_right: [hw, 0, w - hw, hh],
    bottom_left: [0, hh, hw, h - hh],
    bottom_right: [hw, hh, w - hw, h - hh],
  }

  const result: Record<string, string> = {}
  for (const [key, [sx, sy, sw, sh]] of Object.entries(quadrants)) {
    result[key] = cropAndCompressTo1080p(img, sx, sy, sw, sh, quality, boxesByQuadrant[key])
  }
  return result
}
