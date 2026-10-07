import { useEffect, useState } from "react";
import { api } from "../api";

export function BrandLogo({ revision = 0, className, alt = "로고" }) {
  const [src, setSrc] = useState("");

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
        if (active) setSrc("");
      });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [revision]);

  if (!src) return null;
  return <img src={src} alt={alt} className={className} />;
}
