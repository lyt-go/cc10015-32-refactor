import { expect, test } from '@playwright/test'
import { readFile } from 'node:fs/promises'

type ModuleCase = {
  key: string
  fields: string[]
  actions: string[]
  actionTargets: string[]
  shape: string
}

const modules: ModuleCase[] = [
  {
    "key": "experiment",
    "fields": [
      "方案编号",
      "实验名称",
      "对照组说明",
      "实验组说明",
      "样本总量",
      "分流比例",
      "启动日期",
      "预期时长"
    ],
    "actions": [
      "提交审批",
      "启动实验",
      "终止实验"
    ],
    "actionTargets": [
      "待审批",
      "运行中",
      "已结束"
    ],
    "shape": "job-timeline"
  },
  {
    "key": "sample_group",
    "fields": [
      "分群编号",
      "分群名称",
      "筛选条件",
      "样本基数",
      "分群日期",
      "更新方式",
      "有效天数",
      "负责人"
    ],
    "actions": [
      "开始计算",
      "确认就绪",
      "标记过期"
    ],
    "actionTargets": [
      "计算中",
      "已就绪",
      "已过期"
    ],
    "shape": "crud-table"
  },
  {
    "key": "metric_def",
    "fields": [
      "指标编号",
      "指标名称",
      "计算公式",
      "统计粒度",
      "时间窗口",
      "基准取值",
      "精度位数",
      "口径版本"
    ],
    "actions": [
      "提交校验",
      "标记生效",
      "标记废弃"
    ],
    "actionTargets": [
      "待校验",
      "已生效",
      "已废弃"
    ],
    "shape": "crud-table"
  },
  {
    "key": "ab_result",
    "fields": [
      "报告编号",
      "实验编号",
      "分析指标",
      "对照组均值",
      "实验组均值",
      "置信水平",
      "效果方向",
      "生成时间"
    ],
    "actions": [
      "开始计算",
      "确认完成",
      "归档报告"
    ],
    "actionTargets": [
      "计算中",
      "已完成",
      "已归档"
    ],
    "shape": "analysis-dashboard"
  },
  {
    "key": "segment_compare",
    "fields": [
      "任务编号",
      "分群A",
      "分群B",
      "对比指标",
      "时间范围",
      "差异阈值",
      "显著性水平",
      "比较方法"
    ],
    "actions": [
      "开始计算",
      "确认完成",
      "废弃任务"
    ],
    "actionTargets": [
      "计算中",
      "已完成",
      "已废弃"
    ],
    "shape": "analysis-dashboard"
  },
  {
    "key": "drill_down",
    "fields": [
      "维度编号",
      "维度名称",
      "下钻层级",
      "基准指标",
      "父级维度",
      "子级维度",
      "数据来源",
      "刷新间隔"
    ],
    "actions": [
      "提交校验",
      "标记生效",
      "停用维度"
    ],
    "actionTargets": [
      "待校验",
      "已生效",
      "已停用"
    ],
    "shape": "analysis-dashboard"
  },
  {
    "key": "data_filter",
    "fields": [
      "规则编号",
      "数据来源",
      "筛选字段",
      "筛选算子",
      "筛选阈值",
      "逻辑组合",
      "输出集合",
      "规则版本"
    ],
    "actions": [
      "提交校验",
      "标记生效",
      "停用规则"
    ],
    "actionTargets": [
      "待校验",
      "已生效",
      "已停用"
    ],
    "shape": "crud-table"
  },
  {
    "key": "attr_analysis",
    "fields": [
      "任务编号",
      "目标指标",
      "候选因子",
      "归因模型",
      "分析窗口",
      "贡献度阈值",
      "交互项数",
      "任务批次"
    ],
    "actions": [
      "开始计算",
      "确认完成",
      "取消任务"
    ],
    "actionTargets": [
      "计算中",
      "已完成",
      "已取消"
    ],
    "shape": "analysis-dashboard"
  },
  {
    "key": "anomaly_detect",
    "fields": [
      "规则编号",
      "监控指标",
      "检测算法",
      "基线窗口",
      "波动阈值",
      "告警级别",
      "静默时段",
      "规则版本"
    ],
    "actions": [
      "提交校验",
      "标记生效",
      "停用规则"
    ],
    "actionTargets": [
      "待校验",
      "已生效",
      "已停用"
    ],
    "shape": "crud-table"
  },
  {
    "key": "forecast_model",
    "fields": [
      "模型编号",
      "预测对象",
      "历史窗口",
      "预测周期",
      "模型类型",
      "参数配置",
      "训练批次",
      "评估误差"
    ],
    "actions": [
      "开始训练",
      "确认就绪",
      "废弃模型"
    ],
    "actionTargets": [
      "训练中",
      "已就绪",
      "已废弃"
    ],
    "shape": "analysis-dashboard"
  },
  {
    "key": "data_export",
    "fields": [
      "任务编号",
      "数据来源",
      "导出格式",
      "字段清单",
      "数据范围",
      "压缩方式",
      "分片大小",
      "导出批次"
    ],
    "actions": [
      "开始导出",
      "确认完成",
      "取消导出"
    ],
    "actionTargets": [
      "导出中",
      "已完成",
      "已取消"
    ],
    "shape": "job-timeline"
  },
  {
    "key": "cohort_track",
    "fields": [
      "群组编号",
      "群组名称",
      "首次行为",
      "时间基准",
      "追踪周期",
      "留存窗口",
      "分析指标",
      "对比群组"
    ],
    "actions": [
      "提交校验",
      "标记生效",
      "停用群组"
    ],
    "actionTargets": [
      "待校验",
      "已生效",
      "已停用"
    ],
    "shape": "analysis-dashboard"
  },
  {
    "key": "chart_config",
    "fields": [
      "图表编号",
      "图表类型",
      "数据来源",
      "横轴字段",
      "纵轴字段",
      "分组字段",
      "刷新间隔",
      "分享链接"
    ],
    "actions": [
      "提交校验",
      "确认发布",
      "停用图表"
    ],
    "actionTargets": [
      "待校验",
      "已发布",
      "已停用"
    ],
    "shape": "analysis-dashboard"
  },
  {
    "key": "insight_report",
    "fields": [
      "报告编号",
      "分析主题",
      "数据来源",
      "关键发现",
      "建议措施",
      "影响范围",
      "生成时间",
      "报告版本"
    ],
    "actions": [
      "开始生成",
      "确认完成",
      "归档报告"
    ],
    "actionTargets": [
      "生成中",
      "已完成",
      "已归档"
    ],
    "shape": "analysis-dashboard"
  },
  {
    "key": "data_freshness",
    "fields": [
      "监控编号",
      "数据表名",
      "最新分区",
      "期望刷新",
      "滞后时长",
      "告警阈值",
      "检查间隔",
      "通知方式"
    ],
    "actions": [
      "提交校验",
      "标记生效",
      "停用监控"
    ],
    "actionTargets": [
      "待校验",
      "已生效",
      "已停用"
    ],
    "shape": "crud-table"
  },
  {
    "key": "metric_alias",
    "fields": [
      "版本编号",
      "指标编号",
      "变更说明",
      "旧口径",
      "新口径",
      "生效时间",
      "审批状态",
      "变更人"
    ],
    "actions": [
      "提交审批",
      "确认生效",
      "执行回滚"
    ],
    "actionTargets": [
      "待审批",
      "已生效",
      "已回滚"
    ],
    "shape": "crud-table"
  },
  {
    "key": "expr_factor",
    "fields": [
      "因子编号",
      "因子名称",
      "因子层级",
      "取值集合",
      "分配比例",
      "互斥规则",
      "关联实验",
      "生效批次"
    ],
    "actions": [
      "提交校验",
      "标记生效",
      "停用因子"
    ],
    "actionTargets": [
      "待校验",
      "已生效",
      "已停用"
    ],
    "shape": "crud-table"
  },
  {
    "key": "evaluate_board",
    "fields": [
      "看板编号",
      "看板名称",
      "关联实验",
      "展示指标",
      "数据范围",
      "刷新策略",
      "消费范围",
      "看板版本"
    ],
    "actions": [
      "提交校验",
      "确认发布",
      "停用看板"
    ],
    "actionTargets": [
      "待校验",
      "已发布",
      "已停用"
    ],
    "shape": "analysis-dashboard"
  }
]
const repoKind = 'fullstack'
const crudModules = modules.filter(m => m.shape === 'crud-table')
const dagModules = modules.filter(m => m.shape === 'dag-graph')
const timelineModules = modules.filter(m => m.shape === 'job-timeline')
const analysisModules = modules.filter(m => m.shape === 'analysis-dashboard')

