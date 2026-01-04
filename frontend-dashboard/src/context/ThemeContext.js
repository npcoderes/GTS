import React, { createContext, useState, useContext, useEffect } from 'react';

const ThemeContext = createContext(null);

// Theme configurations
// Theme configurations
export const themes = {
  light: {
    name: 'light',
    token: {
      colorPrimary: '#4F46E5', // Indigo 600
      colorBgContainer: '#ffffff',
      colorBgLayout: '#F8FAFC', // Slate 50
      colorText: '#0F172A', // Slate 900
      colorTextSecondary: '#64748B', // Slate 500
      colorBorder: '#E2E8F0', // Slate 200
      borderRadius: 10,
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    },
    sider: {
      background: '#ffffff',
      textColor: '#0F172A',
      selectedBg: '#EEF2FF', // Indigo 50
      selectedColor: '#4F46E5', // Indigo 600
      borderRight: '1px solid #E2E8F0',
    },
    header: {
      background: 'rgba(255, 255, 255, 0.8)',
      textColor: '#0F172A',
      backdropFilter: 'blur(12px)',
      boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.05)',
    },
    card: {
      background: '#ffffff',
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03)',
      border: '1px solid #E2E8F0',
      borderRadius: '12px',
    },
  },
  dark: {
    name: 'dark',
    token: {
      colorPrimary: '#6366F1', // Indigo 500
      colorBgContainer: '#1E293B', // Slate 800
      colorBgLayout: '#0F172A', // Slate 900
      colorText: '#F8FAFC', // Slate 50
      colorTextSecondary: '#94A3B8', // Slate 400
      colorBorder: '#334155', // Slate 700
      borderRadius: 10,
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.18)',
    },
    sider: {
      background: '#1E293B', // Slate 800
      textColor: '#F8FAFC',
      selectedBg: '#312E81', // Indigo 900
      selectedColor: '#818CF8', // Indigo 400
      borderRight: '1px solid #334155',
    },
    header: {
      background: 'rgba(30, 41, 59, 0.8)', // Slate 800 with opacity
      textColor: '#F8FAFC',
      backdropFilter: 'blur(12px)',
      boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.3)',
    },
    card: {
      background: '#1E293B', // Slate 800
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.18)',
      border: '1px solid #334155',
      borderRadius: '12px',
    },
  },
};

export const ThemeProvider = ({ children }) => {
  // Initialize from localStorage or default to light
  const [themeName, setThemeName] = useState(() => {
    const saved = localStorage.getItem('gts-theme');
    return saved || 'light';
  });

  const theme = themes[themeName];

  // Persist theme choice
  useEffect(() => {
    localStorage.setItem('gts-theme', themeName);

    // Update body class for CSS variables
    document.body.classList.remove('theme-light', 'theme-dark');
    document.body.classList.add(`theme-${themeName}`);

    // Update background color
    document.body.style.background = theme.token.colorBgLayout;
  }, [themeName, theme]);

  const toggleTheme = () => {
    setThemeName(prev => prev === 'light' ? 'dark' : 'light');
  };

  const setTheme = (name) => {
    if (themes[name]) {
      setThemeName(name);
    }
  };

  const value = {
    theme,
    themeName,
    isDark: themeName === 'dark',
    toggleTheme,
    setTheme,
  };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

export default ThemeContext;
