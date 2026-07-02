/**
 * ECharts 按需引入，替代全局 import * as echarts from 'echarts'
 * 只注册项目实际使用的图表类型和组件，减少 ~800KB 打包体积
 */
import * as echarts from 'echarts/core'
import { BarChart, PieChart, MapChart } from 'echarts/charts'
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
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  BarChart,
  PieChart,
  MapChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  GeoComponent,
  VisualMapComponent,
  ToolboxComponent,
  GraphicComponent,
  DataZoomComponent,
  CanvasRenderer,
])

export default echarts
