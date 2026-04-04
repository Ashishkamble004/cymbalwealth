import {
  AppBar as MuiAppBar,
  Toolbar,
  Box,
  Typography,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import ThemeToggle from './ThemeToggle';

export default function AppBar() {
  const navigate = useNavigate();

  return (
    <MuiAppBar
      position="static"
      color="default"
      elevation={0}
      sx={{
        borderBottom: '1px solid',
        borderColor: 'divider',
        boxShadow: 'none',
        backgroundColor: 'background.paper',
      }}
    >
      <Toolbar
        sx={{
          justifyContent: 'space-between',
          py: 1.5,
          minHeight: 'auto !important',
          maxWidth: '1280px',
          width: '100%',
          mx: 'auto',
          px: { xs: 2, md: 4 },
        }}
      >
        {/* CymbalWealth wordmark + Ad Studio badge */}
        <Box
          sx={{ display: 'flex', alignItems: 'center', gap: 1.5, cursor: 'pointer' }}
          onClick={() => navigate('/')}
        >
          <Box>
            <Typography
              variant="h6"
              sx={{
                fontWeight: 800,
                letterSpacing: '-0.03em',
                lineHeight: 1,
                color: 'primary.main',
                fontSize: '1.25rem',
              }}
            >
              Cymbal<Box component="span" sx={{ color: '#C5A55A' }}>Wealth</Box>
            </Typography>
            <Typography
              variant="overline"
              sx={{
                fontSize: '0.55rem',
                letterSpacing: '0.14em',
                color: 'text.secondary',
                lineHeight: 1,
                display: 'block',
                mt: 0.25,
              }}
            >
              Ad Studio
            </Typography>
          </Box>
          <Box
            sx={{
              px: 1,
              py: 0.25,
              borderRadius: '6px',
              background: 'linear-gradient(135deg, #791652, #9a2a6e)',
              display: { xs: 'none', sm: 'flex' },
              alignItems: 'center',
            }}
          >
            <Typography sx={{ fontSize: '0.6rem', fontWeight: 700, color: '#fff', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
              Powered by Gemini 3.1
            </Typography>
          </Box>
        </Box>

        {/* Nav links */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box
            component="a"
            href="/"
            sx={{
              display: { xs: 'none', md: 'block' },
              fontSize: '0.8rem',
              fontWeight: 500,
              color: 'text.secondary',
              textDecoration: 'none',
              px: 1.5,
              py: 0.5,
              borderRadius: 2,
              '&:hover': { color: 'primary.main', backgroundColor: 'primary.light' },
            }}
          >
            ← Back to CymbalWealth
          </Box>
          <ThemeToggle />
        </Box>
      </Toolbar>
    </MuiAppBar>
  );
}
