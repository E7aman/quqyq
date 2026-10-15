import { useEffect, useRef } from "react";

// Lightweight pointer-reactive dot field inspired by the supplied visual reference.
export default function BackgroundField() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return undefined;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const pointer = { x: -999, y: -999, targetX: -999, targetY: -999 };
    const ripples = [];
    let width = 0;
    let height = 0;
    let frame = 0;
    let visible = true;
    const gap = 36;

    const resize = () => {
      const ratio = Math.min(window.devicePixelRatio || 1, 1.5);
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = Math.floor(width * ratio);
      canvas.height = Math.floor(height * ratio);
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      if (reduceMotion) draw(0);
    };

    const draw = (time) => {
      pointer.x += (pointer.targetX - pointer.x) * 0.12;
      pointer.y += (pointer.targetY - pointer.y) * 0.12;
      context.clearRect(0, 0, width, height);
      for (let x = gap / 2; x < width; x += gap) {
        for (let y = gap / 2; y < height; y += gap) {
          const dx = x - pointer.x;
          const dy = y - pointer.y;
          const distance = Math.hypot(dx, dy) || 1;
          const force = Math.max(0, 1 - distance / 210);
          let px = x + (dx / distance) * force * force * 26;
          let py = y + (dy / distance) * force * force * 26;
          for (const ripple of ripples) {
            const rd = Math.hypot(x - ripple.x, y - ripple.y) || 1;
            const strength = Math.exp(-(((rd - ripple.radius) / 48) ** 2)) * ripple.alpha;
            px += ((x - ripple.x) / rd) * strength * 12;
            py += ((y - ripple.y) / rd) * strength * 12;
          }
          const wave = Math.sin(x * 0.009 + y * 0.008 + time * 0.00065) * 0.5 + 0.5;
          context.fillStyle = `rgba(167, 139, 250, ${0.11 + wave * 0.1 + force * 0.65})`;
          context.beginPath();
          context.arc(px, py, 0.8 + wave * 0.55 + force * 2, 0, Math.PI * 2);
          context.fill();
        }
      }
      ripples.forEach((ripple) => { ripple.radius += 7; ripple.alpha *= 0.965; });
      while (ripples.length && ripples[0].alpha < 0.035) ripples.shift();
      if (!reduceMotion && visible) frame = requestAnimationFrame(draw);
    };

    const move = (event) => {
      pointer.targetX = event.clientX;
      pointer.targetY = event.clientY;
    };
    const ripple = (event) => ripples.push({ x: event.clientX, y: event.clientY, radius: 0, alpha: 0.8 });
    const observer = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      cancelAnimationFrame(frame);
      if (visible && !reduceMotion) frame = requestAnimationFrame(draw);
    });
    observer.observe(canvas);
    resize();
    if (!reduceMotion) frame = requestAnimationFrame(draw);
    window.addEventListener("resize", resize, { passive: true });
    window.addEventListener("pointermove", move, { passive: true });
    window.addEventListener("pointerdown", ripple, { passive: true });
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerdown", ripple);
    };
  }, []);

  return <canvas ref={canvasRef} className="background-field" aria-hidden="true" />;
}
