import { createTheme } from '@mui/material/styles';

export const theme = createTheme({
  cssVariables: {
    colorSchemeSelector: 'class',
  },
  colorSchemes: {
    light: {
      palette: {
        primary: {
          main: '#791652',
          light: '#f5e6f0',
          dark: '#5a1040',
        },
        secondary: {
          main: '#C5A55A',
        },
        success: {
          main: '#1E8E3E',
          light: '#E6F4EA',
        },
        warning: {
          main: '#F9AB00',
          light: '#FEF7E0',
        },
        error: {
          main: '#D93025',
          light: '#FCE8E6',
        },
        background: {
          default: '#FAFAFA',
          paper: '#FFFFFF',
        },
        text: {
          primary: '#111827',
          secondary: '#6B7280',
        },
        divider: 'rgba(0,0,0,0.08)',
      },
    },
    dark: {
      palette: {
        primary: {
          main: '#c97ab0',
          light: '#4a0a2e',
          dark: '#e8c4dd',
        },
        secondary: {
          main: '#C4C7C5',
          light: '#474747',
        },
        success: {
          main: '#81C995',
          light: '#1B3726',
        },
        warning: {
          main: '#FDE293',
          light: '#4D360B',
        },
        error: {
          main: '#F28B82',
          light: '#3C2020',
        },
        background: {
          default: '#131314', // Google true dark
          paper: '#1E1F20',   // Elevated dark surface
        },
        text: {
          primary: '#E3E3E3',
          secondary: '#C4C7C5',
        },
        divider: 'rgba(255,255,255,0.08)',
      },
    },
  },
  typography: {
    fontFamily: '"Inter", system-ui, -apple-system, sans-serif',
    h1: {
      fontFamily: '"Inter", system-ui, -apple-system, sans-serif',
      fontWeight: 800,
      letterSpacing: '-0.02em',
    },
    h2: {
      fontFamily: '"Inter", system-ui, -apple-system, sans-serif',
      fontWeight: 700,
      letterSpacing: '-0.01em',
    },
    h3: {
      fontFamily: '"Inter", system-ui, -apple-system, sans-serif',
      fontWeight: 600,
    },
    h4: {
      fontFamily: '"Inter", system-ui, -apple-system, sans-serif',
      fontWeight: 600,
    },
    h5: {
      fontFamily: '"Inter", system-ui, -apple-system, sans-serif',
      fontWeight: 600,
    },
    h6: {
      fontFamily: '"Inter", system-ui, -apple-system, sans-serif',
      fontWeight: 600,
    },
    body1: {
      fontFamily: '"Inter", system-ui, -apple-system, sans-serif',
      letterSpacing: '0.01em',
    },
    body2: {
      fontFamily: '"Inter", system-ui, -apple-system, sans-serif',
      letterSpacing: '0.01em',
    },
    button: {
      fontFamily: '"Inter", system-ui, -apple-system, sans-serif',
      fontWeight: 600,
      letterSpacing: '0.02em',
    },
    caption: {
      fontFamily: '"Inter", system-ui, -apple-system, sans-serif',
    },
    overline: {
      fontFamily: '"Inter", system-ui, -apple-system, sans-serif',
      letterSpacing: '0.06em',
      fontWeight: 700,
      textTransform: 'uppercase',
    },
  },
  shape: {
    borderRadius: 16,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: ({ theme }) => ({
          borderRadius: 999, // Pill shape M3
          textTransform: 'none' as const,
          fontWeight: 600,
          boxShadow: 'none',
          padding: '8px 20px',
          transition: 'transform 0.2s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.2s cubic-bezier(0.4, 0, 0.2, 1), background-color 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            transform: 'translateY(-1px)',
          },
          '&:active': {
            transform: 'translateY(0)',
          },
          ...theme.applyStyles('dark', {
            '&:hover': {
              boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
            },
          })
        }),
        containedPrimary: ({ theme }) => ({
          background: 'linear-gradient(135deg, #791652 0%, #9a2a6e 100%)',
          color: '#FFFFFF',
          '&:hover': {
            background: 'linear-gradient(135deg, #5a1040 0%, #791652 100%)',
            boxShadow: '0 4px 12px rgba(121,22,82,0.35)',
          },
          ...theme.applyStyles('dark', {
            background: 'linear-gradient(135deg, #c97ab0 0%, #e8c4dd 100%)',
            color: '#2d0018',
            '&:hover': {
              background: 'linear-gradient(135deg, #e8c4dd 0%, #c97ab0 100%)',
              boxShadow: '0 4px 12px rgba(201,122,176,0.3)',
            },
          }),
        }),
      },
    },
    MuiCard: {
      styleOverrides: {
        root: ({ theme }) => ({
          borderRadius: 24,
          border: `1px solid ${theme.palette.divider}`,
          boxShadow: 'none',
          backgroundColor: '#FFFFFF',
          transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          backgroundImage: 'none',
          '&:hover': {
            boxShadow: '0 12px 32px rgba(121,22,82,0.08)',
            transform: 'translateY(-4px)',
          },
          ...theme.applyStyles('dark', {
            backgroundColor: '#1E1F20',
            '&:hover': {
              boxShadow: '0 12px 32px rgba(0,0,0,0.4)',
            }
          })
        }),
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: ({ theme }) => ({
          borderRadius: 24,
          boxShadow: 'none',
          backgroundImage: 'none',
          border: `1px solid ${theme.palette.divider}`,
          backgroundColor: theme.palette.background.paper,
          ...theme.applyStyles('dark', {
            backgroundColor: '#1E1F20', // dark surface container
          })
        }),
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          fontWeight: 500,
        },
      },
    },
    MuiTextField: {
      defaultProps: {
        variant: 'outlined' as const,
      },
      styleOverrides: {
        root: ({ theme }) => ({
          '& .MuiOutlinedInput-root': {
            borderRadius: 12,
            transition: 'box-shadow 0.2s ease',
            backgroundColor: 'transparent',
            '&:hover': {
              backgroundColor: 'rgba(0,0,0,0.01)',
            },
            '&.Mui-focused': {
              backgroundColor: 'transparent',
              boxShadow: `0 0 0 2px ${theme.palette.primary.light}`,
            },
          },
          ...theme.applyStyles('dark', {
            '& .MuiOutlinedInput-root': {
              '&:hover': {
                backgroundColor: 'rgba(255,255,255,0.01)',
              },
              '&.Mui-focused': {
                boxShadow: `0 0 0 2px ${theme.palette.primary.dark}`,
              },
            }
          })
        })
      }
    },
    MuiAppBar: {
      styleOverrides: {
        root: ({ theme }) => ({
          backgroundColor: 'transparent',
          color: theme.palette.text.primary,
          boxShadow: 'none',
          backgroundImage: 'none',
          borderBottom: 'none',
          transition: 'background-color 0.3s ease',
          ...theme.applyStyles('dark', {
            backgroundColor: 'transparent',
            backgroundImage: 'none',
          })
        }),
      },
    },
    MuiStepConnector: {
      styleOverrides: {
        line: ({ theme }) => ({
          borderColor: theme.palette.divider,
          borderTopWidth: 3,
          borderRadius: 2,
        }),
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          height: 6,
        },
      },
    },
    MuiStepIcon: {
      styleOverrides: {
        root: {
          color: '#e0c0d4',
          '&.Mui-active': { color: '#791652' },
          '&.Mui-completed': { color: '#791652' },
        },
      },
    },
    MuiStepLabel: {
      styleOverrides: {
        label: {
          '&.Mui-active': { color: '#791652', fontWeight: 700 },
          '&.Mui-completed': { color: '#791652' },
        },
      },
    },
    MuiSlider: {
      styleOverrides: {
        root: { color: '#791652' },
        thumb: {
          '&:hover, &.Mui-focusVisible': {
            boxShadow: '0 0 0 8px rgba(121,22,82,0.16)',
          },
        },
      },
    },
    MuiCheckbox: {
      styleOverrides: {
        root: {
          color: '#c0a0b8',
          '&.Mui-checked': { color: '#791652' },
        },
      },
    },
    MuiRadio: {
      styleOverrides: {
        root: {
          color: '#c0a0b8',
          '&.Mui-checked': { color: '#791652' },
        },
      },
    },
    MuiSwitch: {
      styleOverrides: {
        switchBase: {
          '&.Mui-checked': {
            color: '#791652',
            '& + .MuiSwitch-track': { backgroundColor: '#791652' },
          },
        },
      },
    },
    MuiFormLabel: {
      styleOverrides: {
        root: {
          '&.Mui-focused': { color: '#791652' },
        },
      },
    },
    MuiInputLabel: {
      styleOverrides: {
        root: {
          '&.Mui-focused': { color: '#791652' },
        },
      },
    },
    MuiSelect: {
      styleOverrides: {
        icon: { color: '#791652' },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
            borderColor: '#791652',
          },
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          '&.Mui-selected': { color: '#791652' },
        },
      },
    },
    MuiTabs: {
      styleOverrides: {
        indicator: { backgroundColor: '#791652' },
      },
    },
    MuiToggleButton: {
      styleOverrides: {
        root: {
          '&.Mui-selected': {
            color: '#ffffff',
            backgroundColor: '#791652',
            '&:hover': { backgroundColor: '#5a1040' },
          },
        },
      },
    },
    MuiLink: {
      styleOverrides: {
        root: { color: '#791652' },
      },
    },
    MuiCircularProgress: {
      styleOverrides: {
        root: { color: '#791652' },
      },
    },
    MuiTableHead: {
      styleOverrides: {
        root: ({ theme }) => ({
          '& .MuiTableCell-head': {
            backgroundColor: '#F1F3F4',
            color: theme.palette.text.primary,
            fontWeight: 600,
          },
          ...theme.applyStyles('dark', {
            '& .MuiTableCell-head': {
              backgroundColor: '#282A2C',
              color: '#E3E3E3',
            },
          }),
        }),
      },
    },
  },
});
