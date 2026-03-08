#!/usr/bin/env python3
"""
PDF klasöründeki her dosya için hedef şirket ilanının tam metnini çıkarır.
Çıktı: --output-dir altında her PDF için <isim>_metin.txt

Kullanım:
  python scripts/run_extract_text.py --pdf-dir path/to/pdfs --target-company-name "Parla Enerji" --output-dir result/
"""

import argparse
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.pipelines.document_text_extraction import DocumentTextExtractionPipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Belge bazlı metin çıkarımı (hedef şirket)"
    )
    parser.add_argument("--pdf-dir", type=Path, required=True, help="PDF klasörü")
    parser.add_argument("--target-company-name", type=str, default=None)
    parser.add_argument("--target-mersis", type=str, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    if not args.target_company_name and not args.target_mersis:
        print("--target-company-name veya --target-mersis gerekli", file=sys.stderr)
        sys.exit(1)

    pdf_dir = args.pdf_dir.resolve()
    if not pdf_dir.is_dir():
        print(f"Klasör yok: {pdf_dir}", file=sys.stderr)
        sys.exit(1)
    out_dir = (args.output_dir or pdf_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    pipeline = DocumentTextExtractionPipeline(
        target_company_name=args.target_company_name,
        target_mersis=args.target_mersis,
    )
    for path in sorted(pdf_dir.glob("*.pdf")):
        try:
            result = pipeline.run_full(path)
        except Exception as e:
            print(f"Atlandı {path}: {e}", file=sys.stderr)
            continue
        full_text = result.get("full_text", "")
        out_path = out_dir / f"{path.stem}_metin.txt"
        out_path.write_text(full_text or result.get("error", ""), encoding="utf-8")
        print(f"Yazıldı: {out_path}")


if __name__ == "__main__":
    main()
