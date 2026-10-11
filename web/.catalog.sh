#!/bin/zsh
# Helper for the landing-page build: runs 21st.dev catalog searches and prints
# compact results. Not part of the app; scratch tooling only.
C=../.tools-cache/_npx/87cd840c1ea4f182/node_modules/.bin/21st
for q in "$@"; do
  print "\n### $q"
  $C search "$q" --limit 8 2>&1
done
