#!/usr/bin/env bash
# Install the third-party skills this setup relies on, fresh from upstream.
# These are NOT vendored into this repo on purpose: `npx skills update` keeps
# them current, and forking them would freeze them at one commit.
#
# Skills land in ~/.agents/skills. Run install.sh afterwards to link them into
# ~/.claude/skills. Run `npx skills update` periodically to refresh.
set -euo pipefail

# 25 skill(s): ask-matt, code-review, codebase-design, diagnosing-bugs …
npx --yes skills@latest add mattpocock/skills

# 23 skill(s): lark-approval, lark-attendance, lark-base, lark-calendar …
npx --yes skills@latest add larksuite/cli

#  7 skill(s): brandkit, design-taste-frontend, high-end-visual-design, image-to-code …
npx --yes skills@latest add Leonxlnx/taste-skill

#  1 skill(s): find-skills
npx --yes skills@latest add vercel-labs/skills

#  1 skill(s): deslop
npx --yes skills@latest add cursor/plugins

#  1 skill(s): stop-slop
npx --yes skills@latest add hardikpandya/stop-slop

#  1 skill(s): microsoft-foundry
npx --yes skills@latest add microsoft/azure-skills

#  1 skill(s): improve
npx --yes skills@latest add shadcn/improve

#  1 skill(s): impeccable
npx --yes skills@latest add pbakaus/impeccable

#  1 skill(s): improve-react
npx --yes skills@latest add aidenybai/react-doctor