function parseCsv(text: string): string[][] {
  const records: string[][] = []
  let row: string[] = []
  let cell = ''
  let quoted = false
  const input = text.replace(/^\uFEFF/, '')
  for (let index = 0; index < input.length; index++) {
    const char = input[index]
    if (quoted) {
      if (char === '"' && input[index + 1] === '"') { cell += '"'; index++ }
      else if (char === '"') { quoted = false }
      else { cell += char }
    } else if (char === '"' && cell === '') { quoted = true }
    else if (char === ',') { row.push(cell); cell = '' }
    else if (char === '\n') {
      row.push(cell.replace(/\r$/, ''))
      if (row.some(v => v !== '')) records.push(row)
      row = []; cell = ''
    } else { cell += char }
  }
  row.push(cell.replace(/\r$/, ''))
  if (row.some(v => v !== '')) records.push(row)
  return records
}

test('CRUD模块：筛选、导出、登记、动作、指标全链路', async ({ page }) => {
  test.setTimeout(300_000)
  const browserErrors: string[] = []
  page.on('pageerror', e => browserErrors.push(e.message))
  page.on('response', r => { if (r.url().includes('/api/') && r.status()>=400) browserErrors.push(`${r.status()} ${r.url()}`) })
  if (crudModules.length === 0) { test.skip(); return }

  for (const mod of crudModules) {
    await page.goto(`/${mod.key}`)
    await page.waitForTimeout(3000)
    const bodyRows = page.locator('tbody tr[data-testid^="row-"]')
    await expect(bodyRows).toHaveCount(3)
    const firstValue = await bodyRows.nth(0).locator('td').nth(0).innerText()

    await page.getByTestId(`filter-${mod.fields[0]}`).fill(firstValue)
    await page.getByTestId('query').click()
    await expect(bodyRows).toHaveCount(1)
    await page.getByTestId('reset').click()
    await expect(bodyRows).toHaveCount(3)

    const downloadPromise = page.waitForEvent('download')
    await page.getByTestId('export').click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe(`${mod.key}.csv`)

    const createdValues = mod.fields.map((f, i) => `验收-${mod.key}-${i+1}`)
    await page.getByTestId('open-create').click()
    await expect(page.getByTestId('create-modal')).toBeVisible()
    for (const [i, field] of mod.fields.entries()) {
      await page.getByTestId(`create-${field}`).fill(createdValues[i])
    }
    await page.getByTestId('submit-create').click()
    await expect(page.getByTestId('create-modal')).toHaveCount(0)
    await expect(bodyRows).toHaveCount(4)

    const createdRow = page.locator('tbody tr').filter({ hasText: createdValues[0] })
    for (const [i, action] of mod.actions.entries()) {
      await createdRow.getByRole('button', { name: action, exact: true }).click()
      await expect(createdRow).toHaveAttribute('data-status', mod.actionTargets[i])
    }
  }

  expect(browserErrors).toEqual([])
})

