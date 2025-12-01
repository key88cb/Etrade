/**
 * 主题管理工具
 * 自动检测系统暗色模式偏好，并持久化到 localStorage
 */

const THEME_STORAGE_KEY = 'app-theme-preference';

export type ThemeMode = 'light' | 'dark' | 'auto';

/**
 * 检测系统是否偏好暗色模式
 */
function prefersDarkMode(): boolean {
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

/**
 * 应用主题到文档
 */
function applyTheme(isDark: boolean): void {
  const html = document.documentElement;
  if (isDark) {
    html.classList.add('dark');
  } else {
    html.classList.remove('dark');
  }
}

/**
 * 获取当前主题模式
 */
export function getThemeMode(): ThemeMode {
  const stored = localStorage.getItem(THEME_STORAGE_KEY);
  if (stored === 'light' || stored === 'dark' || stored === 'auto') {
    return stored;
  }
  return 'auto';
}

/**
 * 设置主题模式
 */
export function setThemeMode(mode: ThemeMode): void {
  localStorage.setItem(THEME_STORAGE_KEY, mode);
  updateTheme();
}

/**
 * 获取当前实际的主题状态（是否为暗色）
 */
export function isDarkMode(): boolean {
  const mode = getThemeMode();
  if (mode === 'dark') {
    return true;
  }
  if (mode === 'light') {
    return false;
  }
  // auto 模式：使用系统偏好
  return prefersDarkMode();
}

/**
 * 更新主题（根据当前设置）
 */
export function updateTheme(): void {
  const isDark = isDarkMode();
  applyTheme(isDark);
}

/**
 * 初始化主题（在应用启动时调用）
 */
export function initTheme(): void {
  // 立即应用主题，避免闪烁
  updateTheme();

  // 监听系统主题变化（仅在 auto 模式下有效）
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
  const handleChange = () => {
    if (getThemeMode() === 'auto') {
      updateTheme();
    }
  };

  // 使用 addEventListener 而不是 addListener（更现代的方式）
  if (mediaQuery.addEventListener) {
    mediaQuery.addEventListener('change', handleChange);
  } else {
    // 兼容旧浏览器
    mediaQuery.addListener(handleChange);
  }
}

