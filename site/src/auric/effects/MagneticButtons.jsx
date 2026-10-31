import { useEffect } from 'react';
import { enhance, canHover, springValue, lerp } from '../kit.js';

export default function MagneticButtons() {
  useEffect(() => {
    if (!canHover()) return undefined;

    return enhance('.btn', (el) => {
      const onMouseMove = (e) => {
        const rect = el.getBoundingClientRect();
        const dx = e.clientX - rect.left - rect.width / 2;
        const dy = e.clientY - rect.top - rect.height / 2;
        const distance = Math.sqrt(dx * dx + dy * dy);

        if (distance < 8) {
          const spring = springValue(([tx, ty]) => {
            el.style.transform = `translate(${tx}px, ${ty}px)`;
          }, { initial: [0, 0] });

          spring.set([
            lerp(dx, 0, Math.min(distance / 8, 1)),
            lerp(dy, 0, Math.min(distance / 8, 1))
          ]);
        } else {
          el.style.transform = '';
        }
      };

      const onMouseLeave = () => {
        el.style.transform = '';
      };

      el.addEventListener('pointermove', onMouseMove);
      el.addEventListener('pointerleave', onMouseLeave);

      return () => {
        el.removeEventListener('pointermove', onMouseMove);
        el.removeEventListener('pointerleave', onMouseLeave);
        el.style.transform = '';
      };
    });
  }, []);

  return null;
}
