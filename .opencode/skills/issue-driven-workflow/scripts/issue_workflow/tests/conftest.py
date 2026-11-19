import sys
from pathlib import Path

# Тесты импортируют пакет как `issue_workflow`, поэтому в path нужен каталог scripts.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
