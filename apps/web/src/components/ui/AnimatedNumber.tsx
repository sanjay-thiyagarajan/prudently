"use client";

import { animate, useMotionValue, useTransform } from "framer-motion";
import { useEffect, useRef, useState } from "react";

export function AnimatedNumber({ value }: { value: number }) {
  const motionValue = useMotionValue(0);
  const rounded = useTransform(motionValue, (latest) => Math.round(latest).toLocaleString());
  const [display, setDisplay] = useState("0");
  const previous = useRef(0);

  useEffect(() => {
    const controls = animate(motionValue, value, { duration: 0.7, ease: "easeOut" });
    const unsubscribe = rounded.on("change", setDisplay);
    previous.current = value;
    return () => {
      controls.stop();
      unsubscribe();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return <span>{display}</span>;
}
