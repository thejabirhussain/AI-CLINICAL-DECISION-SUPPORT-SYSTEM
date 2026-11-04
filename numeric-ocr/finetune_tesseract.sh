#!/usr/bin/env bash
# Fine-tune Tesseract 5.5's English LSTM (tessdata_best) on low-resolution clinical numerics.
# Standard tesstrain recipe, done by hand: line boxes -> .lstmf -> lstmtraining --continue_from -> traineddata.
#   ./finetune_tesseract.sh [iterations]
#   RESUME=1 ./finetune_tesseract.sh [iterations]   # skip data prep, continue from $WORK/${NAME}_checkpoint
#   NAME=labnum2 LINES=data/train_lines_v2 WORK=models/train_v2 ./finetune_tesseract.sh   # a second model
set -euo pipefail
cd "$(dirname "$0")"
ITER="${1:-10000}"
NAME="${NAME:-labnum}"
export LINES="${LINES:-data/train_lines}"
export WORK="${WORK:-models/train}"
mkdir -p "$WORK"
FROM="$WORK/eng.lstm"
LOGMODE=""
if [ "${RESUME:-0}" = 1 ]; then
  FROM="$WORK/${NAME}_checkpoint"
  LOGMODE="-a"
  echo "resuming from $FROM"
else

echo "1/5 extract base LSTM"
combine_tessdata -e models/eng_best.traineddata "$WORK/eng.lstm" >/dev/null

echo "2/5 line box files"
.venv/bin/python - <<'EOF'
import os
from pathlib import Path
from PIL import Image
for gt in sorted(Path(os.environ["LINES"]).glob("*.gt.txt")):
    png = gt.with_name(gt.name.replace(".gt.txt", ".png"))
    w, h = Image.open(png).size
    text = gt.read_text().strip()
    # tesstrain's line format: one WordStr covering the whole line, then an end-of-line marker
    gt.with_name(gt.name.replace(".gt.txt", ".box")).write_text(
        f"WordStr 0 0 {w} {h} 0 #{text}\n\t {w} 0 {w + 1} {h} 0\n")
EOF

echo "3/5 compile .lstmf (parallel)"
ls "$LINES"/*.png | sed 's/\.png$//' | xargs -P 8 -I{} sh -c 'tesseract {}.png {} --psm 13 --tessdata-dir models -l eng_best lstm.train >/dev/null 2>&1 || true'
ls "$LINES"/*.lstmf > "$WORK/all.txt"
echo "   $(wc -l < "$WORK/all.txt") lstmf files"

echo "4/5 split train/eval"
.venv/bin/python - <<'EOF'
import os, random
from pathlib import Path
W = Path(os.environ["WORK"])
files = (W / "all.txt").read_text().split()
random.Random(1).shuffle(files)
n = max(1, len(files) // 20)
(W / "list.eval").write_text("\n".join(files[:n]) + "\n")
(W / "list.train").write_text("\n".join(files[n:]) + "\n")
print(f"   train {len(files) - n}, eval {n}")
EOF
fi

echo "5/5 lstmtraining ($ITER iterations, fine-tune learning rate 1e-4)"
lstmtraining \
  --model_output "$WORK/$NAME" \
  --continue_from "$FROM" \
  --traineddata models/eng_best.traineddata \
  --train_listfile "$WORK/list.train" \
  --eval_listfile "$WORK/list.eval" \
  --learning_rate 0.0001 \
  --max_iterations "$ITER" \
  --target_error_rate 0.005 2>&1 | tee $LOGMODE "$WORK/training.log" | grep -E "At iteration|Finished|best" || true

lstmtraining --stop_training \
  --continue_from "$WORK/${NAME}_checkpoint" \
  --traineddata models/eng_best.traineddata \
  --model_output "models/$NAME.traineddata"
ls -la "models/$NAME.traineddata"
