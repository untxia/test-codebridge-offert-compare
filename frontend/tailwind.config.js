module.exports = {
  content: ['../public/index.html', '../public/app.js'],
  theme: {
    extend: {
      colors: {
        night: '#0A0F1F', vellum: '#F4F6FF', ink: '#E9EDFB', mist: '#9AA6C6',
        cobalt: { DEFAULT: '#6C7CFF', deep: '#4C5CF0' }, marker: '#FFD23F', mint: '#4ADEA8', coral: '#FF7A66', sky: '#7FB8FF', amber: '#FFC266',
      },
      fontFamily: { display: ['"Bricolage Grotesque"', 'system-ui', 'sans-serif'], sans: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'] },
    },
  },
};
