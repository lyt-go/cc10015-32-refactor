<template>
  <section class="page" data-module="insight_report">
    <header class="page-head">
      <div><h2>洞察报告</h2><p class="page-desc">维护洞察报告的输入、执行约束与结果记录，为洞察报告提供可验证的数据工程流程。</p></div>
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

    <section class="analysis-section" data-testid="insight-conclusions">
      <header class="page-head" style="margin-top:20px">
        <div>
          <h3 style="margin:0">洞察结论</h3>
          <p class="page-desc">关键发现读取留存矩阵的周期留存率（V031 历史列 / V032 新口径），不再单独维护口径。</p>
        </div>
        <div class="page-actions">
          <button class="btn" type="button" data-testid="verify-samples" @click="verifySamples">核对原报告样例</button>
        </div>
      </header>
      <p v-if="verifyResult" class="matrix-message" data-testid="verify-result">
        样例核对：{{ verifyResult.ok ? '通过' : '存在差异' }} · 报告 {{ verifyResult.checked }} 份
        <span v-for="item in verifyResult.mismatches || []" :key="item['报告编号'] + item['原因']" style="margin-left:8px;color:#b42318">
          {{ item['报告编号'] }}：{{ item['原因'] }}
        </span>
      </p>
      <table class="data-table" data-testid="conclusion-table">
        <thead><tr><th>报告编号</th><th>分析主题</th><th>群组编号</th><th>核对周期</th><th>历史口径留存率</th><th>新口径留存率</th><th>差异</th><th>结论</th></tr></thead>
        <tbody>
          <tr v-for="row in conclusions" :key="row.id" :data-testid="`conclusion-${row['报告编号']}`">
            <td>{{ row['报告编号'] }}</td>
            <td>{{ row['分析主题'] }}</td>
            <td>{{ row['群组编号'] }}</td>
            <td>第{{ row['核对周期'] }}期</td>
            <td>{{ formatRate(row['历史口径留存率']) }}</td>
            <td>{{ formatRate(row['新口径留存率']) }}</td>
            <td>{{ formatRate(row['差异']) }}</td>
            <td>{{ row['结论'] }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </section>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { request } from '@/api/client'
const ENDPOINT = '/api/insight_report'
const summaryMetrics = ref<{label:string;value:number;trend:number}[]>([])
const results = ref<any[]>([]); const chartData = ref<{label:string;value:number}[]>([])
const loading = ref(false)
const params = ref<Record<string,string>>({})
const paramFields = ["报告编号", "分析主题", "数据来源", "关键发现", "建议措施", "影响范围", "生成时间", "报告版本"].filter((f: string) => !['编号','名称','版本'].includes(f)).slice(0, 4)
const options: Record<string,string[]> = { '统计粒度': ['按日','按周','按月'], '分组字段': ['全量','按类型','按区域'], '比较方法': ['环比','同比','绝对值'], '时间范围': ['最近7天','最近30天','最近90天'] }
const resultColumns = computed(() => ["报告编号", "分析主题", "数据来源", "关键发现", "建议措施", "影响范围", "生成时间", "报告版本"].slice(0, 5))
const conclusions = ref<any[]>([])
const verifyResult = ref<any>(null)

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
async function reloadConclusions() {
  try { const res = await request(`${ENDPOINT}/conclusions`); conclusions.value = (await res.json()).items || [] } catch (e) { conclusions.value = [] }
}
async function verifySamples() {
  try { const res = await request(`${ENDPOINT}/verify`); verifyResult.value = await res.json() } catch (e) { verifyResult.value = { ok: false, checked: 0, mismatches: [] } }
}
onMounted(() => { fetchSummary(); reloadConclusions() })
</script>
