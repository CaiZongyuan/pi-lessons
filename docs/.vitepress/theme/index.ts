import DefaultTheme from 'vitepress/theme'
import { h } from 'vue'
import BookLibrary from './components/BookLibrary.vue'
import SidebarToggle from './components/SidebarToggle.vue'
import ManualFigure from './components/ManualFigure.vue'
import BookFigure from './components/BookFigure.vue'
import AdjustableTable from './components/AdjustableTable.vue'
import '@fontsource/manrope/600.css'
import '@fontsource/manrope/700.css'
import '@fontsource/source-sans-3/400.css'
import '@fontsource/source-sans-3/600.css'
import '@fontsource/source-serif-4/400-italic.css'
import '@fontsource/jetbrains-mono/400.css'
import './style.css'
export default {
 extends: DefaultTheme,
 Layout: () => h(DefaultTheme.Layout, null, { 'nav-bar-content-after': () => h(SidebarToggle) }),
 enhanceApp({app}) { app.component('BookLibrary',BookLibrary); app.component('ManualFigure',ManualFigure); app.component('BookFigure',BookFigure); app.component('AdjustableTable',AdjustableTable) }
}