test('DAG拓扑模块：节点渲染、详情、动作、导出', async ({ page }) => {
  test.setTimeout(300_000)
  const browserErrors: string[] = []
  page.on('pageerror', e => browserErrors.push(e.message))
  page.on('response', r => { if (r.url().includes('/api/') && r.status()>=400) browserErrors.push(`${r.status()} ${r.url()}`) })
  if (dagModules.length === 0) { test.skip(); return }

  for (const mod of dagModules) {
    await page.goto(`/${mod.key}`)
    await page.waitForTimeout(3000)
    await expect(page.locator('svg.dag-svg')).toBeVisible()
    const nodes = page.locator('g.dag-node')
    const count = await nodes.count()
    expect(count).toBeGreaterThanOrEqual(3)

    await nodes.first().click()
    await expect(page.getByTestId('dag-detail')).toBeVisible()

    const downloadPromise = page.waitForEvent('download')
    await page.getByTestId('export').click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe(`${mod.key}.csv`)

    await page.getByTestId('open-create').click()
    await expect(page.getByTestId('create-modal')).toBeVisible()
    for (const [i, field] of mod.fields.slice(0,3).entries()) {
      await page.locator('.create-field input').nth(i).fill(`E2E-${mod.key}-${i}`)
    }
    await page.getByTestId('submit-create').click()
    await expect(page.getByTestId('create-modal')).toHaveCount(0)
  }

  expect(browserErrors).toEqual([])
})

