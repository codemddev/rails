#!/usr/bin/env bash
root="$(pwd)"
target="${1:-all}"
status=0
mkdir -p "$root/codemd-reports" "$root/.codemd/test-results"
if [ "$target" = "finalize" ]; then
  if [ ! -f "$root/.codemd/test-results/0.exit" ]; then echo "CODEMD_TIMEOUT 0"; echo "CODEMD_RESULT 0 124"; status=1; else code="$(cat "$root/.codemd/test-results/0.exit")"; [ "$code" -eq 0 ] || status=1; fi
  exit "$status"
fi
if [ "$target" = "all" ] || [ "$target" = "0" ]; then { echo '### CodeMD: changed-line coverage'; echo; echo 'Lines this change touched that the tests ran. The raw reports are in the **codemd-coverage-reports** zip under Artifacts, kept 90 days.'; echo; echo '| File | Changed lines run | Not run |'; echo '|---|---|---|'; } >> "${GITHUB_STEP_SUMMARY:-/dev/null}"; fi
if [ "$target" = "all" ] || [ "$target" = "0" ]; then
( cd . && eval 'export BUNDLE_FROZEN=false BUNDLE_DEPLOYMENT=false; bundle install --jobs 4 && ( ( BUNDLE_FROZEN=false BUNDLE_DEPLOYMENT=false bundle add simplecov --group test >/dev/null 2>&1 || git checkout -- Gemfile Gemfile.lock >/dev/null 2>&1; RUBYOPT="-r$root/.codemd/simplecov_start.rb" bundle exec ruby -Itest -Ilib activesupport/test/message_pack/cache_serializer_test.rb ) || bundle exec ruby -Itest -Ilib activesupport/test/message_pack/cache_serializer_test.rb )' ); code=$?
echo "$code" > "$root/.codemd/test-results/0.exit"
echo "CODEMD_RESULT 0 $code"; [ "$code" -eq 0 ] || status=1
( cd . && [ -f .codemd-ruby-coverage/.resultset.json ] && cp .codemd-ruby-coverage/.resultset.json "$root/codemd-reports/"0-simplecov-resultset.json ) || true
( cd . && python3 "$root/.codemd/coverage_summary.py" simplecov .codemd-ruby-coverage/.resultset.json activesupport/lib/active_support/message_pack/cache_serializer.rb 25 25 0 25 ) || true
if [ "$code" -ne 0 ] && [ "$code" -ne 124 ] && [ "$code" -ne 126 ] && [ "$code" -ne 127 ]; then passes=0; for n in 1 2; do ( cd . && timeout 300 bash -c 'export BUNDLE_FROZEN=false BUNDLE_DEPLOYMENT=false; bundle install --jobs 4 && ( ( BUNDLE_FROZEN=false BUNDLE_DEPLOYMENT=false bundle add simplecov --group test >/dev/null 2>&1 || git checkout -- Gemfile Gemfile.lock >/dev/null 2>&1; RUBYOPT="-r$root/.codemd/simplecov_start.rb" bundle exec ruby -Itest -Ilib activesupport/test/message_pack/cache_serializer_test.rb ) || bundle exec ruby -Itest -Ilib activesupport/test/message_pack/cache_serializer_test.rb )' ) >/dev/null 2>&1 && passes=$((passes+1)); done; echo "CODEMD_RERUN 0 $passes 2"; fi
fi
exit "$status"
