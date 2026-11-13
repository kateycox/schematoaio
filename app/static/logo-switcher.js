(function () {
  const FALLBACK_LOGOS = ["/schematoaio/static/logos/schematoaio-basic.png"];

  const ANIMATIONS = [
    {
      name: "poof",
      duration: 600,
      outStyle: (p) => ({
        transform: `scale(${1 + p * 1.5})`,
        opacity: 1 - p,
        filter: `blur(${p * 20}px)`,
      }),
      inStyle: (p) => ({
        transform: `scale(${0.3 + p * 0.7})`,
        opacity: p,
        filter: `blur(${(1 - p) * 10}px)`,
      }),
    },
    {
      name: "spin-away",
      duration: 700,
      outStyle: (p) => ({
        transform: `rotate(${p * 720}deg) scale(${1 - p})`,
        opacity: 1 - p,
      }),
      inStyle: (p) => ({
        transform: `rotate(${(1 - p) * -360}deg) scale(${p})`,
        opacity: p,
      }),
    },
    {
      name: "flip-x",
      duration: 600,
      outStyle: (p) => ({
        transform: `perspective(600px) rotateY(${p * 90}deg)`,
        opacity: 1 - p * 0.5,
      }),
      inStyle: (p) => ({
        transform: `perspective(600px) rotateY(${(1 - p) * -90}deg)`,
        opacity: 0.5 + p * 0.5,
      }),
    },
    {
      name: "flip-z",
      duration: 650,
      outStyle: (p) => ({
        transform: `perspective(600px) rotateX(${p * 90}deg) translateY(${p * 30}px)`,
        opacity: 1 - p,
      }),
      inStyle: (p) => ({
        transform: `perspective(600px) rotateX(${(1 - p) * -90}deg) translateY(${(1 - p) * -30}px)`,
        opacity: p,
      }),
    },
    {
      name: "slide-left",
      duration: 500,
      outStyle: (p) => ({
        transform: `translateX(${-p * 120}%) rotate(${-p * 15}deg)`,
        opacity: 1 - p,
      }),
      inStyle: (p) => ({
        transform: `translateX(${(1 - p) * 120}%) rotate(${(1 - p) * 15}deg)`,
        opacity: p,
      }),
    },
    {
      name: "slide-right",
      duration: 500,
      outStyle: (p) => ({
        transform: `translateX(${p * 120}%) rotate(${p * 15}deg)`,
        opacity: 1 - p,
      }),
      inStyle: (p) => ({
        transform: `translateX(${(1 - p) * -120}%) rotate(${(1 - p) * -15}deg)`,
        opacity: p,
      }),
    },
    {
      name: "squish",
      duration: 550,
      outStyle: (p) => ({
        transform: `scaleX(${1 + p * 0.5}) scaleY(${1 - p})`,
        opacity: 1 - p,
      }),
      inStyle: (p) => ({
        transform: `scaleX(${1 + (1 - p) * 0.5}) scaleY(${p})`,
        opacity: p,
      }),
    },
    {
      name: "dissolve",
      duration: 800,
      outStyle: (p) => ({
        opacity: 1 - p,
        filter: `saturate(${1 - p}) brightness(${1 + p * 2})`,
      }),
      inStyle: (p) => ({
        opacity: p,
        filter: `saturate(${p}) brightness(${1 + (1 - p) * 2})`,
      }),
    },
    {
      name: "bounce-drop",
      duration: 700,
      outStyle: (p) => ({
        transform: `translateY(${p * 200}px) rotate(${p * 30}deg)`,
        opacity: 1 - p,
      }),
      inStyle: (p) => {
        const bounce = Math.abs(Math.sin(p * Math.PI * 2.5)) * (1 - p) * 40;
        return {
          transform: `translateY(${-bounce + (1 - p) * -80}px)`,
          opacity: Math.min(1, p * 1.5),
        };
      },
    },
    {
      name: "glitch",
      duration: 500,
      outStyle: (p) => {
        const jitterX = (Math.random() - 0.5) * 30 * p;
        const jitterY = (Math.random() - 0.5) * 20 * p;
        return {
          transform: `translate(${jitterX}px, ${jitterY}px) skewX(${p * 20}deg)`,
          opacity: 1 - p,
          filter: `hue-rotate(${p * 180}deg)`,
        };
      },
      inStyle: (p) => {
        const jitterX = (Math.random() - 0.5) * 20 * (1 - p);
        const jitterY = (Math.random() - 0.5) * 15 * (1 - p);
        return {
          transform: `translate(${jitterX}px, ${jitterY}px) skewX(${(1 - p) * -15}deg)`,
          opacity: p,
          filter: `hue-rotate(${(1 - p) * 180}deg)`,
        };
      },
    },
    {
      name: "swirl",
      duration: 800,
      outStyle: (p) => ({
        transform: `rotate(${p * 360}deg) scale(${1 - p * 0.8})`,
        opacity: 1 - p,
        filter: `blur(${p * 8}px)`,
      }),
      inStyle: (p) => ({
        transform: `rotate(${(1 - p) * -360}deg) scale(${0.2 + p * 0.8})`,
        opacity: p,
        filter: `blur(${(1 - p) * 8}px)`,
      }),
    },
    {
      name: "zoom-punch",
      duration: 450,
      outStyle: (p) => ({
        transform: `scale(${1 + p * 3})`,
        opacity: 1 - p * 1.5,
      }),
      inStyle: (p) => {
        const overshoot = p < 0.7 ? (p / 0.7) * 1.15 : 1.15 - ((p - 0.7) / 0.3) * 0.15;
        return {
          transform: `scale(${overshoot})`,
          opacity: Math.min(1, p * 2),
        };
      },
    },
  ];

  function createShuffleBag(sourceArrayGetter) {
    let bag = [];
    let last = null;
    function refill() {
      const source = typeof sourceArrayGetter === "function" ? sourceArrayGetter() : sourceArrayGetter;
      bag = [...source];
      for (let i = bag.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [bag[i], bag[j]] = [bag[j], bag[i]];
      }
      if (bag.length > 1 && bag[bag.length - 1] === last) {
        const swapIdx = Math.floor(Math.random() * (bag.length - 1));
        [bag[bag.length - 1], bag[swapIdx]] = [bag[swapIdx], bag[bag.length - 1]];
      }
    }
    return function next() {
      if (bag.length === 0) refill();
      last = bag.pop();
      return last;
    };
  }

  function easeInOutCubic(t) {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }

  function applyStyle(el, styleObj) {
    el.style.transform = styleObj.transform || "";
    el.style.opacity = styleObj.opacity !== undefined ? styleObj.opacity : "";
    el.style.filter = styleObj.filter || "";
  }

  document.addEventListener("DOMContentLoaded", async () => {
    const wrapper = document.getElementById("logoSwitcher");
    const img = document.getElementById("logoImg");
    if (!wrapper || !img) return;

    let logos = FALLBACK_LOGOS;
    try {
      const res = await fetch("/schematoaio/logos");
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.logos) && data.logos.length > 0) {
          logos = data.logos;
        }
      }
    } catch (e) {
      console.warn("Failed to fetch logo list, using fallback", e);
    }

    logos.forEach((src) => {
      const preload = new Image();
      preload.src = src;
    });

    const nextAnim = createShuffleBag(ANIMATIONS);
    const nextLogo = createShuffleBag(() => logos);

    img.src = nextLogo();

    let isAnimating = false;
    let rafId = null;

    function trigger() {
      if (isAnimating) return;
      isAnimating = true;

      const anim = nextAnim();
      const newLogo = nextLogo();

      const halfDur = anim.duration / 2;
      let start = null;
      let swapped = false;

      const step = (timestamp) => {
        if (!start) start = timestamp;
        const elapsed = timestamp - start;

        if (elapsed < halfDur) {
          const p = easeInOutCubic(Math.min(1, elapsed / halfDur));
          applyStyle(img, anim.outStyle(p));
        } else if (elapsed < anim.duration) {
          if (!swapped) {
            img.src = newLogo;
            swapped = true;
          }
          const p = easeInOutCubic(Math.min(1, (elapsed - halfDur) / halfDur));
          applyStyle(img, anim.inStyle(p));
        } else {
          applyStyle(img, {});
          isAnimating = false;
          return;
        }
        rafId = requestAnimationFrame(step);
      };

      rafId = requestAnimationFrame(step);
    }

    wrapper.addEventListener("click", trigger);
    wrapper.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        trigger();
      }
    });

    // Expose trigger globally so other elements (e.g. Analyze button) can call it
    window.__logoSwitchTrigger = trigger;

    window.addEventListener("beforeunload", () => {
      if (rafId) cancelAnimationFrame(rafId);
    });
  });
})();
