import { useLang } from "../../context/LangContext.jsx";
import Chip from "./Chip.jsx";

export default function LangToggle() {
  const { toggleLang, copy } = useLang();
  return <Chip onClick={toggleLang}>{copy.home.langSwitch}</Chip>;
}
