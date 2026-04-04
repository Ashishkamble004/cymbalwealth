import { Box, Typography, Link } from '@mui/material';

export default function Footer() {
  return (
    <Box
      component="footer"
      sx={{
        mt: 'auto',
        py: 3,
        px: 2,
        textAlign: 'center',
        backgroundColor: 'background.paper',
        borderTop: '1px solid',
        borderColor: 'divider',
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 1, mb: 0.5 }}>
        <Typography variant="body2" sx={{ fontWeight: 800, color: 'primary.main', letterSpacing: '-0.02em' }}>
          Cymbal<Box component="span" sx={{ color: '#C5A55A' }}>Wealth</Box>
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
          Ad Studio
        </Typography>
      </Box>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
        Powered by Gemini 3.1 Pro · Veo 3.1 · Imagen 4
      </Typography>
      <Link
        href="https://cymbalwealth.ak-demos.com"
        target="_blank"
        rel="noopener noreferrer"
        underline="hover"
        sx={{ fontSize: '0.75rem', color: 'primary.main', fontWeight: 500 }}
      >
        ← Return to CymbalWealth
      </Link>
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 0.5, mt: 1.5 }}>
        <Typography variant="caption" color="text.disabled">
          By
        </Typography>
        <Link href="https://www.linkedin.com/in/sunilkumar88/" target="_blank" rel="noopener noreferrer" underline="hover" sx={{ fontSize: '0.7rem', color: 'text.secondary' }}>Sunil Kumar</Link>
        <Typography variant="caption" color="text.disabled">•</Typography>
        <Link href="https://www.linkedin.com/in/gopaladhar/" target="_blank" rel="noopener noreferrer" underline="hover" sx={{ fontSize: '0.7rem', color: 'text.secondary' }}>Gopala Dhar</Link>
        <Typography variant="caption" color="text.disabled">•</Typography>
        <Link href="https://www.linkedin.com/in/lavinigam/" target="_blank" rel="noopener noreferrer" underline="hover" sx={{ fontSize: '0.7rem', color: 'text.secondary' }}>Lavi Nigam</Link>
      </Box>
    </Box>
  );
}
