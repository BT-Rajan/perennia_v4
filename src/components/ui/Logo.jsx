import { useState } from "react";
import { useLang } from "../../context/LangContext.jsx";
import "./Logo.css";

/**
 * Logo image URL and wordmark text both come from live branding config
 * (branding.logo_url / branding.site_name — see useLang()), so swapping
 * either from the admin panel needs no rebuild. Shows the image OR the
 * site-name wordmark — never both — falling back to the text if there's
 * no logo configured or the image fails to load.
 */
export default function Logo() {
  const { branding } = useLang();
  const [imgFailed, setImgFailed] = useState(false);

  const showImage = branding.logoUrl && !imgFailed;

  return (
    <div className="logo">
      {showImage ? (
        <img
          className="logo-img"
          style={{ "--logo-scale": branding.logoScale || 1 }}
          src={branding.logoUrl}
          alt={`${branding.siteName} logo`}
          onError={() => setImgFailed(true)}
        />
      ) : (
        <span className="logo-word">{branding.siteName}</span>
      )}
    </div>
  );
}
