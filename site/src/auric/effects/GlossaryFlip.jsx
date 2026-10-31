import { useEffect } from 'react';
import { enhance, canHover, reducedMotion, animate } from '../kit.js';

export default function GlossaryFlip() {
  useEffect(() => {
    if (!canHover()) return undefined;

    return enhance('dl.glossary > div', (glossaryItem) => {
      glossaryItem.classList.add('ax-glossary-flip');

      const term = glossaryItem.querySelector('dt');
      const definition = glossaryItem.querySelector('dd');

      term.style.position = 'relative';
      term.style.zIndex = '2';
      definition.style.position = 'absolute';
      definition.style.backfaceVisibility = 'hidden';
      definition.style.transition = 'transform 0.35s cubic-bezier(.2,.8,.2,1)';
      definition.style.transformStyle = 'preserve-3d';
      definition.style.transform = 'rotateY(180deg) translateZ(0)';

      const flip = () => {
        if (reducedMotion()) {
          term.style.transform = 'none';
          definition.style.transform = 'none';
        } else {
          animate({
            from: { termTransform: 'none', definitionTransform: 'rotateY(180deg)' },
            to: { termTransform: 'rotateY(180deg)', definitionTransform: 'none' },
            duration: 350,
            onUpdate: ({ termTransform, definitionTransform }) => {
              term.style.transform = termTransform;
              definition.style.transform = definitionTransform;
            },
            onDone: () => {
              term.style.transform = 'none';
              definition.style.transform = 'none';
            }
          });
        }
      };

      glossaryItem.addEventListener('click', flip);
      glossaryItem.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          flip();
        }
      });

      // Add tabIndex and role attributes for accessibility
      term.tabIndex = 0;
      term.setAttribute('role', 'button');
      term.setAttribute('aria-pressed', 'false');

      return () => {
        glossaryItem.removeEventListener('click', flip);
        glossaryItem.removeEventListener('keydown', flip);
        glossaryItem.classList.remove('ax-glossary-flip');
        term.removeAttribute('tabIndex');
        term.removeAttribute('role');
        term.removeAttribute('aria-pressed');
      };
    });
  }, []);

  return null;
}
