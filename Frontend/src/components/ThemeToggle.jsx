import { useTheme } from "../context/ThemeContext";
import { IconSun, IconMoon } from "./Icons";

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  return (
    <button
      className="theme-toggle"
      onClick={toggleTheme}
      aria-label="Toggle dark/light mode"
      title="Toggle theme"
    >
      {theme === "dark" ? <IconSun /> : <IconMoon />}
    </button>
  );
}
