<template>
  <section class="page" data-module="cohort_track">
    <header class="page-head">
      <div><h2>同期群追踪</h2><p class="page-desc">维护同期群定义的输入、执行约束与结果记录，为同期群追踪提供可验证的数据工程流程。</p></div>
    </header>
    <div class="analysis-summary">
      <article v-for="m in summaryMetrics" :key="m.label" class="analysis-card" data-testid="kpi-card">
        <span style="font-size:12px;color:var(--muted)">{{ m.label }}</span>
        <strong style="font-size:22px;display:block">{{ m.value }}</strong>
        <span :class="m.trend > 0 ? 'trend-up' : 'trend-down'" style="font-size:12px">{{ m.trend > 0 ? '↑' : '↓' }}{{ Math.abs(m.trend) }}%</span>
      </article>
    </div>
    <form class="analysis-form" @submit.prevent="runAnalysis">
      <label v-for="field in paramFields" :key="field"><span>{{ field }}</span>
        <select v-if="field.includes('方法')||field.includes('策略')||field.includes('粒度')" v-model="params[field]"><option v-for="o in options[field]" :key="o" :value="o">{{ o }}</option></select>
        <input v-else v-model="params[field]" :placeholder="`请输入${field}`" />
      </label>
      <button class="btn primary" type="submit" data-testid="run-analysis">运行分析</button>
    </form>
    <div v-if="chartData.length" class="analysis-chart">
      <div v-for="(bar, i) in chartData" :key="i" class="analysis-bar" :style="{ height: barHeight(bar.value) + 'px' }"><span>{{ bar.label }}</span></div>
    </div>
    <table class="data-table" v-if="results.length">
      <thead><tr><th v-for="c in resultColumns" :key="c">{{ c }}</th></tr></thead>
      <tbody><tr v-for="row in results" :key="row.id"><td v-for="c in resultColumns" :key="c">{{ row[c] ?? '—' }}</td></tr></tbody>
    </table>
    <p v-if="!results.length && !loading" style="text-align:center;color:var(--muted)">请配置参数后运行分析</p>

    <section class="analysis-section" data-testid="retention-matrix">
      <header class="page-head" style="margin-top:20px">
        <div>
          <h3 style="margin:0">留存矩阵</h3>
          <p class="page-desc">周期窗口与指标口径来自同一份同期群定义；V031 为历史列，V032 为新口径独立版本。</p>
        </div>
        <div class="page-actions">
          <label class="inline-field"><span>口径版本</span>
            <select v-model="matrixVersion" data-testid="matrix-version" @change="reloadMatrix">
              <option value="V031">V031 历史口径</option>
              <option value="V032">V032 新口径</option>
            </select>
          </label>
          <label class="inline-field"><span>替换策略</span>
            <select v-model="policy" data-testid="matrix-policy">
              <option value="historical_first">历史口径优先（保留旧列 + 差异附注）</option>
              <option value="recompute">按新口径整列重算（保留历史快照）</option>
            </select>
          </label>
          <button class="btn" type="button" data-testid="matrix-replace" @click="replaceMatrix">执行矩阵替换</button>
          <button class="btn" type="button" data-testid="matrix-history-check" @click="runHistoryCheck">历史核对</button>
        </div>
      </header>
      <p v-if="matrixMessage" class="matrix-message" data-testid="matrix-message">{{ matrixMessage }}</p>
      <table class="data-table" data-testid="matrix-table">
        <thead><tr><th>群组编号</th><th>群组名称</th><th>时间基准</th><th>追踪周期</th><th>留存窗口</th><th v-for="c in matrixColumns" :key="c">{{ c }}</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="row in matrixRows" :key="row.id" :data-testid="`matrix-row-${row['群组编号']}`">
            <td>{{ row['群组编号'] }}</td>
            <td>{{ row['群组名称'] }}</td>
            <td>{{ row['时间基准'] }}</td>
            <td>{{ row['追踪周期'] }}</td>
            <td>{{ row['留存窗口'] }}</td>
            <td v-for="c in matrixColumns" :key="c">{{ formatRate(row[c]) }}</td>
            <td><button class="link" type="button" @click="openDetail(row)">查看详情</button></td>
          </tr>
        </tbody>
      </table>
      <div v-if="historyCheck" class="matrix-message" data-testid="history-check-result">
        历史核对：{{ historyCheck.ok ? '通过' : '存在差异' }} · 群组 {{ historyCheck['核对群组数'] }} · 指纹 {{ historyCheck['矩阵指纹'] }}
        <span v-if="historyCheck['未清残留'] && Object.keys(historyCheck['未清残留']).length"> · 未清残留 {{ JSON.stringify(historyCheck['未清残留']) }}</span>
      </div>
      <div v-if="detail" class="matrix-detail" data-testid="cohort-detail">
        <h4 style="margin:0 0 8px">详情：{{ detail['群组编号'] }}</h4>
        <p style="margin:0 0 8px;font-size:13px;color:var(--muted)">
          成员边界 {{ detail['成员基数'] }} / {{ detail['边界版本'] }} ·
          周期口径 {{ detail['周期口径'] }} · 留存窗口 {{ detail['留存窗口'] }} {{ detail['追踪周期'] }}
        </p>
        <table class="data-table">
          <thead><tr><th>周期</th><th>{{ detail['周期口径'] }} 留存率</th><th v-if="detail['新口径留存率']">V032 新口径留存率</th></tr></thead>
          <tbody>
            <tr v-for="label in detailPeriods" :key="label">
              <td>{{ label }}</td>
              <td>{{ formatRate(detail['留存率'] && detail['留存率'][label]) }}</td>
              <td v-if="detail['新口径留存率']">{{ formatRate(detail['新口径留存率'][label]) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="archive.length" class="matrix-message" data-testid="v032-archive">
        V032 留档：<span v-for="item in archive" :key="item.id" style="margin-right:12px">{{ item['操作'] }} · {{ item['结果'] }} · {{ item['原因'] }}</span>
      </div>
    </section>
  </section>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { request } from '@/api/client'
const ENDPOINT = '/api/cohort_track'
const MATRIX_ENDPOINT = '/api/retention_matrix'
const summaryMetrics = ref<{label:string;value:number;trend:number}[]>([])
const results = ref<any[]>([]); const chartData = ref<{label:string;value:number}[]>([])
const loading = ref(false)
const params = ref<Record<string,string>>({})
const paramFields = ["群组编号", "群组名称", "首次行为", "时间基准", "追踪周期", "留存窗口", "分析指标", "对比群组"].filter((f: string) => !['编号','名称','版本'].includes(f)).slice(0, 4)
const options: Record<string,string[]> = { '统计粒度': ['按日','按周','按月'], '分组字段': ['全量','按类型','按区域'], '比较方法': ['环比','同比','绝对值'], '时间范围': ['最近7天','最近30天','最近90天'] }
const resultColumns = computed(() => ["群组编号", "群组名称", "首次行为", "时间基准", "追踪周期", "留存窗口", "分析指标", "对比群组"].slice(0, 5))

const matrixVersion = ref('V031')
const policy = ref('historical_first')
const matrixRows = ref<any[]>([])
const matrixColumns = ref<string[]>([])
const matrixMessage = ref('')
const historyCheck = ref<any>(null)
const archive = ref<any[]>([])
const detail = ref<any>(null)
const detailPeriods = computed<string[]>(() => Object.keys(detail.value?.['留存率'] || {}))

function formatRate(value: unknown) {
  return typeof value === 'number' ? `${(value * 100).toFixed(2)}%` : '—'
}
function barHeight(v: number) { const max = Math.max(...chartData.value.map(d => d.value), 1); return Math.max(10, (v / max) * 140) }
async function fetchSummary() { try { const res = await request(`${ENDPOINT}/summary`); summaryMetrics.value = (await res.json()).metrics || [] } catch(e) {} }
async function runAnalysis() {
  loading.value = true
  try { const res = await request(`${ENDPOINT}/run`, { method: 'POST', body: JSON.stringify({ values: params.value }) }); const data = await res.json(); results.value = data.items || []; chartData.value = (data.items || []).map((r: any) => ({ label: Object.values(r)[0] as string, value: Object.values(r).filter(v => typeof v === 'number')[0] as number || 0 })).slice(0, 6) } catch(e) { results.value = [] }
  loading.value = false
}
async function reloadMatrix() {
  detail.value = null
  try {
    const res = await request(`${MATRIX_ENDPOINT}?version=${matrixVersion.value}`)
    const data = await res.json()
    matrixRows.value = data.items || []
    matrixColumns.value = data.columns || []
  } catch (e) { matrixRows.value = []; matrixColumns.value = [] }
}
async function openDetail(row: any) {
  try {
    const res = await request(`${ENDPOINT}/${row.id}`)
    detail.value = await res.json()
  } catch (e) { detail.value = null }
}
async function replaceMatrix() {
  try {
    const res = await request(`${MATRIX_ENDPOINT}/replace`, {
      method: 'POST',
      body: JSON.stringify({ values: { 策略: policy.value, 接收方: 'V032' } }),
    })
    const data = await res.json()
    matrixMessage.value = data.ok
      ? `矩阵替换完成（${data['策略']}），结果写入 V032 独立版本`
      : `矩阵替换已回滚：${data['原因']}`
    await Promise.all([reloadMatrix(), reloadArchive()])
  } catch (e: any) { matrixMessage.value = e.message }
}
async function runHistoryCheck() {
  try {
    const res = await request(`${MATRIX_ENDPOINT}/history-check`)
    historyCheck.value = await res.json()
  } catch (e) { historyCheck.value = { ok: false } }
}
async function reloadArchive() {
  try { const res = await request(`${MATRIX_ENDPOINT}/archive`); archive.value = (await res.json()).items || [] } catch (e) { archive.value = [] }
}
onMounted(() => { fetchSummary(); reloadMatrix(); reloadArchive() })
</script>
