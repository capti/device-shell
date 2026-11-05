/** Диаграммы дашборда; независимый запрос не блокирует основную сводку. */

import { BarChart, DonutChart } from '@mantine/charts'
import { Alert, Center, Grid, Loader, Paper, Text, Title } from '@mantine/core'
import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'

import { ApiError } from '../api/client'
import { fetchDashboardCharts, type Counters } from '../api/reports'

export default function DashboardCharts({ counters }: { counters: Counters }) {
  const charts = useQuery({
    queryKey: ['dashboard-charts'],
    queryFn: fetchDashboardCharts,
  })

  return (
    <>
      {charts.isError && (
        <Alert color="red" title="Не удалось загрузить часть графиков">
          {charts.error instanceof ApiError
            ? charts.error.message
            : 'Ошибка сети. Повторите попытку'}
        </Alert>
      )}
      <Grid>
        <Grid.Col span={{ base: 12, md: 6 }}>
          <ChartPanel title="Выдачи и возвраты">
            {charts.isPending ? (
              <ChartLoader />
            ) : charts.isError ? (
              <Text c="dimmed">Данные динамики временно недоступны</Text>
            ) : charts.data.turnover.every(
                (point) => point.checked_out === 0 && point.returned === 0,
              ) ? (
              <Text c="dimmed">За последние 12 месяцев выдач и возвратов не было</Text>
            ) : (
              <BarChart
                h={280}
                data={charts.data.turnover.map((point) => ({
                  ...point,
                  label: formatMonth(point.month),
                }))}
                dataKey="label"
                series={[
                  { name: 'checked_out', label: 'Выдано', color: 'blue.6' },
                  { name: 'returned', label: 'Возвращено', color: 'green.6' },
                ]}
                withLegend
                legendProps={{ verticalAlign: 'bottom', height: 36 }}
                gridAxis="y"
                yAxisProps={{ allowDecimals: false }}
              />
            )}
          </ChartPanel>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 6 }}>
          <ChartPanel title="Состояние парка">
            <FleetStatusChart counters={counters} />
          </ChartPanel>
        </Grid.Col>
        <Grid.Col span={12}>
          <ChartPanel title="Возраст просрочки">
            {charts.isPending ? (
              <ChartLoader />
            ) : charts.isError ? (
              <Text c="dimmed">Данные по просрочке временно недоступны</Text>
            ) : (
              <BarChart
                h={260}
                data={charts.data.overdue_buckets.map((bucket) => ({
                  label: overdueBucketLabel(bucket.bucket),
                  count: bucket.count,
                }))}
                dataKey="label"
                series={[{ name: 'count', label: 'Устройств', color: 'orange.6' }]}
                withLegend
                legendProps={{ verticalAlign: 'bottom', height: 36 }}
                gridAxis="y"
                yAxisProps={{ allowDecimals: false }}
              />
            )}
          </ChartPanel>
        </Grid.Col>
      </Grid>
    </>
  )
}

function ChartPanel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Paper h="100%" p="md" radius="md" withBorder>
      <Title order={5} mb="sm">
        {title}
      </Title>
      {children}
    </Paper>
  )
}

function ChartLoader() {
  return (
    <Center h={260}>
      <Loader size="sm" />
    </Center>
  )
}

function FleetStatusChart({ counters }: { counters: Counters }) {
  const data = [
    {
      name: 'Активно',
      value: counters.total_active - counters.in_repair - counters.lost,
      color: 'blue.6',
    },
    { name: 'В ремонте', value: counters.in_repair, color: 'yellow.6' },
    { name: 'Утеряно', value: counters.lost, color: 'red.6' },
    { name: 'В архиве', value: counters.archived, color: 'gray.6' },
  ]
  const total = data.reduce((sum, item) => sum + item.value, 0)

  if (total === 0) {
    return <Text c="dimmed">Нет устройств для отображения</Text>
  }

  return (
    <Center>
      <DonutChart
        data={data}
        size={220}
        thickness={30}
        withLegend
        chartLabel={String(total)}
      />
    </Center>
  )
}

function formatMonth(month: string): string {
  const [yearText, monthText] = month.split('-')
  const year = Number(yearText)
  const monthIndex = Number(monthText) - 1
  const label = new Intl.DateTimeFormat('ru-RU', { month: 'short' }).format(
    new Date(year, monthIndex, 1),
  )
  return monthIndex === 0 ? `${label} ${year}` : label
}

function overdueBucketLabel(bucket: string): string {
  return `${bucket.replace('-', '–')} дн.`
}
