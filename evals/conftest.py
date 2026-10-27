import os
import sys
import tempfile
from pathlib import Path

# evals/ sits next to gogo/, not inside it — make both importable when
# running `pytest evals` from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# Every test gets a throwaway home. Without this, a test that builds Settings()
# resolves to the repo's ./.gogo (a maintainer's real memory) or to the
# person's real ~/.gogo. Set before gogo.config is imported, so a .env that
# names GOGO_HOME cannot override it. Tests of the resolution rules pass their
# own env, cwd and user_home.
os.environ["GOGO_HOME"] = tempfile.mkdtemp(prefix="gogo-evals-")
