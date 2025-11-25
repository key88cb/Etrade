## 技术栈

- **前端框架**: React 18 + TypeScript
- **构建工具**: Vite 5
- **样式方案**: Tailwind CSS 4.0
- **图表库**: ECharts 5
- **图标库**: Lucide React

## 快速开始

### 1. 安装依赖

确保你的电脑上已安装 [Node.js](https://nodejs.org/) (建议 v18 或更高版本)。

```bash
# 使用 npm
npm install

# 或使用 yarn
yarn install

# 或使用 pnpm
pnpm install
```

### 2. 启动开发服务器

```bash
# 使用 npm
npm run dev

# 或使用 yarn
yarn dev

# 或使用 pnpm
pnpm dev
```

开发服务器将在 `http://localhost:3000` 启动，浏览器会自动打开。

### 3. 构建生产版本

```bash
# 使用 npm
npm run build

# 或使用 yarn
yarn build

# 或使用 pnpm
pnpm build
```

构建完成后，产物在 `dist` 目录。

### 4. 预览生产构建

```bash
# 使用 npm
npm run preview

# 或使用 yarn
yarn preview

# 或使用 pnpm
pnpm preview
```

## 项目结构

```
frontend_demo/
├── src/
│   ├── components/          # React 组件
│   │   ├── PriceComparison.tsx
│   │   ├── ArbitrageOpportunities.tsx
│   │   └── DataManagement.tsx
│   ├── styles/
│   │   └── globals.css      # 全局样式和 Tailwind 配置
│   ├── App.tsx              # 主应用组件
│   └── main.tsx             # 应用入口
├── index.html               # HTML 模板
├── vite.config.ts           # Vite 配置
├── package.json             # 项目依赖
└── README.md                # 项目说明
```

## 核心依赖

```json
{
  "react": "^18.3.1",
  "react-dom": "^18.3.1",
  "echarts": "^5.5.0",
  "lucide-react": "^0.454.0",
  "tailwindcss": "^4.0.0"
}
```

## 页面说明

### 1. Price Comparison (价格对比)
- 可视化对比 Uniswap V3 和 Binance 的 USDT/ETH 价格走势
- 支持自定义日期范围 (2025年9月)
- 交互式图表：缩放、平移、悬停显示详细信息

### 2. Arbitrage Opportunities (套利机会)
- 展示已识别的套利机会列表
- 统计卡片：总机会数、最大利润、平均利润、潜在总利润
- 可排序表格：支持按时间、利润等字段排序
- 分页功能：每页显示 10 条记录

### 3. Data Management (数据管理)
- 配置参数：时间范围、Pool 地址、聚合粒度等
- 任务执行：数据采集、聚合、分析
- 系统状态监控：数据库连接、记录数量

## 主题切换

点击右上角的太阳/月亮图标即可在白天模式和黑夜模式之间切换。

- **黑夜模式** (默认): GitHub Dark 配色方案
- **白天模式**: GitHub Light 配色方案

## 开发说明

### 添加新组件

1. 在 `src/components/` 目录创建新的 `.tsx` 文件
2. 接收 `theme` prop 以支持主题切换
3. 在 `App.tsx` 中导入并使用

### 修改主题颜色

编辑 `src/styles/globals.css` 文件中的 CSS 变量。

### 自定义图表

修改 `PriceComparison.tsx` 中的 ECharts 配置选项。

## 浏览器支持

- Chrome (推荐)
- Firefox
- Safari
- Edge

## 许可证

MIT


