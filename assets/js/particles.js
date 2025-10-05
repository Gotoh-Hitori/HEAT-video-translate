// 粒子特效配置，基于 tsParticles CDN
window.addEventListener('DOMContentLoaded', function() {
  if (!window.tsParticles) return;
  tsParticles.load('particles-bg', {
    background: {
      color: { value: '#000' }
    },
    fpsLimit: 60,
    particles: {
      number: { value: 60, density: { enable: true, area: 800 } },
      color: { value: '#b3002d' },
      shape: { type: 'circle' },
      opacity: { value: 0.5 },
      size: { value: { min: 2, max: 4 } },
      move: {
        enable: true,
        speed: 1.5,
        direction: 'none',
        outModes: { default: 'out' }
      },
      links: {
        enable: true,
        color: '#b3002d',
        distance: 120,
        opacity: 0.2,
        width: 1
      }
    },
    detectRetina: true
  });
});
