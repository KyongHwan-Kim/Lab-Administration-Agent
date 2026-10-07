import { useEffect, useState } from "react";
import { api } from "../api";
import fallbackLogo from "../assets/aisl-logo.png";

export function BrandLogo({ revision = 0, className, alt = "AISL LAB" }) {
  const [src, setSrc] = useState(fallbackLogo);

  useEffect(() => {
    let active = true;
    let objectUrl = "";
    api(`/api/branding/logo?v=${revision}`)
      .then((blob) => {
        if (!active || !blob) return;
        objectUrl = URL.createObjectURL(blob);
        setSrc(objectUrl);
      })
      .catch(() => {
        if (active) setSrc(fallbackLogo);
      });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [revision]);

  return <img src={src} alt={alt} className={className} />;
}
