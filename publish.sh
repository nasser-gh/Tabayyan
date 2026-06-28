#!/usr/bin/env bash
#
# publish.sh — prepare and push Tabayyan to your GitHub.
#
#   ./publish.sh <github-username> [--repo NAME] [--branch NAME] [--dry-run]
#
# What it does:
#   1. Replaces the OWNER placeholder in links/badges with your username.
#   2. git init (if needed), commits, sets the origin remote.
#   3. Pushes the branch, then creates and pushes the version tag
#      (which triggers the PyPI release workflow, once Trusted Publisher is set).
#
# It will NOT publish to PyPI or post anywhere — only your GitHub repo.
# Review the diff it shows before confirming.

set -euo pipefail

REPO="tabayyan"
BRANCH="main"
DRY_RUN=0
USERNAME=""

c_g=$'\033[32m'; c_y=$'\033[33m'; c_r=$'\033[31m'; c_b=$'\033[1m'; c_0=$'\033[0m'
say(){ printf "${c_b}==>${c_0} %s\n" "$*"; }
warn(){ printf "${c_y}!! %s${c_0}\n" "$*"; }
die(){ printf "${c_r}xx %s${c_0}\n" "$*" >&2; exit 1; }
run(){ if [ "$DRY_RUN" = 1 ]; then printf "   ${c_y}[dry-run]${c_0} %s\n" "$*"; else eval "$@"; fi; }

ensure_identity(){
  # git commit and annotated tags require a configured identity.
  if [ -n "$(git config user.email 2>/dev/null)" ] && [ -n "$(git config user.name 2>/dev/null)" ]; then
    return 0
  fi
  warn "git identity not set (user.name / user.email)."
  if [ "$DRY_RUN" = 1 ]; then warn "[dry-run] would prompt for name/email"; return 0; fi
  printf "  Your name  : "; read -r gname
  printf "  Your email : "; read -r gemail
  [ -n "$gname" ] && [ -n "$gemail" ] || die "name and email are required to commit."
  git config user.name  "$gname"
  git config user.email "$gemail"
  say "Set local git identity for this repo: $gname <$gemail>"
}

# --- parse args ---
while [ $# -gt 0 ]; do
  case "$1" in
    --repo)    REPO="$2"; shift 2;;
    --branch)  BRANCH="$2"; shift 2;;
    --dry-run) DRY_RUN=1; shift;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    -*)        die "unknown flag: $1";;
    *)         USERNAME="$1"; shift;;
  esac
done

# --- preconditions ---
command -v git >/dev/null || die "git is not installed."
[ -f pyproject.toml ] || die "run this from the extracted tabayyan/ directory (pyproject.toml not found)."
[ -n "$USERNAME" ] || { printf "GitHub username: "; read -r USERNAME; }
[ -n "$USERNAME" ] || die "username is required."

VERSION=$(grep -oE '__version__ = "[^"]+"' src/tabayyan/__init__.py | sed -E 's/.*"([^"]+)".*/\1/')
[ -n "$VERSION" ] || die "could not read version from src/tabayyan/__init__.py"
TAG="v$VERSION"
URL="https://github.com/$USERNAME/$REPO.git"

echo
say "Username : $USERNAME"
say "Repo     : $REPO"
say "Branch   : $BRANCH"
say "Version  : $TAG"
say "Remote   : $URL"
[ "$DRY_RUN" = 1 ] && warn "DRY RUN — no changes will be made."
echo
printf "Proceed? [y/N] "; read -r ok
case "$ok" in y|Y|yes) ;; *) die "aborted.";; esac

# --- 1. replace OWNER placeholder (only in github.com/OWNER URLs) ---
say "Replacing OWNER -> $USERNAME in links/badges"
FILES=$(grep -rl 'github.com/OWNER' . --include='*.toml' --include='*.md' --include='*.yml' 2>/dev/null || true)
for f in $FILES; do
  if [ "$DRY_RUN" = 1 ]; then
    printf "   ${c_y}[dry-run]${c_0} edit %s\n" "$f"
  else
    perl -pi -e "s{github\\.com/OWNER\\b}{github.com/$USERNAME}g" "$f"
    printf "   edited %s\n" "$f"
  fi
done

# --- 2. git init / commit ---
if [ ! -d .git ]; then
  say "Initialising git repo on branch $BRANCH"
  run "git init -b '$BRANCH' >/dev/null"
else
  run "git branch -M '$BRANCH'"
fi
ensure_identity
run "git add -A"
if [ "$DRY_RUN" = 1 ] || ! git diff --cached --quiet 2>/dev/null; then
  run "git commit -m 'Tabayyan $TAG' >/dev/null || true"
else
  warn "nothing to commit (working tree already committed)"
fi

# --- 3. remote + push ---
if git remote | grep -q '^origin$'; then
  run "git remote set-url origin '$URL'"
else
  run "git remote add origin '$URL'"
fi
say "Pushing branch '$BRANCH' to origin"
run "git push -u origin '$BRANCH'"

# --- 4. tag + push tag ---
if git rev-parse "$TAG" >/dev/null 2>&1; then
  warn "tag $TAG already exists locally — skipping tag creation"
else
  run "git tag -a '$TAG' -m '$TAG'"
fi
say "Pushing tag '$TAG' (triggers release workflow if PyPI Trusted Publisher is configured)"
run "git push origin '$TAG'"

echo
WEBURL="https://github.com/$USERNAME/$REPO"
echo
say "${c_g}Done.${c_0} Next, manually:"
echo "   • PyPI: set up a Trusted Publisher (OIDC) for project '$REPO' once, so the tag push can publish."
echo "   • GitHub: add the About text + Topics, and upload the social-preview image (Settings -> Social preview)."
echo "   • Verify the Actions run is green: $WEBURL/actions"
