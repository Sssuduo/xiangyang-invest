/**
 * ECharts 按需引入，替代全局 import * as echarts from 'echarts'
 * 只注册项目实际使用的图表类型和组件，减少 ~800KB 打包体积
 */
import * as echarts from 'echarts/core'
import { BarChart, PieChart, MapChart, RadarChart, LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  GeoComponent,
  VisualMapComponent,
  ToolboxComponent,
  GraphicComponent,
  DataZoomComponent,
  RadarComponent,
  MarkLineComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  BarChart,
  PieChart,
  MapChart,
  RadarChart,
  LineChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  GeoComponent,
  VisualMapComponent,
  ToolboxComponent,
  GraphicComponent,
  DataZoomComponent,
  RadarComponent,
  MarkLineComponent,
  CanvasRenderer,
])

export default echarts
