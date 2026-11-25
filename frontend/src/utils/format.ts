export const languageName = (code: string) =>
  ({
    hi: "Hindi",
    en: "English",
    auto: "Auto-detect",
    "hi-en": "Hindi + English",
  })[code] || code.toUpperCase();
export function duration(seconds: number) {
  const total = Math.floor(seconds);
  return `${Math.floor(total / 60)
    .toString()
    .padStart(2, "0")}:${(total % 60).toString().padStart(2, "0")}`;
}
export function download(text: string, title: string) {
  const url = URL.createObjectURL(
    new Blob([text], { type: "text/plain;charset=utf-8" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = `${title.replace(/[^\p{L}\p{N} _-]/gu, "").slice(0, 100) || "transcript"}.txt`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