test('时间线模块：甘特条渲染、日期筛选、日志查看、登记', async ({ page }) => {
  test.setTimeout(300_000)
  const browserErrors: string[] = []
  page.on('pageerror', e => browserErrors.push(e.message))
  page.on('response', r => { if (r.url().includes('/api/') && r.status()>=400) browserErrors.push(`${r.status()} ${r.url()}`) })
  if (timelineModules.length === 0) { test.skip(); return }

  for (const mod of timelineModules) {
    await page.goto(`/${mod.key}`)
    await expect(page.locator('.timeline-bar').first()).toBeVisible({ timeout: 10000 })
    const bars = page.locator('.timeline-bar')
    const count = await bars.count()
    expect(count).toBeGreaterThanOrEqual(3)

    await bars.first().click()
    await expect(page.getByTestId('timeline-log')).toBeVisible()

    const downloadPromise = page.waitForEvent('download')
    await page.getByTestId('export').click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe(`${mod.key}.csv`)

    await page.getByTestId('open-create').click()
    await expect(page.getByTestId('create-modal')).toBeVisible()
    for (const [i, field] of mod.fields.slice(0,3).entries()) {
      await page.locator('.create-field input').nth(i).fill(`E2E-${mod.key}-${i}`)
    }
    await page.getByTestId('submit-create').click()
    await expect(page.getByTestId('create-modal')).toHaveCount(0)
  }

  expect(browserErrors).toEqual([])
})

test('分析看板模块：KPI卡片、运行分析、图表渲染', async ({ page }) => {
  test.setTimeout(300_000)
  const browserErrors: string[] = []
  page.on('pageerror', e => browserErrors.push(e.message))
  page.on('response', r => { if (r.url().includes('/api/') && r.status()>=400) browserErrors.push(`${r.status()} ${r.url()}`) })
  if (analysisModules.length === 0) { test.skip(); return }

  for (const mod of analysisModules) {
    await page.goto(`/${mod.key}`)
    await expect(page.getByTestId('kpi-card').first()).toBeVisible({ timeout: 10000 })
    const kpiCards = page.getByTestId('kpi-card')
    const kpiCount = await kpiCards.count()
    expect(kpiCount).toBeGreaterThanOrEqual(2)
    await expect(kpiCards.first().locator('strong')).toBeVisible()

    await page.getByTestId('run-analysis').click()
    await expect(page.locator('.analysis-bar').first()).toBeVisible({ timeout: 5000 })
    await expect(page.locator('.data-table tbody tr').first()).toBeVisible({ timeout: 5000 })
  }

  expect(browserErrors).toEqual([])
})

test('概览汇总', async ({ page }) => {
  test.setTimeout(300_000)
  await page.goto('/')
  await expect(page.locator('.stat-value').nth(1)).toBeVisible()
  // 验证概览页加载正常即可，不硬编码精确计数（取决于各模块 E2E 登记成功数）
})

test('留存矩阵与洞察结论：同源数据、V032 留档与历史核对', async ({ page }) => {
  test.setTimeout(300_000)
  const browserErrors: string[] = []
  page.on('pageerror', e => browserErrors.push(e.message))
  page.on('response', r => { if (r.url().includes('/api/') && r.status() >= 400) browserErrors.push(`${r.status()} ${r.url()}`) })

  await page.goto('/cohort_track')
  await expect(page.getByTestId('matrix-table')).toBeVisible()
  await expect(page.getByTestId('matrix-row-COHO-0001')).toBeVisible()
  const firstRowHistory = await page.getByTestId('matrix-row-COHO-0001').locator('td').nth(5).innerText()

  await page.getByTestId('matrix-history-check').click()
  await expect(page.getByTestId('history-check-result')).toContainText('历史核对：通过')

  // 查看详情后返回工作台，历史周期列必须保持一致。
  await page.getByTestId('matrix-row-COHO-0001').getByRole('button', { name: '查看详情' }).click()
  await expect(page.getByTestId('cohort-detail')).toBeVisible()
  const detailHistory = await page.getByTestId('cohort-detail').locator('tbody tr').nth(0).locator('td').nth(1).innerText()
  expect(detailHistory).toBe(firstRowHistory)

  await page.getByTestId('matrix-version').selectOption('V032')
  await expect(page.getByTestId('matrix-row-COHO-0001')).toBeVisible()

  // 未清残留存在时，替换应被阻断并回滚。
  await page.getByTestId('matrix-policy').selectOption('recompute')
  await page.getByTestId('matrix-replace').click()
  await expect(page.getByTestId('matrix-message')).toContainText('回滚')
  await expect(page.getByTestId('v032-archive')).toContainText('rolled_back')

  // 切到洞察报告：结论表读取同一份矩阵留存率。
  await page.goto('/insight_report')
  await expect(page.getByTestId('conclusion-table')).toBeVisible()
  await expect(page.getByTestId('conclusion-INSI-0001')).toContainText('%')
  await page.getByTestId('verify-samples').click()
  await expect(page.getByTestId('verify-result')).toContainText('样例核对：通过')

  expect(browserErrors).toEqual([])
})
