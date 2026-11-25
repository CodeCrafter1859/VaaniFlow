import { Copy, Download } from "lucide-react";
import { useToast } from "../../context/ToastContext";
import { download } from "../../utils/format";
export function TranscriptActions({
  text,
  title,
}: {
  text: string;
  title: string;
}) {
  const toast = useToast();
  return (
    <>
      <button
        className="button secondary"
        disabled={!text}
        onClick={() => {
          navigator.clipboard
            .writeText(text)
            .then(() => toast("Transcript copied"))
            .catch(() =>
              toast("Clipboard unavailable. Download the transcript instead."),
            );
        }}
      >
        <Copy size={16} />
        Copy
      </button>
      <button
        className="button secondary"
        disabled={!text}
        onClick={() => download(text, title)}
      >
        <Download size={16} />
        Download
      </button>
    </>
  );
}
