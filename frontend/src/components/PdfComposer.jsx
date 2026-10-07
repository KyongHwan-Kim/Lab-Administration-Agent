import { useEffect, useMemo, useState } from "react";
import { api, downloadBlob } from "../api";

export function PdfComposer() {
  const [delivery, setDelivery] = useState([]);
  const [receipt, setReceipt] = useState([]);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [extracted, setExtracted] = useState([]);

  const deliveryPreviews = useMemo(
    () => delivery.map((file) => ({ file, url: URL.createObjectURL(file) })),
    [delivery],
  );
  const receiptPreviews = useMemo(
    () => receipt.map((file) => ({ file, url: URL.createObjectURL(file) })),
    [receipt],
  );
  const previewCount = deliveryPreviews.length + receiptPreviews.length;

  useEffect(() => {
    return () => {
      deliveryPreviews.forEach((item) => URL.revokeObjectURL(item.url));
      receiptPreviews.forEach((item) => URL.revokeObjectURL(item.url));
    };
  }, [deliveryPreviews, receiptPreviews]);

  async function extract() {
    setError("");
    setExtracting(true);
    try {
      const body = new FormData();
      delivery.forEach((file) => body.append("delivery", file));
      receipt.forEach((file) => body.append("receipt", file));
      const result = await api("/api/overtime/receipts", { method: "POST", body });
      setExtracted(result.items || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setExtracting(false);
    }
  }

  async function download() {
    setError("");
    setPending(true);
    try {
      const body = new FormData();
      delivery.forEach((file) => body.append("delivery", file));
      receipt.forEach((file) => body.append("receipt", file));
      const blob = await api("/api/overtime/pdf", { method: "POST", body });
      downloadBlob(blob, "증빙.pdf");
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="rounded-3xl border border-line bg-card p-4 sm:p-6">
      <div className="flex flex-wrap justify-end gap-2">
        <button
          type="button"
          disabled={pending || extracting || previewCount === 0}
          onClick={extract}
          className="rounded-xl bg-pine px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {extracting ? "추출 중" : "항목 추출"}
        </button>
        <button
          type="button"
          disabled={pending || extracting || previewCount === 0}
          onClick={download}
          className="rounded-xl bg-copper px-4 py-2 text-sm font-medium text-white hover:bg-copper-dark disabled:opacity-50"
        >
          {pending ? "만드는 중" : "PDF 다운로드"}
        </button>
      </div>
      <p className="mt-3 text-xs text-muted">
        같은 결제는 항목 하나입니다. 영수증 카드 번호의 끝자리가 프로젝트에 등록된 끝자리와 같으면 그 프로젝트로 배정되고, 아니면 프로젝트 할당 전에 들어갑니다. 회의시간은 사용시각 앞뒤 2시간, 추천 인원 수는 1인 12,000원 한도의 올림입니다.
      </p>
      {extracted.length > 0 && (
        <ul className="mt-3 space-y-1 text-sm">
          {extracted.map((item) => (
            <li key={item.id} className="rounded-xl bg-paper px-3 py-2">
              {[item.project_name || "프로젝트 할당 전", item.values?.사용일자, item.values?.사용시각, item.values?.사용처, item.values?.사용금액, item.values?.회의시간, item.values?.회의장소, item.values?.추천인원 ? `추천 인원 수 ${item.values.추천인원}` : item.values?.총인원]
                .filter(Boolean)
                .join(" · ") || "읽은 내용이 없습니다. 프로젝트 할당 전에서 직접 입력해 주세요."}
            </li>
          ))}
        </ul>
      )}
      <div className="mt-5 grid gap-5 lg:grid-cols-[280px_minmax(0,1fr)]">
        <div className="space-y-4">
          <FileField label="배달 내역" files={delivery} onChange={setDelivery} />
          <FileField label="영수증" files={receipt} onChange={setReceipt} />
          {error && <p className="text-sm text-copper">{error}</p>}
        </div>
        <div className="min-h-40 space-y-4 rounded-2xl bg-paper p-3">
          {previewCount === 0 ? (
            <p className="grid h-full min-h-32 place-items-center text-sm text-muted">
              사진을 올리면 배달 내역과 영수증이 한 줄에 가로로 배치됩니다.
            </p>
          ) : (
            <div
              className="grid gap-2"
              style={{ gridTemplateColumns: `repeat(${previewCount}, minmax(0, 1fr))` }}
            >
              {deliveryPreviews.map((item) => (
                <PreviewFigure key={item.url} item={item} label="배달 내역" />
              ))}
              {receiptPreviews.map((item) => (
                <PreviewFigure key={item.url} item={item} label="영수증" />
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function PreviewFigure({ item, label }) {
  return (
    <figure className="overflow-hidden rounded-xl bg-white">
      <img src={item.url} alt={label} className="h-36 w-full object-contain" />
      <figcaption className="px-2 py-1 text-center text-xs text-muted">{label}</figcaption>
    </figure>
  );
}

function FileField({ label, files, onChange }) {
  return (
    <label className="block rounded-2xl border border-dashed border-line px-3 py-3 text-sm">
      <span className="font-medium">{label}</span>
      <span className="mt-1 block text-muted">{files.length ? `${files.length}장 선택` : "사진 선택"}</span>
      <input
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple
        className="mt-2 block w-full text-xs"
        onChange={(event) => onChange(Array.from(event.target.files || []))}
      />
    </label>
  );
}
